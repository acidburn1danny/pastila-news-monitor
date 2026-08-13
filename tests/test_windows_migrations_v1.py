from __future__ import annotations

import copy
import json
import pickle
import shutil
import sqlite3
import weakref
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.active_project_v1 import (
    ActiveProjectStoreV1,
    ActiveProjectV1,
    ChiefEditorItemV1,
    EditorMaterialV1,
)
from pastila_scout.contracts.samples import sample_scout_input
from pastila_scout.windows_state_v1 import migrations
from pastila_scout.windows_state_v1.errors import _WindowsStateMigrationError
from pastila_scout.windows_state_v1.migrations import (
    DevelopmentMigrationApplicabilityV1,
    _execute_development_state_migration_v1,
    _inspect_development_state_migration_applicability_v1,
    _inspect_development_state_migration_v1,
    _migrate_windows_database_v1,
)
from pastila_scout.windows_state_v1.paths import (
    _create_windows_application_directories_v1,
    _resolve_windows_application_paths_v1,
)

DEFAULTS = Path("src/pastila_scout/desktop_v1/default-settings-v1.json").resolve()
SOURCES = Path("config/sources.yaml").resolve()


def test_no_development_state_is_a_passive_noop(tmp_path: Path) -> None:
    root, paths = _layout(tmp_path)
    plan = _inspect_development_state_migration_v1(
        development_root=root, destination=paths
    )
    assert plan.status == "nothing_to_migrate"
    assert (
        _execute_development_state_migration_v1(plan=plan).status
        == "nothing_to_migrate"
    )


def test_applicability_requires_a_root_without_reading_source_state(
    tmp_path: Path,
) -> None:
    root, paths = _layout(tmp_path)
    malformed = root / "config" / "sources.yaml"
    malformed.parent.mkdir(parents=True)
    malformed.write_text("ai: {}\n", encoding="utf-8")

    first = _inspect_development_state_migration_applicability_v1(destination=paths)
    second = _inspect_development_state_migration_applicability_v1(destination=paths)

    assert first.status == second.status == "development_root_required"
    assert first == second


def test_applicability_validates_receipt_without_development_root(
    tmp_path: Path,
) -> None:
    root, paths = _layout(tmp_path)
    settings = root / "config" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_bytes(DEFAULTS.read_bytes())
    _execute_development_state_migration_v1(
        plan=_inspect_development_state_migration_v1(
            development_root=root, destination=paths
        )
    )

    applicability = _inspect_development_state_migration_applicability_v1(
        destination=paths
    )

    assert applicability.status == "already_migrated"


def test_applicability_recovers_pending_state_without_development_root(
    tmp_path: Path,
) -> None:
    _, paths = _layout(tmp_path)
    operation = "a" * 32
    local_stage = paths.local_state_root / f".development-migration-{operation}"
    roaming_stage = paths.roaming_state_root / f".development-migration-{operation}"
    local_stage.mkdir()
    roaming_stage.mkdir()
    paths.migration_pending_path.write_text(
        json.dumps(
            {
                "schema": "pastila-scout-development-migration-pending",
                "schema_version": 1,
                "operation_id": operation,
                "artifacts": [],
            }
        ),
        encoding="utf-8",
    )

    applicability = _inspect_development_state_migration_applicability_v1(
        destination=paths
    )

    assert applicability.status == "development_root_required"
    assert not paths.migration_pending_path.exists()
    assert not local_stage.exists()
    assert not roaming_stage.exists()


def test_applicability_rejects_invalid_receipt_safely(tmp_path: Path) -> None:
    _, paths = _layout(tmp_path)
    paths.migration_receipt_path.write_text('{"schema":"wrong"}\n', encoding="utf-8")

    with pytest.raises(_WindowsStateMigrationError) as raised:
        _inspect_development_state_migration_applicability_v1(destination=paths)

    assert str(raised.value) == "Windows application state migration failed."
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


def test_applicability_rejects_unsupported_receipt_version(tmp_path: Path) -> None:
    _, paths = _layout(tmp_path)
    _write_receipt(paths, schema_version=2)

    with pytest.raises(_WindowsStateMigrationError) as raised:
        _inspect_development_state_migration_applicability_v1(destination=paths)

    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


def test_applicability_rejects_invalid_pending_recovery_safely(tmp_path: Path) -> None:
    _, paths = _layout(tmp_path)
    paths.migration_pending_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(_WindowsStateMigrationError) as raised:
        _inspect_development_state_migration_applicability_v1(destination=paths)

    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    assert paths.migration_pending_path.exists()


