from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from pastila_scout.windows_state_v1.errors import _WindowsStateMigrationError
from pastila_scout.windows_state_v1.migrations import (
    _execute_development_state_migration_v1,
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
