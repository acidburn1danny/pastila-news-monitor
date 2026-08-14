"""Explicit owner-authorized replacement of installed state from development state."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.active_project_v1 import ActiveProjectStoreV1

FINAL_CATEGORIES = frozenset({"Politica", "Social", "CanCan", "Diverse", "Externe"})


class OwnerStateImportError(ValueError):
    """Owner-state import failed closed."""


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _material_payload_sha256(path: Path) -> str:
    """Read the Editor payload identity; retain raw-file legacy compatibility."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError, UnicodeError, json.JSONDecodeError:
        value = None
    if isinstance(value, dict) and isinstance(value.get("payload_sha256"), str):
        return value["payload_sha256"]
    return f"sha256:{_hash(path).lower()}"


def _database_facts(path: Path) -> dict[str, object]:
    if not path.is_file():
        raise OwnerStateImportError("database is missing")
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise OwnerStateImportError("database integrity failed")
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        if not {"events", "articles", "sources", "event_categories"} <= tables:
            raise OwnerStateImportError("database schema is unsupported")
        categories = {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT category FROM events WHERE category IS NOT NULL"
            )
        }
        row_categories = {
            row[0]
            for row in connection.execute(
                "SELECT DISTINCT category FROM event_categories"
            )
        }
        if not categories | row_categories <= FINAL_CATEGORIES:
            raise OwnerStateImportError("database contains legacy categories")
        multiple = connection.execute(
            "SELECT COUNT(*) FROM (SELECT event_id FROM event_categories "
            "GROUP BY event_id HAVING COUNT(*) != 1)"
        ).fetchone()[0]
        mismatch = connection.execute(
            "SELECT COUNT(*) FROM events e LEFT JOIN event_categories c "
            "ON c.event_id=e.id AND c.category=e.category WHERE c.event_id IS NULL"
        ).fetchone()[0]
        orphans = connection.execute(
            "SELECT COUNT(*) FROM articles a LEFT JOIN events e ON e.id=a.event_id "
            "WHERE a.event_id IS NOT NULL AND e.id IS NULL"
        ).fetchone()[0]
        foreign_keys = len(connection.execute("PRAGMA foreign_key_check").fetchall())
        invalid_ids = connection.execute(
            "SELECT COUNT(*) FROM events WHERE id IS NULL OR id <= 0"
        ).fetchone()[0]
        if multiple or mismatch or orphans or foreign_keys or invalid_ids:
            raise OwnerStateImportError("database violates final category integrity")
        return {
            "integrity": "ok",
            "events": connection.execute("SELECT COUNT(*) FROM events").fetchone()[0],
            "articles": connection.execute("SELECT COUNT(*) FROM articles").fetchone()[
                0
            ],
            "sources": connection.execute("SELECT COUNT(*) FROM sources").fetchone()[0],
            "multiple_categories": multiple,
            "scalar_row_mismatches": mismatch,
            "orphan_articles": orphans,
            "foreign_key_violations": foreign_keys,
            "invalid_event_ids": invalid_ids,
        }
    except sqlite3.Error as error:
        raise OwnerStateImportError("database validation failed") from error
    finally:
        connection.close()