def test_applicability_value_is_hardened_and_minimal() -> None:
    required = DevelopmentMigrationApplicabilityV1("development_root_required")
    same = DevelopmentMigrationApplicabilityV1("development_root_required")
    migrated = DevelopmentMigrationApplicabilityV1("already_migrated")

    assert required == same
    assert required != migrated
    assert hash(required) == hash(same)
    shallow = copy.copy(required)
    deep = copy.deepcopy(required)
    assert shallow == deep == required
    assert shallow is not required
    assert deep is not required
    assert tuple(item.name for item in fields(required)) == ("status",)
    assert not hasattr(required, "__dict__")
    with pytest.raises(TypeError):
        weakref.ref(required)
    assert repr(required) == (
        "DevelopmentMigrationApplicabilityV1(status='development_root_required')"
    )
    with pytest.raises(FrozenInstanceError):
        required.status = "already_migrated"  # type: ignore[misc]
    assert required.status == "development_root_required"
    with pytest.raises((FrozenInstanceError, AttributeError, TypeError)):
        required.receipt = {}  # type: ignore[attr-defined]
    assert not hasattr(required, "receipt")
    with pytest.raises(TypeError):
        pickle.dumps(required)
    with pytest.raises(TypeError):

        class DerivedApplicability(DevelopmentMigrationApplicabilityV1):
            pass

    for invalid in ("unknown", 1, None):
        with pytest.raises(_WindowsStateMigrationError):
            DevelopmentMigrationApplicabilityV1(invalid)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "process_control",
    [KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError],
)
def test_applicability_propagates_process_control(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    process_control: type[BaseException],
) -> None:
    _, paths = _layout(tmp_path)

    def interrupt(_paths) -> None:
        raise process_control

    monkeypatch.setattr(migrations, "_recover_pending", interrupt)
    with pytest.raises(process_control) as raised:
        _inspect_development_state_migration_applicability_v1(destination=paths)
    assert raised.type is process_control


@pytest.mark.parametrize(
    "state",
    ["valid_receipt", "malformed_receipt", "pending", "recovery_failure"],
)
def test_full_inspector_rejects_invalid_root_before_applicability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
) -> None:
    _, paths = _layout(tmp_path)
    if state == "valid_receipt":
        _write_receipt(paths)
    elif state == "malformed_receipt":
        paths.migration_receipt_path.write_text("{}\n", encoding="utf-8")
    elif state in {"pending", "recovery_failure"}:
        paths.migration_pending_path.write_text(
            (_pending_json(operation="b" * 32) if state == "pending" else "{}\n"),
            encoding="utf-8",
        )
    receipt_before = (
        paths.migration_receipt_path.read_bytes()
        if paths.migration_receipt_path.exists()
        else None
    )
    pending_before = (
        paths.migration_pending_path.read_bytes()
        if paths.migration_pending_path.exists()
        else None
    )
    called = False

    def applicability_spy(*, destination):
        nonlocal called
        del destination
        called = True
        raise AssertionError

    monkeypatch.setattr(
        migrations,
        "_inspect_development_state_migration_applicability_v1",
        applicability_spy,
    )
    with pytest.raises(_WindowsStateMigrationError):
        _inspect_development_state_migration_v1(
            development_root=(tmp_path / "missing").resolve(), destination=paths
        )

    assert not called
    assert (
        paths.migration_receipt_path.read_bytes()
        if paths.migration_receipt_path.exists()
        else None
    ) == receipt_before
    assert (
        paths.migration_pending_path.read_bytes()
        if paths.migration_pending_path.exists()
        else None
    ) == pending_before


def test_applicability_never_inspects_development_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, paths = _layout(tmp_path)

    def forbidden(*args, **kwargs):
        del args, kwargs
        raise AssertionError

    monkeypatch.setattr(migrations, "load_sources_config", forbidden)
    monkeypatch.setattr(migrations, "_load_windows_settings_v1", forbidden)
    monkeypatch.setattr(migrations, "_regular_optional", forbidden)
    monkeypatch.setattr(migrations, "_reports_optional", forbidden)

    result = _inspect_development_state_migration_applicability_v1(destination=paths)

    assert result.status == "development_root_required"


def test_applicability_recovery_is_idempotent(tmp_path: Path) -> None:
    _, paths = _layout(tmp_path)
    operation = "c" * 32
    paths.migration_pending_path.write_text(
        _pending_json(operation=operation), encoding="utf-8"
    )

    first = _inspect_development_state_migration_applicability_v1(destination=paths)
    second = _inspect_development_state_migration_applicability_v1(destination=paths)

    assert (
        first
        == second
        == DevelopmentMigrationApplicabilityV1("development_root_required")
    )
    assert not paths.migration_pending_path.exists()


