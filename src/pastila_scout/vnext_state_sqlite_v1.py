"""Isolated SQLite operational-state boundary for VNext."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from .vnext_foundation_v1 import (
    BoundaryError,
    canonical_json,
    contained_path,
    object_identity,
    sha256_bytes,
)
from .vnext_workflow_v1 import (
    ReplayConflict,
    TransitionRequest,
    apply_transition,
    new_workflow,
    validate_workflow,
)

SCHEMA_VERSION = 1
DEFAULT_BUSY_TIMEOUT_MS = 5_000
MIGRATION_1 = (
    "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, migration_identity TEXT NOT NULL UNIQUE, applied_by TEXT NOT NULL)",
    "CREATE TABLE writer_owner (singleton INTEGER PRIMARY KEY CHECK(singleton=1), writer_identity TEXT NOT NULL)",
    "CREATE TABLE sources (source_identity TEXT PRIMARY KEY, source_type TEXT NOT NULL, config_identity TEXT NOT NULL)",
    "CREATE TABLE captures (capture_identity TEXT PRIMARY KEY, source_identity TEXT NOT NULL REFERENCES sources(source_identity), payload_identity TEXT NOT NULL, payload_ref TEXT NOT NULL, captured_at TEXT)",
    "CREATE TABLE events (event_identity TEXT PRIMARY KEY, grouping_identity TEXT NOT NULL)",
    "CREATE TABLE event_sources (event_identity TEXT NOT NULL REFERENCES events(event_identity), capture_identity TEXT NOT NULL REFERENCES captures(capture_identity), PRIMARY KEY(event_identity,capture_identity))",
    "CREATE TABLE source_packets (packet_identity TEXT PRIMARY KEY, event_identity TEXT NOT NULL REFERENCES events(event_identity), payload_identity TEXT NOT NULL, payload_ref TEXT NOT NULL)",
    "CREATE TABLE workflows (workflow_identity TEXT PRIMARY KEY, current_state TEXT NOT NULL, state_identity TEXT NOT NULL, state_json BLOB NOT NULL)",
    "CREATE TABLE workflow_artifacts (artifact_identity TEXT PRIMARY KEY, workflow_identity TEXT NOT NULL REFERENCES workflows(workflow_identity), artifact_kind TEXT NOT NULL CHECK(artifact_kind IN ('EDITOR_DRAFT','VOICE_DRAFT','FINAL_OUTPUT')), payload_identity TEXT NOT NULL, payload_ref TEXT NOT NULL, schema_identity TEXT NOT NULL)",
    "CREATE TABLE decisions (decision_identity TEXT PRIMARY KEY, workflow_identity TEXT NOT NULL REFERENCES workflows(workflow_identity), decision_kind TEXT NOT NULL CHECK(decision_kind IN ('FACTUAL','APPROVAL')), outcome TEXT NOT NULL, actor TEXT NOT NULL, input_identity TEXT NOT NULL, receipt_identity TEXT NOT NULL)",
    "CREATE TABLE attempts (attempt_identity TEXT PRIMARY KEY, workflow_identity TEXT NOT NULL REFERENCES workflows(workflow_identity), operation_identity TEXT NOT NULL, outcome TEXT NOT NULL)",
    "CREATE TABLE idempotency (workflow_identity TEXT NOT NULL REFERENCES workflows(workflow_identity), idempotency_identity TEXT NOT NULL, request_identity TEXT NOT NULL, receipt_identity TEXT NOT NULL, PRIMARY KEY(workflow_identity,idempotency_identity))",
    "CREATE TABLE state_transitions (sequence INTEGER PRIMARY KEY AUTOINCREMENT, workflow_identity TEXT NOT NULL REFERENCES workflows(workflow_identity), receipt_identity TEXT NOT NULL UNIQUE, operation_identity TEXT NOT NULL, previous_state TEXT NOT NULL, resulting_state TEXT NOT NULL, actor TEXT NOT NULL, outcome TEXT NOT NULL, input_identity TEXT NOT NULL, output_identity TEXT, attempt_identity TEXT NOT NULL REFERENCES attempts(attempt_identity), idempotency_identity TEXT NOT NULL, receipt_json BLOB NOT NULL)",
)
MIGRATIONS = {1: MIGRATION_1}


class StateBoundaryError(BoundaryError):
    pass


class SchemaMismatch(StateBoundaryError):
    pass


class WriterOwnershipError(StateBoundaryError):
    pass


class IntegrityFailure(StateBoundaryError):
    pass


@dataclass(frozen=True)
class BackupReceipt:
    path: str
    sha256: str
    size: int
    schema_version: int
    integrity: str


def migration_identity(version: int) -> str:
    return object_identity({"version": version, "statements": MIGRATIONS[version]})


def _decode_json(value: bytes | str) -> dict[str, object]:
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    result = json.loads(value)
    if not isinstance(result, dict):
        raise IntegrityFailure("expected JSON object")
    return result


class SQLiteStateStore:
    """Single-writer state persistence; every operation owns its connection."""

    def __init__(self, *, root: Path, database: Path, writer_identity: str, busy_timeout_ms: int = DEFAULT_BUSY_TIMEOUT_MS):
        self.root = root.resolve(strict=True)
        self.database = contained_path(self.root, database)
        self.writer_identity = writer_identity
        self.busy_timeout_ms = busy_timeout_ms
        if not writer_identity or busy_timeout_ms < 1:
            raise StateBoundaryError("writer identity and positive busy timeout required")

    def _connect(self, *, readonly: bool = False) -> sqlite3.Connection:
        if readonly:
            if not self.database.exists():
                raise StateBoundaryError("database does not exist")
            connection = sqlite3.connect(f"file:{self.database.as_posix()}?mode=ro", uri=True, isolation_level=None)
        else:
            self.database.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.database, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(f"PRAGMA busy_timeout={int(self.busy_timeout_ms)}")
        if not readonly:
            mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            if str(mode).casefold() != "wal":
                connection.close()
                raise StateBoundaryError(f"WAL unavailable: {mode}")
            connection.execute("PRAGMA synchronous=FULL")
        return connection

    @contextmanager
    def read(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect(readonly=True)
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def write(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._assert_writer(connection)
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def bootstrap(self) -> None:
        connection = self._connect()
        try:
            current = int(connection.execute("PRAGMA user_version").fetchone()[0])
            if current > SCHEMA_VERSION:
                raise SchemaMismatch(f"database version {current} is newer than {SCHEMA_VERSION}")
            for version in range(current + 1, SCHEMA_VERSION + 1):
                if version not in MIGRATIONS:
                    raise SchemaMismatch(f"missing migration {version}")
                connection.execute("BEGIN IMMEDIATE")
                try:
                    for statement in MIGRATIONS[version]:
                        connection.execute(statement)
                    connection.execute(
                        "INSERT INTO schema_migrations(version,migration_identity,applied_by) VALUES(?,?,?)",
                        (version, migration_identity(version), self.writer_identity),
                    )
                    connection.execute(
                        "INSERT OR IGNORE INTO writer_owner(singleton,writer_identity) VALUES(1,?)",
                        (self.writer_identity,),
                    )
                    connection.execute(f"PRAGMA user_version={version}")
                    connection.commit()
                except BaseException:
                    connection.rollback()
                    raise
            self._verify_schema_connection(connection)
            self._assert_writer(connection)
        finally:
            connection.close()

    def _assert_writer(self, connection: sqlite3.Connection) -> None:
        try:
            row = connection.execute("SELECT writer_identity FROM writer_owner WHERE singleton=1").fetchone()
        except sqlite3.OperationalError as exc:
            raise SchemaMismatch("writer ownership schema missing") from exc
        if row is None or row[0] != self.writer_identity:
            raise WriterOwnershipError(f"database owned by {None if row is None else row[0]}")

    def _verify_schema_connection(self, connection: sqlite3.Connection) -> None:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version != SCHEMA_VERSION:
            raise SchemaMismatch(f"expected schema {SCHEMA_VERSION}, got {version}")
        rows = connection.execute("SELECT version,migration_identity FROM schema_migrations ORDER BY version").fetchall()
        expected = [(version, migration_identity(version)) for version in range(1, SCHEMA_VERSION + 1)]
        if [(row[0], row[1]) for row in rows] != expected:
            raise SchemaMismatch("migration history mismatch")

    def create_workflow(self, workflow_identity: str) -> dict[str, object]:
        state = new_workflow(workflow_identity)
        with self.write() as connection:
            connection.execute(
                "INSERT INTO workflows(workflow_identity,current_state,state_identity,state_json) VALUES(?,?,?,?)",
                (workflow_identity, state["state"], state["state_identity"], canonical_json(state)),
            )
        return state

    def load_workflow(self, workflow_identity: str) -> dict[str, object]:
        with self.read() as connection:
            row = connection.execute(
                "SELECT current_state,state_identity,state_json FROM workflows WHERE workflow_identity=?",
                (workflow_identity,),
            ).fetchone()
        if row is None:
            raise StateBoundaryError(f"unknown workflow: {workflow_identity}")
        state = _decode_json(row["state_json"])
        validate_workflow(state)
        if row["current_state"] != state["state"] or row["state_identity"] != state["state_identity"]:
            raise IntegrityFailure("workflow columns disagree with canonical document")
        return state

    def transition(
        self,
        request: TransitionRequest,
        *,
        before_commit: Callable[[sqlite3.Connection], None] | None = None,
        after_commit: Callable[[], None] | None = None,
    ) -> tuple[dict[str, object], dict[str, object], bool]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._assert_writer(connection)
            row = connection.execute(
                "SELECT state_json FROM workflows WHERE workflow_identity=?",
                (request.workflow_id,),
            ).fetchone()
            if row is None:
                raise StateBoundaryError(f"unknown workflow: {request.workflow_id}")
            current = _decode_json(row[0])
            validate_workflow(current)
            request_identity = object_identity(request.semantic())
            existing = connection.execute(
                "SELECT request_identity,receipt_identity FROM idempotency WHERE workflow_identity=? AND idempotency_identity=?",
                (request.workflow_id, request.idempotency_identity),
            ).fetchone()
            if existing is not None:
                if existing["request_identity"] != request_identity:
                    raise ReplayConflict(f"conflicting replay: {request.idempotency_identity}")
                receipt_row = connection.execute(
                    "SELECT receipt_json FROM state_transitions WHERE receipt_identity=?",
                    (existing["receipt_identity"],),
                ).fetchone()
                connection.commit()
                return current, _decode_json(receipt_row[0]), False
            updated, receipt, changed = apply_transition(current, request)
            if not changed:
                raise IntegrityFailure("unpersisted idempotency unexpectedly replayed")
            connection.execute(
                "INSERT INTO attempts(attempt_identity,workflow_identity,operation_identity,outcome) VALUES(?,?,?,?)",
                (request.attempt_identity, request.workflow_id, request.operation_id, request.outcome),
            )
            connection.execute(
                "INSERT INTO state_transitions(workflow_identity,receipt_identity,operation_identity,previous_state,resulting_state,actor,outcome,input_identity,output_identity,attempt_identity,idempotency_identity,receipt_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    request.workflow_id, receipt["receipt_identity"], request.operation_id,
                    request.previous_state, request.resulting_state, request.actor, request.outcome,
                    request.input_identity, request.output_identity, request.attempt_identity,
                    request.idempotency_identity, canonical_json(receipt),
                ),
            )
            connection.execute(
                "INSERT INTO idempotency(workflow_identity,idempotency_identity,request_identity,receipt_identity) VALUES(?,?,?,?)",
                (request.workflow_id, request.idempotency_identity, request_identity, receipt["receipt_identity"]),
            )
            connection.execute(
                "UPDATE workflows SET current_state=?,state_identity=?,state_json=? WHERE workflow_identity=?",
                (updated["state"], updated["state_identity"], canonical_json(updated), request.workflow_id),
            )
            if before_commit is not None:
                before_commit(connection)
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()
        if after_commit is not None:
            after_commit()
        return updated, receipt, True

    def reconstruct_workflow(self, workflow_identity: str) -> dict[str, object]:
        state = new_workflow(workflow_identity)
        with self.read() as connection:
            rows = connection.execute(
                "SELECT receipt_json FROM state_transitions WHERE workflow_identity=? ORDER BY sequence",
                (workflow_identity,),
            ).fetchall()
        for row in rows:
            receipt = _decode_json(row[0])
            request = TransitionRequest(
                workflow_id=str(receipt["workflow_identity"]),
                operation_id=str(receipt["operation_identity"]),
                previous_state=str(receipt["previous_state"]),
                resulting_state=str(receipt["resulting_state"]),
                actor=str(receipt["actor"]), outcome=str(receipt["outcome"]),
                input_identity=str(receipt["input_identity"]),
                output_identity=None if receipt["output_identity"] is None else str(receipt["output_identity"]),
                attempt_identity=str(receipt["attempt_identity"]),
                idempotency_identity=str(receipt["idempotency_identity"]),
                observed_at=None if "observed_at" not in receipt else str(receipt["observed_at"]),
                provenance=receipt.get("provenance") if isinstance(receipt.get("provenance"), Mapping) else None,
            )
            state, reproduced, changed = apply_transition(state, request)
            if not changed or reproduced["receipt_identity"] != receipt["receipt_identity"]:
                raise IntegrityFailure("transition reconstruction mismatch")
        stored = self.load_workflow(workflow_identity)
        if state != stored:
            raise IntegrityFailure("reconstructed workflow differs from stored state")
        return state

    def verify_integrity(self, database: Path | None = None) -> dict[str, object]:
        target = self.database if database is None else contained_path(self.root, database, allow_missing=False)
        connection = sqlite3.connect(f"file:{target.as_posix()}?mode=ro", uri=True, isolation_level=None)
        connection.row_factory = sqlite3.Row
        try:
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise IntegrityFailure("integrity_check failed")
            connection.execute("PRAGMA foreign_keys=ON")
            violations = connection.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise IntegrityFailure(f"foreign key violations: {len(violations)}")
            self._verify_schema_connection(connection)
            for row in connection.execute("SELECT current_state,state_identity,state_json FROM workflows"):
                value = _decode_json(row["state_json"])
                validate_workflow(value)
                if value["state"] != row["current_state"] or value["state_identity"] != row["state_identity"]:
                    raise IntegrityFailure("canonical workflow mismatch")
            return {"status": "PASS", "schema_version": SCHEMA_VERSION, "foreign_key_violations": 0}
        except (sqlite3.DatabaseError, BoundaryError) as exc:
            if isinstance(exc, IntegrityFailure):
                raise
            raise IntegrityFailure(str(exc)) from exc
        finally:
            connection.close()

    def checkpoint_wal(self) -> tuple[int, int, int]:
        connection = self._connect()
        try:
            row = connection.execute("PRAGMA wal_checkpoint(FULL)").fetchone()
            return int(row[0]), int(row[1]), int(row[2])
        finally:
            connection.close()

    def backup(self, destination: Path) -> BackupReceipt:
        destination = contained_path(self.root, destination)
        if destination.exists():
            raise StateBoundaryError(f"backup destination exists: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = contained_path(self.root, destination.parent / f".{destination.name}.tmp-{uuid.uuid4().hex}")
        self.checkpoint_wal()
        try:
            source = self._connect(readonly=True)
            target = sqlite3.connect(temporary)
            try:
                source.backup(target)
                target.commit()
            finally:
                target.close()
                source.close()
            self.verify_integrity(temporary)
            with temporary.open("r+b") as stream:
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return BackupReceipt(
            path=destination.relative_to(self.root).as_posix(),
            sha256=sha256_bytes(destination.read_bytes()),
            size=destination.stat().st_size,
            schema_version=SCHEMA_VERSION,
            integrity="PASS",
        )

    def restore(self, backup: Path, destination: Path, *, expected_identity: str) -> BackupReceipt:
        backup = contained_path(self.root, backup, allow_missing=False)
        destination = contained_path(self.root, destination)
        if destination.exists():
            raise StateBoundaryError("restore never overwrites an existing database")
        if sha256_bytes(backup.read_bytes()) != expected_identity:
            raise IntegrityFailure("backup identity mismatch")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = contained_path(self.root, destination.parent / f".{destination.name}.tmp-{uuid.uuid4().hex}")
        try:
            source = sqlite3.connect(f"file:{backup.as_posix()}?mode=ro", uri=True)
            target = sqlite3.connect(temporary)
            try:
                source.backup(target)
                target.commit()
            except sqlite3.DatabaseError as exc:
                raise IntegrityFailure(str(exc)) from exc
            finally:
                target.close()
                source.close()
            self.verify_integrity(temporary)
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return BackupReceipt(
            path=destination.relative_to(self.root).as_posix(),
            sha256=sha256_bytes(destination.read_bytes()), size=destination.stat().st_size,
            schema_version=SCHEMA_VERSION, integrity="PASS",
        )