def _assert_not_locked(path: Path) -> None:
    if not path.exists() or sys.platform != "win32":
        return
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    )
    kernel32.CreateFileW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    handle = kernel32.CreateFileW(str(path), 0x80000000, 0, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise OwnerStateImportError("installed database is in use")
    kernel32.CloseHandle(handle)


def _database_sidecars(path: Path) -> tuple[Path, ...]:
    return tuple(Path(f"{path}{suffix}") for suffix in ("-wal", "-shm", "-journal"))


def _assert_source_stable(path: Path) -> None:
    if path.exists() and sys.platform == "win32":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.argtypes = (
            ctypes.c_wchar_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_void_p,
        )
        kernel32.CreateFileW.restype = ctypes.c_void_p
        kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
        handle = kernel32.CreateFileW(
            str(path), 0x80000000, 0x1 | 0x4, None, 3, 0x80, None
        )
        if handle == ctypes.c_void_p(-1).value:
            raise OwnerStateImportError("source database may be in use by a writer")
        kernel32.CloseHandle(handle)
    if any(sidecar.exists() for sidecar in _database_sidecars(path)):
        raise OwnerStateImportError("source database has SQLite sidecars")


def _assert_no_reparse(path: Path, *, label: str) -> None:
    current = path
    while True:
        if current.exists() and (
            current.is_symlink()
            or (sys.platform == "win32" and current.stat().st_file_attributes & 0x400)
        ):
            raise OwnerStateImportError(f"{label} cannot contain reparse points")
        if current.parent == current:
            break
        current = current.parent


def _overlaps(first: Path, second: Path) -> bool:
    first_text = os.path.normcase(str(first.resolve()))
    second_text = os.path.normcase(str(second.resolve()))
    try:
        common = os.path.commonpath((first_text, second_text))
    except ValueError:
        return False
    return common in (first_text, second_text)


def _expected_project_identity(source: Path, target: Path) -> dict[str, object]:
    project = source / "data" / "active-project-v1.json"
    _validate_project(project, source / "data" / "news_monitor.db")
    value = json.loads(project.read_text(encoding="utf-8"))
    materials: list[dict[str, str]] = []
    seen: set[str] = set()
    reserved = {
        "news_monitor.db",
        "active-project-v1.json",
        "development-migration-v1.json",
        "owner-state-import-v1.json",
    }
    reports = (source / "reports").resolve()
    for material in value.get("editor_materials", ()):
        output = material.get("output_path")
        if not isinstance(output, str):
            raise OwnerStateImportError("active project material path is invalid")
        source_output = Path(output).resolve()
        identity = source_output.name.casefold()
        if (
            not source_output.is_file()
            or reports not in source_output.parents
            or identity in seen
            or identity in reserved
        ):
            raise OwnerStateImportError("active project material names collide")
        seen.add(identity)
        digest = _hash(source_output)
        if material.get("payload_sha256") != _material_payload_sha256(source_output):
            raise OwnerStateImportError("active project material hash mismatch")
        destination = target / "reports" / source_output.name
        material["output_path"] = str(destination)
        materials.append(
            {"source": str(source_output), "target": str(destination), "sha256": digest}
        )
    payload = (
        json.dumps(value, ensure_ascii=False, sort_keys=True) + os.linesep
    ).encode()
    return {
        "payload": payload,
        "sha256": hashlib.sha256(payload).hexdigest().upper(),
        "materials": materials,
    }


def _state_is_current(
    *, plan_database_hash: str, target: Path, project: dict[str, object] | None
) -> bool:
    database = target / "data" / "news_monitor.db"
    if not database.is_file() or _hash(database) != plan_database_hash:
        return False
    if any(sidecar.exists() for sidecar in _database_sidecars(database)):
        return False
    if project is None:
        return True
    target_project = target / "data" / "active-project-v1.json"
    if not target_project.is_file() or _hash(target_project) != project["sha256"]:
        return False
    return all(
        Path(item["target"]).is_file() and _hash(Path(item["target"])) == item["sha256"]
        for item in project["materials"]
    )


def _file_record(path: Path) -> dict[str, object]:
    return {"path": str(path), "size": path.stat().st_size, "sha256": _hash(path)}


def _validate_project(path: Path, database: Path) -> None:
    if not path.is_file():
        raise OwnerStateImportError("active project is missing")
    try:
        ActiveProjectStoreV1(database_path=database, project_path=path).load()
    except Exception as error:
        raise OwnerStateImportError("active project is invalid") from error


def _stage_project(
    *, source: Path, target: Path, stage: Path, staged_database: Path
) -> tuple[Path, list[tuple[Path, Path]]]:
    source_project = source / "data" / "active-project-v1.json"
    _validate_project(source_project, source / "data" / "news_monitor.db")
    value = json.loads(source_project.read_text(encoding="utf-8"))
    report_destinations: list[tuple[Path, Path]] = []
    seen: set[str] = set()
    for material in value.get("editor_materials", ()):
        output = material.get("output_path")
        if not isinstance(output, str):
            raise OwnerStateImportError("active project material path is invalid")
        source_output = Path(output).resolve()
        reports = (source / "reports").resolve()
        if not source_output.is_file() or reports not in source_output.parents:
            raise OwnerStateImportError(
                "active project material is outside source reports"
            )
        if source_output.name in seen:
            raise OwnerStateImportError("active project material names collide")
        seen.add(source_output.name)
        staged_output = stage / "reports" / source_output.name
        staged_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_output, staged_output)
        digest = material.get("payload_sha256")
        if digest != _material_payload_sha256(staged_output):
            raise OwnerStateImportError("active project material hash mismatch")
        destination = target / "reports" / source_output.name
        material["output_path"] = str(destination)
        report_destinations.append((staged_output, destination))
    staged_project = stage / "active-project-v1.json"
    staged_project.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    # Validate identity/event references against the staged DB using temporary
    # report paths, without publishing anything into installed state.
    temporary = json.loads(staged_project.read_text(encoding="utf-8"))
    for material in temporary.get("editor_materials", ()):
        material["output_path"] = str(
            stage / "reports" / Path(material["output_path"]).name
        )
    validation_project = stage / "active-project-validation.json"
    validation_project.write_text(
        json.dumps(temporary, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _validate_project(validation_project, staged_database)
    validation_project.unlink()
    return staged_project, report_destinations


def inspect_owner_state_import(
    *,
    source_root: Path,
    target_local_root: Path,
    backup_root: Path,
    include_active_project: bool = False,
) -> dict[str, object]:
    for path, label in (
        (source_root, "source"),
        (target_local_root, "target"),
        (backup_root, "backup"),
    ):
        _assert_no_reparse(path, label=label)
    source_root = source_root.resolve()
    target_local_root = target_local_root.resolve()
    backup_root = backup_root.resolve()
    if _overlaps(source_root, target_local_root):
        raise OwnerStateImportError("source and target overlap")
    if _overlaps(backup_root, target_local_root) or _overlaps(backup_root, source_root):
        raise OwnerStateImportError(
            "backup must be external to source and installed state"
        )
    source_db = source_root / "data" / "news_monitor.db"
    _assert_source_stable(source_db)
    facts = _database_facts(source_db)
    target_db = target_local_root / "data" / "news_monitor.db"
    if target_db.exists():
        _assert_not_locked(target_db)
        target_connection = sqlite3.connect(
            f"file:{target_db.as_posix()}?mode=ro", uri=True
        )
        try:
            target_integrity = target_connection.execute(
                "PRAGMA integrity_check"
            ).fetchone()[0]
        finally:
            target_connection.close()
        if target_integrity != "ok":
            raise OwnerStateImportError("target database integrity failed")
    project_identity = None
    if include_active_project:
        project_identity = _expected_project_identity(source_root, target_local_root)
    target_items = tuple(
        path
        for path in (
            target_db,
            *_database_sidecars(target_db),
            target_local_root / "data" / "active-project-v1.json",
            target_local_root / "data" / "owner-state-import-v1.json",
            target_local_root / "data" / "development-migration-v1.json",
        )
        if path.is_file()
    )
    material_bytes = sum(
        Path(item["source"]).stat().st_size
        for item in (project_identity or {}).get("materials", ())
    )
    required = (
        source_db.stat().st_size * 2
        + material_bytes * 2
        + sum(item.stat().st_size for item in target_items)
    )
    probe = backup_root
    while not probe.exists():
        probe = probe.parent
    if shutil.disk_usage(probe).free < required:
        raise OwnerStateImportError("insufficient backup/staging space")
    source_record = _file_record(source_db)
    return {
        "status": "already_current"
        if _state_is_current(
            plan_database_hash=str(source_record["sha256"]),
            target=target_local_root,
            project=project_identity,
        )
        else "ready",
        "source_root": str(source_root),
        "target_local_root": str(target_local_root),
        "backup_root": str(backup_root),
        "include_active_project": include_active_project,
        "source_database": source_record,
        "source_facts": facts,
        "target_database": _file_record(target_db) if target_db.exists() else None,
        "settings_policy": "preserve",
        "source_override_policy": "preserve_and_rebase_at_startup",
        "development_migration_receipt_policy": "preserve",
        "replacement_policy": "owner_authoritative_exact_replacement_not_merge",
        "active_project_identity": (
            {
                "sha256": project_identity["sha256"],
                "materials": project_identity["materials"],
            }
            if project_identity
            else None
        ),
    }


def execute_owner_state_import(
    *,
    source_root: Path,
    target_local_root: Path,
    backup_root: Path,
    include_active_project: bool = False,
    failure_injector: Callable[[str], None] | None = None,
) -> dict[str, object]:
    plan = inspect_owner_state_import(
        source_root=source_root,
        target_local_root=target_local_root,
        backup_root=backup_root,
        include_active_project=include_active_project,
    )
    target = Path(str(plan["target_local_root"]))
    source = Path(str(plan["source_root"]))
    receipt_path = target / "data" / "owner-state-import-v1.json"
    if plan["status"] == "already_current":
        return {**plan, "orchestration_result": "already_current"}
    operation = uuid.uuid4().hex
    backup = Path(str(plan["backup_root"])) / f"owner-state-{operation}"
    stage = target / f".owner-state-import-{operation}"
    replaced: list[Path] = []
    backup_records: list[dict[str, object]] = []
    try:
        backup.mkdir(parents=True, exist_ok=False)
        stage.mkdir(parents=True, exist_ok=False)
        target_db = target / "data" / "news_monitor.db"
        targets = [target_db, *_database_sidecars(target_db)]
        source_project_value = None
        if include_active_project:
            targets.append(target / "data" / "active-project-v1.json")
            source_project_value = json.loads(
                (source / "data" / "active-project-v1.json").read_text(encoding="utf-8")
            )
            for material in source_project_value.get("editor_materials", ()):
                targets.append(target / "reports" / Path(material["output_path"]).name)
        migration = target / "data" / "development-migration-v1.json"
        receipt_target = target / "data" / "owner-state-import-v1.json"
        targets.extend((migration, receipt_target))
        target_identities: set[str] = set()
        for original in targets:
            relative = original.relative_to(target)
            identity = relative.as_posix().casefold()
            if identity in target_identities:
                raise OwnerStateImportError("target state paths collide")
            target_identities.add(identity)
            record: dict[str, object] = {
                "original": str(original),
                "original_existed": original.exists(),
                "backup": None,
                "original_size": original.stat().st_size if original.exists() else None,
                "original_sha256": _hash(original) if original.exists() else None,
            }
            if original.exists():
                saved = backup / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, saved)
                if _hash(saved) != _hash(original):
                    raise OwnerStateImportError("backup verification failed")
                record["backup"] = str(saved)
                record["backup_size"] = saved.stat().st_size
                record["backup_sha256"] = _hash(saved)
            backup_records.append(record)
        if failure_injector:
            failure_injector("after_backup")
        _assert_source_stable(source / "data" / "news_monitor.db")
        staged_db = stage / "news_monitor.db"
        shutil.copy2(source / "data" / "news_monitor.db", staged_db)
        if _hash(staged_db) != str(plan["source_database"]["sha256"]):
            raise OwnerStateImportError("source database changed during staging")
        _database_facts(staged_db)
        staged_project = None
        report_destinations: list[tuple[Path, Path]] = []
        if include_active_project:
            staged_project, report_destinations = _stage_project(
                source=source, target=target, stage=stage, staged_database=staged_db
            )
        if failure_injector:
            failure_injector("after_staging")
        (target / "data").mkdir(parents=True, exist_ok=True)
        for sidecar in _database_sidecars(target_db):
            if sidecar.exists():
                sidecar.unlink()
                replaced.append(sidecar)
                if failure_injector:
                    failure_injector(f"after_replace:{sidecar.name}")
        destinations = [
            (staged_db, target / "data" / "news_monitor.db"),
            *report_destinations,
        ]
        if staged_project is not None:
            destinations.append(
                (staged_project, target / "data" / "active-project-v1.json")
            )
        for staged, destination in destinations:
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged, destination)
            replaced.append(destination)
            if failure_injector:
                failure_injector(
                    f"after_replace:{destination.relative_to(target).as_posix()}"
                )
        if failure_injector:
            failure_injector("after_replace")
        facts = _database_facts(target / "data" / "news_monitor.db")
        if _hash(target / "data" / "news_monitor.db") != str(
            plan["source_database"]["sha256"]
        ):
            raise OwnerStateImportError("post-import database identity mismatch")
        if include_active_project:
            _validate_project(
                target / "data" / "active-project-v1.json",
                target / "data" / "news_monitor.db",
            )
        receipt = {
            "schema": "pastila-scout-owner-state-import",
            "schema_version": 1,
            "source_head": _source_head(source),
            "source_database_sha256": plan["source_database"]["sha256"],
            "target_pre_import_database_sha256": (
                plan["target_database"]["sha256"] if plan["target_database"] else None
            ),
            "target_post_import_database_sha256": _hash(
                target / "data" / "news_monitor.db"
            ),
            "included_state_items": ["database"]
            + (["active_project"] if include_active_project else []),
            "backup_path": str(backup),
            "backup_files": backup_records,
            "validation": facts,
            "settings_policy": "preserved",
            "source_override_policy": "preserved",
            "development_migration_receipt_policy": "preserved",
            "replacement_policy": "owner_authoritative_exact_replacement_not_merge",
            "completed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "orchestration_result": "completed",
        }
        temporary = receipt_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, receipt_path)
        replaced.append(receipt_path)
        if failure_injector:
            failure_injector("after_receipt")
        shutil.rmtree(stage, ignore_errors=True)
        return receipt
    except BaseException as error:
        temporary = receipt_path.with_suffix(".tmp")
        if temporary.exists():
            temporary.unlink()
        rollback_error: Exception | None = None
        try:
            for destination in reversed(replaced):
                saved = backup / destination.relative_to(target)
                if saved.exists():
                    shutil.copy2(saved, destination)
                    if _hash(saved) != _hash(destination):
                        raise OwnerStateImportError("rollback verification failed")
                elif destination.exists():
                    destination.unlink()
            restored_db = target / "data" / "news_monitor.db"
            if restored_db.exists():
                restored = sqlite3.connect(
                    f"file:{restored_db.as_posix()}?mode=ro", uri=True
                )
                try:
                    if restored.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise OwnerStateImportError(
                            "rollback database integrity failed"
                        )
                finally:
                    restored.close()
        except Exception as rollback_failure:  # noqa: BLE001 - record rollback failure
            rollback_error = rollback_failure
        if backup.exists():
            failure = {
                "schema": "pastila-scout-owner-state-import-failure",
                "schema_version": 1,
                "error_type": type(error).__name__,
                "original_error": str(error),
                "rollback": "failed" if rollback_error else "verified",
                "rollback_error": str(rollback_error) if rollback_error else None,
                "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            (backup / "failure-receipt.json").write_text(
                json.dumps(failure, indent=2) + "\n", encoding="utf-8"
            )
        shutil.rmtree(stage, ignore_errors=True)
        if rollback_error:
            raise OwnerStateImportError(
                "rollback failed; inspect failure receipt"
            ) from error
        raise


