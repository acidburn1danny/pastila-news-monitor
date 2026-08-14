from __future__ import annotations

import gc
import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

import pastila_scout.owner_state_import_v1 as owner_import
from pastila_scout.active_project_v1 import ActiveProjectStoreV1
from pastila_scout.database import initialize_database
from pastila_scout.owner_state_import_v1 import (
    OwnerStateImportError,
    execute_owner_state_import,
    inspect_owner_state_import,
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _database(path: Path, *, title: str = "Source", legacy: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.row_factory = sqlite3.Row
        initialize_database(connection)
        category = "Economie" if legacy else "Diverse"
        connection.execute(
            "INSERT INTO events (id,canonical_title,normalized_title,summary,category,"
            "first_seen_at,last_seen_at,article_count,source_count,created_at,updated_at) "
            "VALUES (1,?,?,?,?,'2026-01-01','2026-01-01',1,1,'2026-01-01','2026-01-01')",
            (title, title.lower(), "Summary", category),
        )
        connection.execute(
            "INSERT INTO event_categories(event_id,category,position) VALUES(1,?,0)",
            (category,),
        )
        connection.execute(
            "INSERT INTO sources(id,name,type,url,enabled,created_at,updated_at) "
            "VALUES('source','Source','rss','https://example.test/feed',1,"
            "'2026-01-01','2026-01-01')"
        )
        connection.execute(
            "INSERT INTO articles(source_id,url,normalized_url,title,normalized_title,"
            "discovered_at,event_id) VALUES('source','https://example.test/story',"
            "'https://example.test/story',?,?,'2026-01-01',1)",
            (title, title.lower()),
        )
        connection.commit()
    finally:
        connection.close()


def test_fresh_state_import_and_repeat_are_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "installed"
    backup = tmp_path / "backup"
    _database(source / "data" / "news_monitor.db")

    result = execute_owner_state_import(
        source_root=source, target_local_root=target, backup_root=backup
    )
    repeated = execute_owner_state_import(
        source_root=source, target_local_root=target, backup_root=backup
    )

    assert result["orchestration_result"] == "completed"
    assert repeated["orchestration_result"] == "already_current"
    assert _hash(target / "data" / "news_monitor.db") == _hash(
        source / "data" / "news_monitor.db"
    )


def test_stale_state_is_backed_up_and_replaced_without_touching_user_policy(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    target = tmp_path / "installed"
    backup = tmp_path / "backup"
    _database(source / "data" / "news_monitor.db", title="Authoritative")
    _database(target / "data" / "news_monitor.db", title="Stale", legacy=True)
    old_hash = _hash(target / "data" / "news_monitor.db")
    migration = target / "data" / "development-migration-v1.json"
    migration.write_text('{"historical":true}\n', encoding="utf-8")
    settings = tmp_path / "roaming" / "settings.json"
    override = tmp_path / "roaming" / "sources.override.yaml"
    settings.parent.mkdir()
    settings.write_text("settings", encoding="utf-8")
    override.write_text("override", encoding="utf-8")

    result = execute_owner_state_import(
        source_root=source, target_local_root=target, backup_root=backup
    )

    saved = Path(result["backup_path"]) / "data" / "news_monitor.db"
    assert _hash(saved) == old_hash
    assert migration.read_text(encoding="utf-8") == '{"historical":true}\n'
    assert settings.read_text(encoding="utf-8") == "settings"
    assert override.read_text(encoding="utf-8") == "override"
    assert result["validation"]["multiple_categories"] == 0


def test_failure_after_replace_restores_exact_original(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "installed"
    backup = tmp_path / "backup"
    _database(source / "data" / "news_monitor.db", title="Authoritative")
    _database(target / "data" / "news_monitor.db", title="Original", legacy=True)
    original = (target / "data" / "news_monitor.db").read_bytes()

    def fail(stage: str) -> None:
        if stage == "after_replace":
            raise RuntimeError("injected")

    with pytest.raises(RuntimeError, match="injected"):
        execute_owner_state_import(
            source_root=source,
            target_local_root=target,
            backup_root=backup,
            failure_injector=fail,
        )
    assert (target / "data" / "news_monitor.db").read_bytes() == original


def test_preflight_rejects_invalid_authoritative_category_state(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "installed"
    _database(source / "data" / "news_monitor.db", legacy=True)
    with pytest.raises(OwnerStateImportError, match="legacy categories"):
        inspect_owner_state_import(
            source_root=source,
            target_local_root=target,
            backup_root=tmp_path / "backup",
        )


def test_active_project_must_validate_when_explicitly_requested(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _database(source / "data" / "news_monitor.db")
    project = source / "data" / "active-project-v1.json"
    project.write_text(json.dumps({"version": 1}) + "\n", encoding="utf-8")
    with pytest.raises(OwnerStateImportError, match="active project is invalid"):
        inspect_owner_state_import(
            source_root=source,
            target_local_root=tmp_path / "installed",
            backup_root=tmp_path / "backup",
            include_active_project=True,
        )


def test_explicit_active_project_import_relocates_materials(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "installed"
    _database(source / "data" / "news_monitor.db")
    store = ActiveProjectStoreV1(
        database_path=source / "data" / "news_monitor.db",
        project_path=source / "data" / "active-project-v1.json",
    )
    store.handoff(event_id=1)
    output = source / "reports" / "editor-1.json"
    output.parent.mkdir()
    payload_identity = f"sha256:{'a' * 64}"
    output.write_text(
        json.dumps({"payload_sha256": payload_identity, "result": "ok"}) + "\n",
        encoding="utf-8",
    )
    store.record_editor_output(output_path=output, payload_sha256=payload_identity)
    del store
    gc.collect()

    result = execute_owner_state_import(
        source_root=source,
        target_local_root=target,
        backup_root=tmp_path / "backup",
        include_active_project=True,
    )
    restored = ActiveProjectStoreV1(
        database_path=target / "data" / "news_monitor.db",
        project_path=target / "data" / "active-project-v1.json",
    ).load()

    assert result["included_state_items"] == ["database", "active_project"]
    assert restored is not None
    assert (
        Path(restored.editor_materials[0].output_path)
        == target / "reports" / output.name
    )
    assert (target / "reports" / output.name).read_bytes() == output.read_bytes()

    repeat_plan = inspect_owner_state_import(
        source_root=source,
        target_local_root=target,
        backup_root=tmp_path / "repeat-backup",
        include_active_project=True,
    )
    assert (
        _hash(target / "data" / "active-project-v1.json")
        == repeat_plan["active_project_identity"]["sha256"]
    )
    repeated = execute_owner_state_import(
        source_root=source,
        target_local_root=target,
        backup_root=tmp_path / "repeat-backup",
        include_active_project=True,
    )
    assert repeated["orchestration_result"] == "already_current"


def test_same_database_does_not_mask_requested_project_change(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "installed"
    _database(source / "data" / "news_monitor.db")
    (target / "data").mkdir(parents=True)
    (target / "data" / "news_monitor.db").write_bytes(
        (source / "data" / "news_monitor.db").read_bytes()
    )
    store = ActiveProjectStoreV1(
        database_path=source / "data" / "news_monitor.db",
        project_path=source / "data" / "active-project-v1.json",
    )
    store.handoff(event_id=1)
    del store
    gc.collect()

    plan = inspect_owner_state_import(
        source_root=source,
        target_local_root=target,
        backup_root=tmp_path / "backup",
        include_active_project=True,
    )

    assert plan["status"] == "ready"


def test_active_project_material_cannot_collide_with_state_backup_names(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    _database(source / "data" / "news_monitor.db")
    store = ActiveProjectStoreV1(
        database_path=source / "data" / "news_monitor.db",
        project_path=source / "data" / "active-project-v1.json",
    )
    store.handoff(event_id=1)
    output = source / "reports" / "news_monitor.db"
    output.parent.mkdir()
    output.write_bytes(b"material")
    store.record_editor_output(
        output_path=output, payload_sha256=f"sha256:{_hash(output).lower()}"
    )
    del store
    gc.collect()

    with pytest.raises(OwnerStateImportError, match="names collide"):
        inspect_owner_state_import(
            source_root=source,
            target_local_root=tmp_path / "installed",
            backup_root=tmp_path / "backup",
            include_active_project=True,
        )


def test_source_sidecar_fails_closed_without_target_mutation(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "installed"
    _database(source / "data" / "news_monitor.db")
    sidecar = source / "data" / "news_monitor.db-wal"
    sidecar.write_bytes(b"writer-state")

    with pytest.raises(OwnerStateImportError, match="SQLite sidecars"):
        execute_owner_state_import(
            source_root=source,
            target_local_root=target,
            backup_root=tmp_path / "backup",
        )
    assert not (target / "data" / "news_monitor.db").exists()


def test_same_database_with_target_sidecar_is_republished_safely(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    target = tmp_path / "installed"
    _database(source / "data" / "news_monitor.db")
    (target / "data").mkdir(parents=True)
    target_db = target / "data" / "news_monitor.db"
    target_db.write_bytes((source / "data" / "news_monitor.db").read_bytes())
    sidecar = target / "data" / "news_monitor.db-shm"
    sidecar.write_bytes(b"stale")

    result = execute_owner_state_import(
        source_root=source,
        target_local_root=target,
        backup_root=tmp_path / "backup",
    )

    assert result["orchestration_result"] == "completed"
    assert not sidecar.exists()


def test_changed_source_is_not_mistaken_for_already_current(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "installed"
    _database(source / "data" / "news_monitor.db", title="First")
    execute_owner_state_import(
        source_root=source,
        target_local_root=target,
        backup_root=tmp_path / "first-backup",
    )
    (source / "data" / "news_monitor.db").unlink()
    _database(source / "data" / "news_monitor.db", title="Second")

    result = execute_owner_state_import(
        source_root=source,
        target_local_root=target,
        backup_root=tmp_path / "second-backup",
    )

    assert result["orchestration_result"] == "completed"
    assert _hash(target / "data" / "news_monitor.db") == _hash(
        source / "data" / "news_monitor.db"
    )


def test_target_sidecars_and_previous_receipt_restore_after_failure(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    target = tmp_path / "installed"
    _database(source / "data" / "news_monitor.db", title="Authoritative")
    _database(target / "data" / "news_monitor.db", title="Original", legacy=True)
    sidecar = target / "data" / "news_monitor.db-shm"
    sidecar.write_bytes(b"stale-sidecar")
    receipt = target / "data" / "owner-state-import-v1.json"
    receipt.write_bytes(b'{"old":true}\n')
    originals = {path: path.read_bytes() for path in (sidecar, receipt)}

    def fail(stage: str) -> None:
        if stage == "after_receipt":
            raise RuntimeError("injected")

    with pytest.raises(RuntimeError, match="injected"):
        execute_owner_state_import(
            source_root=source,
            target_local_root=target,
            backup_root=tmp_path / "backup",
            failure_injector=fail,
        )
    assert {path: path.read_bytes() for path in originals} == originals


@pytest.mark.parametrize(
    "failure_stage",
    ("after_backup", "after_staging", "after_replace:data/news_monitor.db"),
)
def test_failure_boundaries_preserve_original_database(
    tmp_path: Path, failure_stage: str
) -> None:
    source = tmp_path / "source"
    target = tmp_path / "installed"
    _database(source / "data" / "news_monitor.db", title="Authoritative")
    _database(target / "data" / "news_monitor.db", title="Original", legacy=True)
    original = (target / "data" / "news_monitor.db").read_bytes()

    def fail(stage: str) -> None:
        if stage == failure_stage:
            raise RuntimeError("injected")

    with pytest.raises(RuntimeError, match="injected"):
        execute_owner_state_import(
            source_root=source,
            target_local_root=target,
            backup_root=tmp_path / "backup",
            failure_injector=fail,
        )
    assert (target / "data" / "news_monitor.db").read_bytes() == original


def test_backup_copy_failure_occurs_before_target_mutation(
    tmp_path: Path, monkeypatch
) -> None:
    source = tmp_path / "source"
    target = tmp_path / "installed"
    backup_root = tmp_path / "backup"
    _database(source / "data" / "news_monitor.db", title="Authoritative")
    _database(target / "data" / "news_monitor.db", title="Original", legacy=True)
    original = (target / "data" / "news_monitor.db").read_bytes()
    real_copy = __import__("shutil").copy2

    def fail_backup(source_path, destination_path, *args, **kwargs):
        if backup_root in Path(destination_path).parents:
            raise OSError("backup denied")
        return real_copy(source_path, destination_path, *args, **kwargs)

    monkeypatch.setattr("pastila_scout.owner_state_import_v1.shutil.copy2", fail_backup)
    with pytest.raises(OSError, match="backup denied"):
        execute_owner_state_import(
            source_root=source,
            target_local_root=target,
            backup_root=backup_root,
        )
    assert (target / "data" / "news_monitor.db").read_bytes() == original
    failure_receipts = tuple(backup_root.glob("*/failure-receipt.json"))
    assert len(failure_receipts) == 1
    assert (
        json.loads(failure_receipts[0].read_text(encoding="utf-8"))["rollback"]
        == "verified"
    )


def test_process_enumeration_failure_and_cli_process_fail_closed(monkeypatch) -> None:
    class Result:
        def __init__(self, returncode: int, stdout: str = "") -> None:
            self.returncode = returncode
            self.stdout = stdout

    monkeypatch.setattr(owner_import.sys, "platform", "win32")
    monkeypatch.setattr(
        owner_import.subprocess, "run", lambda *args, **kwargs: Result(1)
    )
    with pytest.raises(OwnerStateImportError, match="cannot prove"):
        owner_import._assert_application_stopped()

    calls = iter((Result(0, "INFO: No tasks"), Result(0, '"pastila-scout.exe"')))
    monkeypatch.setattr(
        owner_import.subprocess, "run", lambda *args, **kwargs: next(calls)
    )
    with pytest.raises(OwnerStateImportError, match="must be closed"):
        owner_import._assert_application_stopped()