def test_applicability_preserves_all_artifact_eligibility(tmp_path: Path) -> None:
    root, paths = _layout(tmp_path)
    database = root / "data" / "news_monitor.db"
    database.parent.mkdir(parents=True)
    database.write_bytes(b"database")
    reports = root / "reports"
    reports.mkdir()
    (reports / "report.html").write_text("report", encoding="utf-8")
    settings = root / "config" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_bytes(DEFAULTS.read_bytes())
    shutil.copyfile(SOURCES, root / "config" / "sources.yaml")

    plan = _inspect_development_state_migration_v1(
        development_root=root, destination=paths
    )

    assert plan.status == "ready"
    assert plan.database_eligible
    assert plan.reports_eligible
    assert plan.settings_eligible
    assert plan.source_eligible


def test_current_desktop_project_and_editor_output_are_imported_and_remapped(
    tmp_path: Path,
) -> None:
    root, paths = _layout(tmp_path)
    reports = root / "reports"
    reports.mkdir()
    output = reports / "editor-555.json"
    output.write_text('{"status":"completed"}\n', encoding="utf-8")
    (reports / "structura-episod.md").write_text("export\n", encoding="utf-8")
    (reports / "editor-diagnostics").mkdir()
    source = sample_scout_input()
    material = EditorMaterialV1(
        "editor-material-v1:event:555",
        source.ranked_events[0].event_id,
        source.ranked_events[0].canonical_title,
        source.ranked_events[0].canonical_summary,
        str(output),
        "sha256:" + "1" * 64,
    )
    project_path = root / "data" / "active-project-v1.json"
    ActiveProjectStoreV1(
        database_path=root / "data" / "news_monitor.db",
        project_path=project_path,
    )._write(
        ActiveProjectV1(
            "active-project-v1:test",
            source.ranked_events[0].canonical_title,
            datetime.now(UTC),
            source,
            (material,),
            (ChiefEditorItemV1(material.reference, "Externe", "Tranziție"),),
            "Test E2E Pastila Scout",
            datetime.now(UTC),
        )
    )

    plan = _inspect_development_state_migration_v1(
        development_root=root, destination=paths
    )
    assert plan.status == "ready"
    assert plan.active_project_available and plan.active_project_eligible
    assert not plan.reports_available
    result = _execute_development_state_migration_v1(plan=plan)
    assert result.status == "completed" and result.active_project_copied
    installed = ActiveProjectStoreV1(
        database_path=paths.database_path,
        project_path=paths.database_path.parent / "active-project-v1.json",
    ).load()
    assert installed is not None
    assert installed.chief_editor_title == "Test E2E Pastila Scout"
    assert installed.chief_editor_items[0].section == "Externe"
    assert installed.editor_materials[0].output_path == str(
        paths.report_directory / output.name
    )
    assert (paths.report_directory / output.name).read_bytes() == output.read_bytes()
    assert not (paths.report_directory / "structura-episod.md").exists()


def test_source_seed_is_validated_byte_preserving_and_idempotent(
    tmp_path: Path,
) -> None:
    root, paths = _layout(tmp_path)
    source = root / "config" / "sources.yaml"
    source.parent.mkdir(parents=True)
    shutil.copyfile(SOURCES, source)
    original = source.read_bytes()
    plan = _inspect_development_state_migration_v1(
        development_root=root, destination=paths
    )
    assert plan.status == "ready" and plan.source_eligible
    result = _execute_development_state_migration_v1(plan=plan)
    assert result.status == "completed" and result.source_override_seeded
    assert paths.source_override_path.read_bytes() == original
    assert source.read_bytes() == original
    assert (
        _inspect_development_state_migration_v1(
            development_root=root, destination=paths
        ).status
        == "already_migrated"
    )


def test_application_config_is_never_migrated(tmp_path: Path) -> None:
    root, paths = _layout(tmp_path)
    config = root / "config" / "config.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("secret: should-not-copy\n", encoding="utf-8")
    plan = _inspect_development_state_migration_v1(
        development_root=root, destination=paths
    )
    assert plan.status == "nothing_to_migrate"
    assert not any(
        "config.yaml" == item.name for item in paths.local_state_root.rglob("*")
    )


def test_malformed_source_fails_without_destination_mutation(tmp_path: Path) -> None:
    root, paths = _layout(tmp_path)
    source = root / "config" / "sources.yaml"
    source.parent.mkdir(parents=True)
    source.write_text("ai: {}\n", encoding="utf-8")
    with pytest.raises(_WindowsStateMigrationError) as raised:
        _inspect_development_state_migration_v1(
            development_root=root, destination=paths
        )
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    assert not paths.source_override_path.exists()


def test_existing_override_is_never_overwritten(tmp_path: Path) -> None:
    root, paths = _layout(tmp_path)
    source = root / "config" / "sources.yaml"
    source.parent.mkdir(parents=True)
    shutil.copyfile(SOURCES, source)
    paths.source_override_path.write_bytes(b"existing\n")
    plan = _inspect_development_state_migration_v1(
        development_root=root, destination=paths
    )
    assert plan.status == "destination_occupied"
    assert (
        _execute_development_state_migration_v1(plan=plan).status
        == "destination_occupied"
    )
    assert paths.source_override_path.read_bytes() == b"existing\n"


