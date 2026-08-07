"""Deterministic passive Windows application paths."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, fields
from pathlib import Path
from typing import NoReturn

from .errors import _WindowsStatePathError

_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {
    f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
}
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")


@dataclass(frozen=True, slots=True, init=False, repr=False)
class WindowsApplicationPathsV1:
    mode: str
    installation_root: Path
    scout_application_config_path: Path
    bundled_source_path: Path
    local_state_root: Path
    roaming_state_root: Path
    database_path: Path
    database_backup_directory: Path
    report_directory: Path
    cache_directory: Path
    log_directory: Path
    settings_defaults_path: Path
    settings_path: Path
    settings_backup_path: Path
    source_override_path: Path
    migration_pending_path: Path
    migration_receipt_path: Path

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Windows application paths cannot be subclassed")

    def __init__(self, **values: object) -> None:
        names = tuple(item.name for item in fields(type(self)))
        invalid = False
        try:
            if tuple(values) != names or values["mode"] not in {
                "installed",
                "development",
            }:
                raise TypeError
            for name in names[1:]:
                value = values[name]
                if not isinstance(value, Path) or not value.is_absolute():
                    raise TypeError
                _validate_path(value)
        except (Exception, MemoryError) as exc:
            if isinstance(exc, MemoryError):
                raise
            invalid = True
        if invalid:
            del values, names, invalid
            raise _WindowsStatePathError() from None
        for name in names:
            object.__setattr__(self, name, values[name])

    def __repr__(self) -> str:
        return f"WindowsApplicationPathsV1(mode={self.mode!r}, paths=<redacted>)"

    def __copy__(self):
        return _reconstruct_windows_application_paths_v1(self)

    def __deepcopy__(self, memo):
        del memo
        return _reconstruct_windows_application_paths_v1(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("WindowsApplicationPathsV1 does not support pickle")


def _resolve_windows_application_paths_v1(
    *,
    frozen: bool,
    environment: Mapping[str, str],
    bundled_application_root: Path | None,
    development_root: Path | None,
) -> WindowsApplicationPathsV1:
    """Resolve one explicit installed or development path authority."""

    invalid = False
    try:
        if type(frozen) is not bool or not isinstance(environment, Mapping):
            raise TypeError
        if frozen:
            if development_root is not None or not isinstance(
                bundled_application_root, Path
            ):
                raise TypeError
            installation = _absolute_directory(bundled_application_root)
            local_base = _environment_directory(environment, "LOCALAPPDATA")
            roaming_base = _environment_directory(environment, "APPDATA")
            expected_installation = _join(local_base, "Programs", "PastilaScout", "app")
            if installation != expected_installation:
                raise OSError
            local = _join(local_base, "PastilaScout")
            roaming = _join(roaming_base, "PastilaScout")
            app_config = _join(installation, "config", "config.yaml")
            sources = _join(installation, "config", "sources.yaml")
            defaults = _join(installation, "desktop_v1", "default-settings-v1.json")
            if not all(path.is_file() for path in (app_config, sources, defaults)):
                raise OSError
            mode = "installed"
        else:
            if bundled_application_root is not None or not isinstance(
                development_root, Path
            ):
                raise TypeError
            installation = _absolute_directory(development_root)
            local = installation
            roaming = _join(installation, "config")
            app_config = _join(installation, "config", "config.yaml")
            sources = _join(installation, "config", "sources.yaml")
            defaults = _join(
                installation,
                "src",
                "pastila_scout",
                "desktop_v1",
                "default-settings-v1.json",
            )
            mode = "development"
        data = _join(local, "data")
        settings = _join(roaming, "settings.json")
        return WindowsApplicationPathsV1(
            mode=mode,
            installation_root=installation,
            scout_application_config_path=app_config,
            bundled_source_path=sources,
            local_state_root=local,
            roaming_state_root=roaming,
            database_path=_join(data, "news_monitor.db"),
            database_backup_directory=_join(data, "backups"),
            report_directory=_join(local, "reports"),
            cache_directory=(
                _join(local, "cache") if frozen else _join(local, "data", "ai_cache")
            ),
            log_directory=_join(local, "logs"),
            settings_defaults_path=defaults,
            settings_path=settings,
            settings_backup_path=_join(roaming, "settings.json.bak"),
            source_override_path=_join(roaming, "sources.override.yaml"),
            migration_pending_path=_join(data, "development-migration-v1.pending.json"),
            migration_receipt_path=_join(data, "development-migration-v1.json"),
        )
    except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        raise
    except Exception:  # noqa: BLE001 - fixed safe path boundary
        invalid = True
    if invalid:
        del environment, bundled_application_root, development_root, invalid
        raise _WindowsStatePathError() from None
    raise AssertionError("unreachable")


def _reconstruct_windows_application_paths_v1(
    value: object,
) -> WindowsApplicationPathsV1:
    invalid = False
    try:
        if type(value) is not WindowsApplicationPathsV1:
            raise TypeError
        return WindowsApplicationPathsV1(
            **{
                item.name: object.__getattribute__(value, item.name)
                for item in fields(type(value))
            }
        )
    except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state boundary
        invalid = True
    if invalid:
        del value, invalid
        raise _WindowsStatePathError() from None
    raise AssertionError("unreachable")


def _create_windows_application_directories_v1(
    *, paths: WindowsApplicationPathsV1
) -> None:
    valid = _reconstruct_windows_application_paths_v1(paths)
    directories = (
        valid.local_state_root,
        valid.roaming_state_root,
        valid.database_path.parent,
        valid.database_backup_directory,
        valid.report_directory,
        valid.cache_directory,
        valid.log_directory,
    )
    invalid = False
    try:
        for directory in directories:
            _reject_reparse_ancestors(directory)
            directory.mkdir(parents=True, exist_ok=True)
            if not directory.is_dir() or directory.is_symlink():
                raise OSError
    except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        raise
    except Exception:  # noqa: BLE001 - fixed safe filesystem boundary
        invalid = True
    if invalid:
        del valid, directories, invalid
        raise _WindowsStatePathError() from None


def _absolute_directory(value: Path) -> Path:
    if not isinstance(value, Path) or not value.is_absolute() or not value.is_dir():
        raise OSError
    normalized = Path(os.path.normpath(value))
    _validate_path(normalized)
    return normalized


def _environment_directory(environment: Mapping[str, str], name: str) -> Path:
    value = environment.get(name)
    if type(value) is not str or not value:
        raise OSError
    return _absolute_directory(Path(value))


def _join(root: Path, *parts: str) -> Path:
    for part in parts:
        if part in {"", ".", ".."} or "/" in part or "\\" in part:
            raise OSError
    value = Path(os.path.normpath(root.joinpath(*parts)))
    _validate_path(value)
    return value


def _validate_path(value: Path) -> None:
    text = str(value)
    if _CONTROL.search(text) or any(0xD800 <= ord(char) <= 0xDFFF for char in text):
        raise OSError
    if text.startswith(("\\\\", "\\\\?\\", "\\\\.\\")):
        raise OSError
    drive = value.drive
    remainder = text[len(drive) :]
    if ":" in remainder:
        raise OSError
    for part in value.parts[1:]:
        stem = part.rstrip(" .").split(".", 1)[0].upper()
        if part in {".", ".."} or stem in _RESERVED:
            raise OSError


def _reject_reparse_ancestors(path: Path) -> None:
    current = path
    while True:
        if current.exists():
            attributes = getattr(
                current.stat(follow_symlinks=False), "st_file_attributes", 0
            )
            if current.is_symlink() or attributes & 0x400:
                raise OSError
        if current.parent == current:
            return
        current = current.parent


__all__: tuple[str, ...] = ()
