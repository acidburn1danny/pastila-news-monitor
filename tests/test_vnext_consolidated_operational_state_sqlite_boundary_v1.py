from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from pastila_scout.vnext_foundation_v1 import object_identity, sha256_bytes
from pastila_scout.vnext_state_sqlite_v1 import (
    IntegrityFailure,
    SchemaMismatch,
    SQLiteStateStore,
    StateBoundaryError,
    WriterOwnershipError,
)
from pastila_scout.vnext_workflow_v1 import (
    IllegalTransition,
    ReplayConflict,
    TransitionRequest,
)


def store(tmp_path: Path, *, writer: str = "writer-1", timeout: int = 100) -> SQLiteStateStore:
    value = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity=writer, busy_timeout_ms=timeout)
    value.bootstrap()
    return value


def transition(previous: str = "DISCOVERED", resulting: str = "CAPTURED", *, key: str = "key-1", operation: str = "op-1", attempt: str = "attempt-1") -> TransitionRequest:
    return TransitionRequest("flow-1", operation, previous, resulting, "fixture", "PASS", "a" * 64, "b" * 64, attempt, key, "2026-09-28T00:00:00Z", {"fixture": "sqlite-v1"})


def test_bootstrap_schema_policy_and_migration_identity(tmp_path: Path):
    value = store(tmp_path)
    with value.read() as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0].casefold() == "wal"
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] == 100
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 4
        assert connection.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0] == 4
    value.bootstrap()
    assert value.verify_integrity()["status"] == "PASS"


def test_schema_newer_than_runtime_fails_closed(tmp_path: Path):
    database = tmp_path / "state.db"
    connection = sqlite3.connect(database); connection.execute("PRAGMA user_version=99"); connection.close()
    value = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="writer-1")
    with pytest.raises(SchemaMismatch):
        value.bootstrap()


def test_writer_ownership_and_foreign_keys(tmp_path: Path):
    value = store(tmp_path)
    other = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="writer-2", busy_timeout_ms=100)
    with pytest.raises(WriterOwnershipError):
        other.bootstrap()
    with value.write() as connection, pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO captures VALUES('capture','missing','payload','ref',NULL)")


def test_atomic_legal_transition_idempotency_conflict_and_reconstruction(tmp_path: Path):
    value = store(tmp_path); value.create_workflow("flow-1")
    updated, receipt, changed = value.transition(transition())
    assert changed and updated["state"] == "CAPTURED"
    replayed, same, changed = value.transition(transition())
    assert not changed and replayed == updated and same == receipt
    with pytest.raises(ReplayConflict):
        value.transition(transition(operation="different"))
    assert value.reconstruct_workflow("flow-1") == updated
    with value.read() as connection:
        assert connection.execute("SELECT COUNT(*) FROM state_transitions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM idempotency").fetchone()[0] == 1


def test_illegal_transition_and_precommit_failure_roll_back_everything(tmp_path: Path):
    value = store(tmp_path); initial = value.create_workflow("flow-1")
    with pytest.raises(IllegalTransition):
        value.transition(transition(resulting="EXPORTED"))
    with pytest.raises(RuntimeError, match="injected"):
        value.transition(transition(), before_commit=lambda _: (_ for _ in ()).throw(RuntimeError("injected")))
    assert value.load_workflow("flow-1") == initial
    with value.read() as connection:
        for table in ("state_transitions", "idempotency", "attempts"):
            assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_post_commit_ack_failure_and_restart_replay(tmp_path: Path):
    value = store(tmp_path); value.create_workflow("flow-1")
    with pytest.raises(RuntimeError, match="ack lost"):
        value.transition(transition(), after_commit=lambda: (_ for _ in ()).throw(RuntimeError("ack lost")))
    restarted = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="writer-1", busy_timeout_ms=100)
    state, _, changed = restarted.transition(transition())
    assert not changed and state["state"] == "CAPTURED"


def test_concurrent_writer_contention_respects_busy_timeout(tmp_path: Path):
    value = store(tmp_path, timeout=50)
    holder = value._connect(); holder.execute("BEGIN IMMEDIATE")
    contender = value._connect()
    try:
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            contender.execute("BEGIN IMMEDIATE")
    finally:
        contender.close(); holder.rollback(); holder.close()