def test_applicability_preserves_partial_eligibility_and_executor_freshness(
    tmp_path: Path,
) -> None:
    root, paths = _layout(tmp_path)
    settings = root / "config" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_bytes(DEFAULTS.read_bytes())
    source = root / "config" / "sources.yaml"
    shutil.copyfile(SOURCES, source)
    paths.source_override_path.write_bytes(b"existing\n")

    partial = _inspect_development_state_migration_v1(
        development_root=root, destination=paths
    )
    assert partial.status == "ready"
    assert partial.settings_eligible
    assert not partial.source_eligible

    paths.settings_path.write_bytes(DEFAULTS.read_bytes())
    with pytest.raises(_WindowsStateMigrationError) as raised:
        _execute_development_state_migration_v1(plan=partial)
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None
    assert not paths.migration_receipt_path.exists()


def test_receipt_is_final_success_authority(tmp_path: Path) -> None:
    root, paths = _layout(tmp_path)
    settings = root / "config" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_bytes(DEFAULTS.read_bytes())
    result = _execute_development_state_migration_v1(
        plan=_inspect_development_state_migration_v1(
            development_root=root, destination=paths
        )
    )
    receipt = json.loads(paths.migration_receipt_path.read_text(encoding="utf-8"))
    assert result.settings_copied
    assert receipt["settings_copied"] is True
    assert not paths.migration_pending_path.exists()


def test_development_destination_is_rejected(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    paths = _resolve_windows_application_paths_v1(
        frozen=False,
        environment={},
        bundled_application_root=None,
        development_root=root,
    )
    with pytest.raises(_WindowsStateMigrationError):
        _inspect_development_state_migration_applicability_v1(destination=paths)
    with pytest.raises(_WindowsStateMigrationError):
        _inspect_development_state_migration_v1(
            development_root=root, destination=paths
        )


def test_database_gate_migrates_exact_lower_schema_once(tmp_path: Path) -> None:
    from pastila_scout.database import initialize_database

    database = (tmp_path / "news_monitor.db").resolve()
    backups = (tmp_path / "backups").resolve()
    backups.mkdir()
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    initialize_database(connection)
    connection.close()
    migrated = _migrate_windows_database_v1(
        database_path=database, backup_directory=backups
    )
    assert migrated.status == "migrated"
    assert len(tuple(backups.glob("news_monitor-v0-*.db"))) == 1
    current = _migrate_windows_database_v1(
        database_path=database, backup_directory=backups
    )
    assert current.status == "current"
    assert len(tuple(backups.glob("news_monitor-v0-*.db"))) == 1


def test_database_gate_rejects_unknown_schema_without_backup(tmp_path: Path) -> None:
    database = (tmp_path / "news_monitor.db").resolve()
    backups = (tmp_path / "backups").resolve()
    backups.mkdir()
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE unknown(value TEXT)")
    connection.commit()
    connection.close()
    result = _migrate_windows_database_v1(
        database_path=database, backup_directory=backups
    )
    assert result.status == "unsupported"
    assert not tuple(backups.iterdir())


def _layout(tmp_path: Path):
    development = (tmp_path / "development").resolve()
    development.mkdir()
    local = (tmp_path / "local").resolve()
    roaming = (tmp_path / "roaming").resolve()
    local.mkdir()
    roaming.mkdir()
    app = (local / "Programs" / "PastilaScout" / "app").resolve()
    (app / "config").mkdir(parents=True)
    (app / "desktop_v1").mkdir()
    (app / "config" / "config.yaml").write_text("polling: {}\n", encoding="utf-8")
    shutil.copyfile(SOURCES, app / "config" / "sources.yaml")
    shutil.copyfile(DEFAULTS, app / "desktop_v1" / "default-settings-v1.json")
    paths = _resolve_windows_application_paths_v1(
        frozen=True,
        environment={"LOCALAPPDATA": str(local), "APPDATA": str(roaming)},
        bundled_application_root=app,
        development_root=None,
    )
    _create_windows_application_directories_v1(paths=paths)
    return development, paths


def _write_receipt(paths, *, schema_version: int = 1) -> None:
    paths.migration_receipt_path.write_text(
        json.dumps(
            {
                "schema": "pastila-scout-development-migration",
                "schema_version": schema_version,
                "operation_id": "d" * 32,
                "database_copied": False,
                "reports_copied": 0,
                "settings_copied": False,
                "source_override_seeded": False,
                "completed_at": "2026-08-08T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )


def _pending_json(*, operation: str) -> str:
    return json.dumps(
        {
            "schema": "pastila-scout-development-migration-pending",
            "schema_version": 1,
            "operation_id": operation,
            "artifacts": [],
        }
    )