def _source_head(source: Path) -> str | None:
    result = subprocess.run(
        ("git", "-C", str(source), "rev-parse", "HEAD"),
        check=False,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _assert_application_stopped() -> None:
    if sys.platform != "win32":
        return
    for executable in ("PastilaScout.exe", "pastila-scout.exe"):
        result = subprocess.run(
            ("tasklist.exe", "/FI", f"IMAGENAME eq {executable}", "/FO", "CSV", "/NH"),
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise OwnerStateImportError(
                "cannot prove PastilaScout is stopped; process enumeration failed"
            )
        if f'"{executable}"' in result.stdout:
            raise OwnerStateImportError("PastilaScout must be closed")


def main() -> int:
    parser = argparse.ArgumentParser(prog="pastila-owner-state-import")
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--target-local-root", required=True, type=Path)
    parser.add_argument("--backup-root", required=True, type=Path)
    parser.add_argument("--include-active-project", action="store_true")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    source = args.source_root.resolve()
    if not (
        (source / ".git").exists()
        and (source / "pyproject.toml").is_file()
        and (source / "src" / "pastila_scout").is_dir()
    ):
        raise OwnerStateImportError("source is not a Pastila Scout development root")
    if str(source).startswith("\\\\") or str(args.backup_root.resolve()).startswith(
        "\\\\"
    ):
        raise OwnerStateImportError("network roots are not supported")
    expected = Path(os.environ["LOCALAPPDATA"]) / "PastilaScout"
    if args.target_local_root.resolve() != expected.resolve():
        raise OwnerStateImportError("target is not the installed LocalAppData state")
    _assert_application_stopped()
    function = execute_owner_state_import if args.apply else inspect_owner_state_import
    result = function(
        source_root=args.source_root,
        target_local_root=args.target_local_root,
        backup_root=args.backup_root,
        include_active_project=args.include_active_project,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
