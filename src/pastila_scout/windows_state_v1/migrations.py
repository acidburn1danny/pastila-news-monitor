"""Explicit passive development-state and SQLite migration APIs."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import threading
import uuid
from dataclasses import dataclass, fields
from datetime import UTC, datetime
from pathlib import Path
from typing import NoReturn

from pastila_scout.active_project_v1 import ActiveProjectStoreV1
from pastila_scout.config import load_sources_config

from .errors import _WindowsStateMigrationError
from .paths import (
    WindowsApplicationPathsV1,
    _reconstruct_windows_application_paths_v1,
)
from .settings import _load_windows_settings_v1

TARGET_SCHEMA_VERSION = 1
_DATABASE_MUTEX = threading.Lock()


class _SafeValue:
    def __init_subclass__(cls, **kwargs) -> None:
        if cls.__module__ == __name__:
            return super().__init_subclass__(**kwargs)
        del cls, kwargs
        raise TypeError("Migration values cannot be subclassed")

    def __copy__(self):
        return type(self)(
            **{
                item.name: object.__getattribute__(self, item.name)
                for item in fields(type(self))
            }
        )

    def __deepcopy__(self, memo):
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("Migration values do not support pickle")


@dataclass(frozen=True, slots=True)
class DevelopmentMigrationApplicabilityV1:
    status: str

    def __post_init__(self) -> None:
        if type(self.status) is not str or self.status not in {
            "development_root_required",
            "already_migrated",
        }:
            raise _WindowsStateMigrationError() from None

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("DevelopmentMigrationApplicabilityV1 cannot be subclassed")

    def __copy__(self):
        return type(self)(self.status)

    def __deepcopy__(self, memo):
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("DevelopmentMigrationApplicabilityV1 does not support pickle")


@dataclass(frozen=True, slots=True, repr=False)
class DevelopmentMigrationPlanV1(_SafeValue):
    status: str
    database_available: bool
    reports_available: bool
    settings_available: bool
    source_available: bool
    active_project_available: bool
    database_eligible: bool
    reports_eligible: bool
    settings_eligible: bool
    source_eligible: bool
    active_project_eligible: bool
    _development_root: Path
    _destination: WindowsApplicationPathsV1

    def __post_init__(self) -> None:
        if (
            type(self.status) is not str
            or self.status
            not in {
                "nothing_to_migrate",
                "ready",
                "destination_occupied",
                "already_migrated",
            }
            or any(type(getattr(self, item)) is not bool for item in _PLAN_BOOLS)
            or not isinstance(self._development_root, Path)
            or not self._development_root.is_absolute()
        ):
            raise _WindowsStateMigrationError() from None
        _reconstruct_windows_application_paths_v1(self._destination)

    def __repr__(self) -> str:
        return f"DevelopmentMigrationPlanV1(status={self.status!r}, sources=<redacted>, paths=<redacted>)"

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("DevelopmentMigrationPlanV1 cannot be subclassed")


@dataclass(frozen=True, slots=True)
class DevelopmentMigrationResultV1(_SafeValue):
    status: str
    database_copied: bool
    reports_copied: int
    settings_copied: bool
    source_override_seeded: bool
    active_project_copied: bool

    def __post_init__(self) -> None:
        if (
            self.status
            not in {
                "nothing_to_migrate",
                "destination_occupied",
                "already_migrated",
                "completed",
            }
            or type(self.database_copied) is not bool
            or type(self.reports_copied) is not int
            or self.reports_copied < 0
            or type(self.settings_copied) is not bool
            or type(self.source_override_seeded) is not bool
            or type(self.active_project_copied) is not bool
        ):
            raise _WindowsStateMigrationError() from None

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("DevelopmentMigrationResultV1 cannot be subclassed")


@dataclass(frozen=True, slots=True)
class DatabaseMigrationResultV1(_SafeValue):
    status: str
    source_version: int
    target_version: int

    def __post_init__(self) -> None:
        if self.status not in {"current", "migrated", "unsupported"} or any(
            type(value) is not int or value < 0
            for value in (self.source_version, self.target_version)
        ):
            raise _WindowsStateMigrationError() from None

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("DatabaseMigrationResultV1 cannot be subclassed")


_PLAN_BOOLS = (
    "database_available",
    "reports_available",
    "settings_available",
    "source_available",
    "active_project_available",
    "database_eligible",
    "reports_eligible",
    "settings_eligible",
    "source_eligible",
    "active_project_eligible",
)


def _inspect_development_state_migration_applicability_v1(
    *, destination: WindowsApplicationPathsV1
) -> DevelopmentMigrationApplicabilityV1:
    """Recover installed migration state and validate any completed receipt."""

    invalid = False
    try:
        paths = _reconstruct_windows_application_paths_v1(destination)
        if paths.mode != "installed":
            raise ValueError
        _recover_pending(paths)
        if paths.migration_receipt_path.exists():
            _read_receipt(paths.migration_receipt_path)
            return DevelopmentMigrationApplicabilityV1("already_migrated")
        return DevelopmentMigrationApplicabilityV1("development_root_required")
    except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        raise
    except Exception:  # noqa: BLE001 - fixed safe migration boundary
        invalid = True
    if invalid:
        del destination, invalid
        raise _WindowsStateMigrationError() from None
    raise AssertionError("unreachable")


def _inspect_development_state_migration_v1(
    *, development_root: Path, destination: WindowsApplicationPathsV1
) -> DevelopmentMigrationPlanV1:
    invalid = False
    try:
        paths = _reconstruct_windows_application_paths_v1(destination)
        if (
            paths.mode != "installed"
            or not isinstance(development_root, Path)
            or not development_root.is_absolute()
            or not development_root.is_dir()
        ):
            raise ValueError
        applicability = _inspect_development_state_migration_applicability_v1(
            destination=paths
        )
        if applicability.status == "already_migrated":
            return _plan("already_migrated", development_root, paths)
        database = development_root / "data" / "news_monitor.db"
        reports = development_root / "reports"
        settings = development_root / "config" / "settings.json"
        source = development_root / "config" / "sources.yaml"
        active_project = development_root / "data" / "active-project-v1.json"
        available = {
            "database": _regular_optional(database),
            "reports": _reports_optional(reports),
            "settings": _regular_optional(settings),
            "source": _regular_optional(source),
            "active_project": _active_project_optional(
                active_project, database, development_root / "reports"
            ),
        }
        if available["source"]:
            load_sources_config(source)
        if available["settings"]:
            _load_windows_settings_v1(
                path=settings, defaults_path=paths.settings_defaults_path
            )
        eligible = {
            "database": available["database"] and not paths.database_path.exists(),
            "reports": available["reports"]
            and (
                not paths.report_directory.exists()
                or not any(paths.report_directory.iterdir())
            ),
            "settings": available["settings"] and not paths.settings_path.exists(),
            "source": available["source"] and not paths.source_override_path.exists(),
            "active_project": available["active_project"]
            and not (paths.database_path.parent / "active-project-v1.json").exists()
            and _active_project_outputs_available(
                active_project, paths.report_directory
            ),
        }
        if any(eligible.values()):
            status = "ready"
        elif any(available.values()):
            status = "destination_occupied"
        else:
            status = "nothing_to_migrate"
        return DevelopmentMigrationPlanV1(
            status=status,
            **{f"{name}_available": value for name, value in available.items()},
            **{f"{name}_eligible": value for name, value in eligible.items()},
            _development_root=development_root,
            _destination=paths,
        )
    except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        raise
    except Exception:  # noqa: BLE001 - fixed safe migration boundary
        invalid = True
    if invalid:
        del development_root, destination, invalid
        raise _WindowsStateMigrationError() from None
    raise AssertionError("unreachable")


def _execute_development_state_migration_v1(
    *, plan: DevelopmentMigrationPlanV1
) -> DevelopmentMigrationResultV1:
    invalid = False
    try:
        valid = _reconstruct_plan(plan)
        if valid.status != "ready":
            return DevelopmentMigrationResultV1(
                valid.status, False, 0, False, False, False
            )
        fresh = _inspect_development_state_migration_v1(
            development_root=valid._development_root, destination=valid._destination
        )
        if fresh != valid:
            raise ValueError
        operation = uuid.uuid4().hex
        paths = valid._destination
        local_stage = paths.local_state_root / f".development-migration-{operation}"
        roaming_stage = paths.roaming_state_root / f".development-migration-{operation}"
        local_stage.mkdir(exist_ok=False)
        roaming_stage.mkdir(exist_ok=False)
        artifacts: list[tuple[str, Path, Path]] = []
        root = valid._development_root
        if valid.database_eligible:
            artifacts.append(
                (
                    "local",
                    _copy(
                        root / "data" / "news_monitor.db",
                        local_stage / "data" / "news_monitor.db",
                    ),
                    paths.database_path,
                )
            )
        report_count = 0
        if valid.reports_eligible:
            for source in sorted(
                (root / "reports").iterdir(), key=lambda item: item.name
            ):
                if (
                    not source.is_file()
                    or source.is_symlink()
                    or source.suffix.lower() != ".html"
                ):
                    raise ValueError
                artifacts.append(
                    (
                        "local",
                        _copy(source, local_stage / "reports" / source.name),
                        paths.report_directory / source.name,
                    )
                )
                report_count += 1
        if valid.settings_eligible:
            staged = _copy(
                root / "config" / "settings.json", roaming_stage / "settings.json"
            )
            _load_windows_settings_v1(
                path=staged, defaults_path=paths.settings_defaults_path
            )
            artifacts.append(("roaming", staged, paths.settings_path))
        if valid.source_eligible:
            staged = _copy(
                root / "config" / "sources.yaml",
                roaming_stage / "sources.override.yaml",
            )
            load_sources_config(staged)
            artifacts.append(("roaming", staged, paths.source_override_path))
        if valid.active_project_eligible:
            project_source = root / "data" / "active-project-v1.json"
            project = json.loads(project_source.read_text(encoding="utf-8"))
            for material in project.get("editor_materials", ()):
                output = material.get("output_path")
                if output is None:
                    continue
                source_output = Path(output)
                destination_output = paths.report_directory / source_output.name
                artifacts.append(
                    (
                        "local",
                        _copy(source_output, local_stage / "reports" / source_output.name),
                        destination_output,
                    )
                )
                material["output_path"] = str(destination_output)
            staged_project = local_stage / "data" / "active-project-v1.json"
            staged_project.parent.mkdir(parents=True, exist_ok=True)
            staged_project.write_text(
                json.dumps(project, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            ActiveProjectStoreV1(
                database_path=paths.database_path,
                project_path=staged_project,
            ).load()
            artifacts.append(
                (
                    "local",
                    staged_project,
                    paths.database_path.parent / "active-project-v1.json",
                )
            )
        journal = _journal(operation, artifacts, paths)
        _publish_json(paths.migration_pending_path, journal)
        for _, staged, destination in artifacts:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise FileExistsError
            os.replace(staged, destination)
        receipt = {
            "schema": "pastila-scout-development-migration",
            "schema_version": 1,
            "operation_id": operation,
            "database_copied": valid.database_eligible,
            "reports_copied": report_count,
            "settings_copied": valid.settings_eligible,
            "source_override_seeded": valid.source_eligible,
            "active_project_copied": valid.active_project_eligible,
            "completed_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        _publish_json(paths.migration_receipt_path, receipt)
        paths.migration_pending_path.unlink()
        shutil.rmtree(local_stage, ignore_errors=True)
        shutil.rmtree(roaming_stage, ignore_errors=True)
        return DevelopmentMigrationResultV1(
            "completed",
            valid.database_eligible,
            report_count,
            valid.settings_eligible,
            valid.source_eligible,
            valid.active_project_eligible,
        )
    except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        raise
    except Exception:  # noqa: BLE001 - fixed safe migration boundary
        try:
            if "paths" in locals():
                _recover_pending(paths)
            if "local_stage" in locals():
                shutil.rmtree(local_stage, ignore_errors=True)
            if "roaming_stage" in locals():
                shutil.rmtree(roaming_stage, ignore_errors=True)
        except Exception:  # noqa: BLE001, S110 - preserve primary safe failure
            pass
        invalid = True
    if invalid:
        del plan, invalid
        raise _WindowsStateMigrationError() from None
    raise AssertionError("unreachable")


def _migrate_windows_database_v1(
    *, database_path: Path, backup_directory: Path
) -> DatabaseMigrationResultV1:
    invalid = False
    try:
        if (
            not isinstance(database_path, Path)
            or not isinstance(backup_directory, Path)
            or not database_path.is_file()
            or not backup_directory.is_dir()
        ):
            raise ValueError
        with _DATABASE_MUTEX:
            connection = sqlite3.connect(database_path)
            connection.row_factory = sqlite3.Row
            try:
                if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError
                version = connection.execute("PRAGMA user_version").fetchone()[0]
                if type(version) is not int or version > TARGET_SCHEMA_VERSION:
                    return DatabaseMigrationResultV1(
                        "unsupported", max(int(version), 0), TARGET_SCHEMA_VERSION
                    )
                if version == TARGET_SCHEMA_VERSION:
                    return DatabaseMigrationResultV1(
                        "current", version, TARGET_SCHEMA_VERSION
                    )
                if version != 0 or not _recognized_database(connection):
                    return DatabaseMigrationResultV1(
                        "unsupported", 0, TARGET_SCHEMA_VERSION
                    )
                size = database_path.stat().st_size
                if (
                    shutil.disk_usage(backup_directory).free
                    < size * 2 + 100 * 1024 * 1024
                ):
                    raise OSError
                timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                temporary = (
                    backup_directory / f".news_monitor-v0-{uuid.uuid4().hex}.tmp"
                )
                target = sqlite3.connect(temporary)
                try:
                    connection.backup(target)
                finally:
                    target.close()
                digest = hashlib.sha256(temporary.read_bytes()).hexdigest()
                backup = backup_directory / f"news_monitor-v0-{timestamp}-{digest}.db"
                os.replace(temporary, backup)
                validation = sqlite3.connect(
                    f"file:{backup.as_posix()}?mode=ro", uri=True
                )
                try:
                    valid_backup = validation.execute("PRAGMA quick_check").fetchone()[
                        0
                    ]
                finally:
                    validation.close()
                if (
                    valid_backup != "ok"
                    or hashlib.sha256(backup.read_bytes()).hexdigest() != digest
                ):
                    raise ValueError
                connection.execute("BEGIN EXCLUSIVE")
                _migrate_0_to_1(connection)
                if (
                    connection.execute("PRAGMA foreign_key_check").fetchone()
                    is not None
                    or connection.execute("PRAGMA quick_check").fetchone()[0] != "ok"
                ):
                    raise ValueError
                connection.commit()
                return DatabaseMigrationResultV1("migrated", 0, TARGET_SCHEMA_VERSION)
            except BaseException:
                connection.rollback()
                raise
            finally:
                connection.close()
    except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        raise
    except Exception:  # noqa: BLE001 - fixed safe database boundary
        invalid = True
    if invalid:
        del database_path, backup_directory, invalid
        raise _WindowsStateMigrationError() from None
    raise AssertionError("unreachable")


def _migrate_0_to_1(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA user_version = 1")


MIGRATIONS = {0: _migrate_0_to_1}


def _recognized_database(connection: sqlite3.Connection) -> bool:
    from pastila_scout.database import initialize_database

    reference = sqlite3.connect(":memory:")
    reference.row_factory = sqlite3.Row
    try:
        initialize_database(reference)
        return _schema_rows(connection) == _schema_rows(reference)
    finally:
        reference.close()


def _schema_rows(connection: sqlite3.Connection) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        tuple(row)
        for row in connection.execute(
            """SELECT type, name,
                      replace(replace(sql, char(10), ' '), char(13), '')
               FROM sqlite_master
               WHERE name NOT LIKE 'sqlite_%' AND sql IS NOT NULL
               ORDER BY type, name"""
        ).fetchall()
    )


def _regular_optional(path: Path) -> bool:
    if not path.exists():
        return False
    if not path.is_file() or path.is_symlink():
        raise ValueError
    return True


def _reports_optional(path: Path) -> bool:
    if not path.exists():
        return False
    if not path.is_dir() or path.is_symlink():
        raise ValueError
    return any(
        item.is_file() and not item.is_symlink() and item.suffix.lower() == ".html"
        for item in path.iterdir()
    )


def _active_project_optional(path: Path, database: Path, reports: Path) -> bool:
    if not _regular_optional(path):
        return False
    project = ActiveProjectStoreV1(database_path=database, project_path=path).load()
    if project is None:
        raise ValueError
    report_root = reports.resolve()
    for material in project.editor_materials:
        if material.output_path is None:
            continue
        output = Path(material.output_path)
        if (
            not output.is_absolute()
            or not output.is_file()
            or output.is_symlink()
            or output.parent.resolve() != report_root
        ):
            raise ValueError
    return True


def _active_project_outputs_available(path: Path, destination: Path) -> bool:
    project = ActiveProjectStoreV1(
        database_path=path.parent / "news_monitor.db", project_path=path
    ).load()
    return project is not None and all(
        material.output_path is None
        or not (destination / Path(material.output_path).name).exists()
        for material in project.editor_materials
    )


def _plan(
    status: str, root: Path, paths: WindowsApplicationPathsV1
) -> DevelopmentMigrationPlanV1:
    return DevelopmentMigrationPlanV1(
        status, *(False for _ in _PLAN_BOOLS), root, paths
    )


def _reconstruct_plan(value: object) -> DevelopmentMigrationPlanV1:
    if type(value) is not DevelopmentMigrationPlanV1:
        raise _WindowsStateMigrationError() from None
    return DevelopmentMigrationPlanV1(
        **{
            item.name: object.__getattribute__(value, item.name)
            for item in fields(type(value))
        }
    )


def _copy(source: Path, destination: Path) -> Path:
    if not source.is_file() or source.is_symlink():
        raise ValueError
    destination.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as reader, destination.open("xb") as writer:
        shutil.copyfileobj(reader, writer)
    return destination


def _journal(
    operation: str,
    artifacts: list[tuple[str, Path, Path]],
    paths: WindowsApplicationPathsV1,
) -> dict[str, object]:
    rows = []
    for kind, staged, destination in artifacts:
        root = paths.local_state_root if kind == "local" else paths.roaming_state_root
        rows.append(
            {
                "destination_kind": kind,
                "relative_path": destination.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(staged.read_bytes()).hexdigest(),
            }
        )
    rows.sort(key=lambda row: (row["destination_kind"], row["relative_path"]))
    return {
        "schema": "pastila-scout-development-migration-pending",
        "schema_version": 1,
        "operation_id": operation,
        "artifacts": rows,
    }


def _publish_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_bytes(
        (
            json.dumps(value, ensure_ascii=False, indent=2, separators=(",", ": "))
            + "\n"
        ).encode()
    )
    os.replace(temporary, path)


def _recover_pending(paths: WindowsApplicationPathsV1) -> None:
    journal = paths.migration_pending_path
    if not journal.exists():
        return
    value = json.loads(journal.read_text(encoding="utf-8"))
    if (
        type(value) is not dict
        or tuple(value) != ("schema", "schema_version", "operation_id", "artifacts")
        or value["schema"] != "pastila-scout-development-migration-pending"
        or value["schema_version"] != 1
        or type(value["artifacts"]) is not list
    ):
        raise ValueError
    for row in value["artifacts"]:
        if type(row) is not dict or tuple(row) != (
            "destination_kind",
            "relative_path",
            "sha256",
        ):
            raise ValueError
        root = (
            paths.local_state_root
            if row["destination_kind"] == "local"
            else (
                paths.roaming_state_root
                if row["destination_kind"] == "roaming"
                else None
            )
        )
        if (
            root is None
            or type(row["relative_path"]) is not str
            or ".." in Path(row["relative_path"]).parts
        ):
            raise ValueError
        target = root / row["relative_path"]
        if target.exists():
            if (
                not target.is_file()
                or hashlib.sha256(target.read_bytes()).hexdigest() != row["sha256"]
            ):
                raise ValueError
            target.unlink()
    operation = value["operation_id"]
    shutil.rmtree(
        paths.local_state_root / f".development-migration-{operation}",
        ignore_errors=True,
    )
    shutil.rmtree(
        paths.roaming_state_root / f".development-migration-{operation}",
        ignore_errors=True,
    )
    journal.unlink()


def _read_receipt(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    legacy_names = (
        "schema",
        "schema_version",
        "operation_id",
        "database_copied",
        "reports_copied",
        "settings_copied",
        "source_override_seeded",
        "completed_at",
    )
    names = legacy_names[:-1] + ("active_project_copied", "completed_at")
    if (
        type(value) is not dict
        or tuple(value) not in {legacy_names, names}
        or value["schema"] != "pastila-scout-development-migration"
        or value["schema_version"] != 1
    ):
        raise ValueError
    return value


__all__: tuple[str, ...] = ()