def test_backup_restore_integrity_and_no_overwrite(tmp_path: Path):
    value = store(tmp_path); value.create_workflow("flow-1"); value.transition(transition())
    backup = value.backup(Path("backups/state.backup.db"))
    assert backup.integrity == "PASS" and backup.sha256 == sha256_bytes((tmp_path / backup.path).read_bytes())
    restored = value.restore(Path(backup.path), Path("restore/state.db"), expected_identity=backup.sha256)
    assert restored.integrity == "PASS"
    restored_store = SQLiteStateStore(root=tmp_path, database=Path(restored.path), writer_identity="writer-1", busy_timeout_ms=100)
    assert restored_store.verify_integrity()["status"] == "PASS"
    assert restored_store.reconstruct_workflow("flow-1")["state"] == "CAPTURED"
    with pytest.raises(StateBoundaryError, match="never overwrites"):
        value.restore(Path(backup.path), Path(restored.path), expected_identity=backup.sha256)


def test_corrupt_incomplete_and_identity_mismatch_backup_fail_closed(tmp_path: Path):
    value = store(tmp_path); value.create_workflow("flow-1")
    corrupt = tmp_path / "corrupt.db"; corrupt.write_bytes(b"not sqlite")
    with pytest.raises(IntegrityFailure):
        value.restore(Path("corrupt.db"), Path("restore-corrupt.db"), expected_identity=sha256_bytes(corrupt.read_bytes()))
    value.backup(Path("valid.db"))
    with pytest.raises(IntegrityFailure, match="identity mismatch"):
        value.restore(Path("valid.db"), Path("restore-wrong.db"), expected_identity="0" * 64)
    assert not (tmp_path / "restore-corrupt.db").exists()
    assert not (tmp_path / "restore-wrong.db").exists()


def test_failed_backup_validation_leaves_no_partial_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    value = store(tmp_path)
    value.create_workflow("flow-1")

    def reject_backup(_database: Path | None = None) -> dict[str, object]:
        raise IntegrityFailure("injected validation failure")

    monkeypatch.setattr(value, "verify_integrity", reject_backup)
    with pytest.raises(IntegrityFailure, match="injected validation failure"):
        value.backup(Path("failed.db"))
    assert not (tmp_path / "failed.db").exists()
    assert list(tmp_path.glob(".failed.db.tmp-*")) == []


def test_canonical_state_corruption_is_detected(tmp_path: Path):
    value = store(tmp_path); value.create_workflow("flow-1")
    connection = sqlite3.connect(tmp_path / "state.db")
    connection.execute("UPDATE workflows SET current_state='EXPORTED'"); connection.commit(); connection.close()
    with pytest.raises(IntegrityFailure, match="canonical workflow mismatch"):
        value.verify_integrity()


def test_fixture_and_contract_are_self_contained():
    contract = json.loads(Path("docs/artifacts/vnext-consolidated-operational-state-sqlite-boundary-v1-contract.json").read_text(encoding="utf-8"))
    fixtures = json.loads(Path("docs/artifacts/vnext-consolidated-operational-state-sqlite-boundary-v1-fixtures.json").read_text(encoding="utf-8"))
    assert contract["external_runtime_dependencies_new"] == 0
    assert contract["product_data_migration"] is False and contract["active_integration"] is False
    assert len(fixtures["cases"]) == 25
    assert object_identity(fixtures) == object_identity(json.loads(json.dumps(fixtures)))


def test_acceptance_artifact_kinds_are_persistable_without_implementing_acceptance(tmp_path: Path):
    value = store(tmp_path); value.create_workflow("flow-1")
    with value.write() as connection:
        for index, kind in enumerate(("EDITOR_DRAFT", "ACCEPTED_SETUP", "SOURCE_FALLBACK", "ABSTAINED")):
            connection.execute(
                "INSERT INTO workflow_artifacts VALUES(?,?,?,?,?,?)",
                (f"artifact-{index}", "flow-1", kind, f"payload-{index}", f"blobs/{index}.json", "schema-v1"),
            )
    with value.read() as connection:
        assert [row[0] for row in connection.execute("SELECT artifact_kind FROM workflow_artifacts ORDER BY artifact_identity")] == [
            "EDITOR_DRAFT", "ACCEPTED_SETUP", "SOURCE_FALLBACK", "ABSTAINED",
        ]
