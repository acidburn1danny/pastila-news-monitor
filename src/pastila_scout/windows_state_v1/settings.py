"""Strict private Windows application settings."""

from __future__ import annotations

import json
import math
import os
import unicodedata
import uuid
from dataclasses import dataclass, fields
from pathlib import Path
from typing import NoReturn

from .errors import _WindowsStateSettingsError

_NAMES = (
    "schema",
    "schema_version",
    "scout_period_days",
    "scout_category",
    "scout_provider",
    "ollama_base_url",
    "ollama_model",
    "scout_ai_timeout_seconds",
    "log_level",
    "editor_profile_path",
    "editor_context_path",
    "editor_generation_path",
    "editor_provider",
    "editor_model",
    "editor_timeout_seconds",
    "editor_output_directory",
    "updates_enabled",
)
_SCOUT_PROVIDER_NAMES = (
    "scout_provider",
    "ollama_base_url",
    "ollama_model",
    "scout_ai_timeout_seconds",
)
_LEGACY_NAMES = tuple(name for name in _NAMES if name not in _SCOUT_PROVIDER_NAMES)


@dataclass(frozen=True, slots=True, init=False, repr=False)
class WindowsSettingsV1:
    schema: str
    schema_version: int
    scout_period_days: int
    scout_category: str
    scout_provider: str
    ollama_base_url: str
    ollama_model: str
    scout_ai_timeout_seconds: float
    log_level: str
    editor_profile_path: Path | None
    editor_context_path: Path | None
    editor_generation_path: Path | None
    editor_provider: str
    editor_model: str
    editor_timeout_seconds: float
    editor_output_directory: Path | None
    updates_enabled: bool

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Windows settings cannot be subclassed")

    def __init__(self, **values: object) -> None:
        invalid = False
        try:
            if tuple(values) != _NAMES:
                raise TypeError
            checked = _validate(values)
        except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
            raise
        except Exception:  # noqa: BLE001 - fixed safe settings boundary
            invalid = True
        if invalid:
            del values, invalid
            raise _WindowsStateSettingsError() from None
        for name, value in checked.items():
            object.__setattr__(self, name, value)

    def __repr__(self) -> str:
        return (
            "WindowsSettingsV1(schema_version=1, "
            f"scout_period_days={self.scout_period_days!r}, "
            f"scout_category={self.scout_category!r}, log_level={self.log_level!r}, "
            "paths=<redacted>, editor_model=<redacted>)"
        )

    def __copy__(self):
        return _reconstruct_windows_settings_v1(self)

    def __deepcopy__(self, memo):
        del memo
        return _reconstruct_windows_settings_v1(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("WindowsSettingsV1 does not support pickle")


def _default_windows_settings_v1(*, defaults_path: Path) -> WindowsSettingsV1:
    return _read_settings(defaults_path)


def _reconstruct_windows_settings_v1(value: object) -> WindowsSettingsV1:
    invalid = False
    try:
        if type(value) is not WindowsSettingsV1:
            raise TypeError
        return WindowsSettingsV1(
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
        raise _WindowsStateSettingsError() from None
    raise AssertionError("unreachable")


def _load_windows_settings_v1(*, path: Path, defaults_path: Path) -> WindowsSettingsV1:
    invalid = False
    try:
        if not isinstance(path, Path) or not isinstance(defaults_path, Path):
            raise TypeError
        if not path.exists():
            return _default_windows_settings_v1(defaults_path=defaults_path)
        return _read_settings(path)
    except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        raise
    except _WindowsStateSettingsError:
        raise
    except Exception:  # noqa: BLE001 - fixed safe settings boundary
        invalid = True
    if invalid:
        del path, defaults_path, invalid
        raise _WindowsStateSettingsError() from None
    raise AssertionError("unreachable")


def _save_windows_settings_v1(*, path: Path, settings: WindowsSettingsV1) -> None:
    temporary: Path | None = None
    backup_published = False
    invalid = False
    try:
        if not isinstance(path, Path) or not path.is_absolute():
            raise TypeError
        valid = _reconstruct_windows_settings_v1(settings)
        parent = path.parent
        if not parent.is_dir() or parent.is_symlink():
            raise OSError
        if path.exists() and (not path.is_file() or path.is_symlink()):
            raise OSError
        backup = path.with_name("settings.json.bak")
        temporary = path.with_name(f".settings.json.{uuid.uuid4().hex}.tmp")
        payload = _encode(valid)
        with temporary.open("xb") as stream:
            stream.write(payload)
            stream.flush()
        if path.exists():
            os.replace(path, backup)
            backup_published = True
        try:
            os.replace(temporary, path)
            temporary = None
        except BaseException:
            if backup_published:
                os.replace(backup, path)
            raise
    except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise
    except Exception:  # noqa: BLE001 - fixed safe filesystem boundary
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        invalid = True
    if invalid:
        del path, settings, temporary, invalid
        raise _WindowsStateSettingsError() from None


def _read_settings(path: Path) -> WindowsSettingsV1:
    invalid = False
    try:
        if not isinstance(path, Path) or not path.is_file() or path.is_symlink():
            raise OSError
        payload = path.read_bytes()
        if not payload or len(payload) > 65_536 or payload.startswith(b"\xef\xbb\xbf"):
            raise ValueError
        text = payload.decode("utf-8", errors="strict")
        pairs = json.loads(
            text,
            object_pairs_hook=lambda items: items,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
        if type(pairs) is not list or any(type(item) is not tuple for item in pairs):
            raise ValueError
        names = tuple(name for name, _ in pairs)
        if names not in {_NAMES, _LEGACY_NAMES} or len(set(names)) != len(names):
            raise ValueError
        values = dict(pairs)
        if names == _LEGACY_NAMES:
            values.update(
                scout_provider="openai",
                ollama_base_url="http://localhost:11434",
                ollama_model="qwen3:14b",
                scout_ai_timeout_seconds=120.0,
            )
            values = {name: values[name] for name in _NAMES}
        return WindowsSettingsV1(**values)
    except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        raise
    except Exception:  # noqa: BLE001 - fixed safe parser boundary
        invalid = True
    if invalid:
        del path, invalid
        raise _WindowsStateSettingsError() from None
    raise AssertionError("unreachable")


def _validate(values: dict[str, object]) -> dict[str, object]:
    if (
        values["schema"] != "pastila-scout-settings"
        or type(values["schema"]) is not str
    ):
        raise TypeError
    if type(values["schema_version"]) is not int or values["schema_version"] != 1:
        raise TypeError
    if type(values["scout_period_days"]) is not int or values[
        "scout_period_days"
    ] not in {1, 3, 7, 14, 30}:
        raise TypeError
    if type(values["scout_category"]) is not str or values["scout_category"] not in {
        "Politica",
        "Social",
        "Conspiratii",
        "Economie",
        "CanCan",
        "Externe",
        "Diverse",
        "all",
    }:
        raise TypeError
    if type(values["log_level"]) is not str or values["log_level"] not in {
        "ERROR",
        "WARNING",
        "INFO",
    }:
        raise TypeError
    if values["scout_provider"] not in {"openai", "ollama"}:
        raise TypeError
    if type(values["ollama_base_url"]) is not str or not values[
        "ollama_base_url"
    ].startswith(("http://", "https://")):
        raise TypeError
    if type(values["ollama_model"]) is not str or not 1 <= len(
        values["ollama_model"].encode("utf-8")
    ) <= 200:
        raise TypeError
    scout_timeout = values["scout_ai_timeout_seconds"]
    if (
        type(scout_timeout) is not float
        or not math.isfinite(scout_timeout)
        or not 0 < scout_timeout <= 3600
    ):
        raise TypeError
    if type(values["editor_provider"]) is not str or values["editor_provider"] not in {
        "openai",
        "ollama",
    }:
        raise TypeError
    model = values["editor_model"]
    if type(model) is not str or not 1 <= len(model.encode("utf-8")) <= 128:
        raise TypeError
    timeout = values["editor_timeout_seconds"]
    if (
        type(timeout) is not float
        or not math.isfinite(timeout)
        or not 0 < timeout <= 3600
    ):
        raise TypeError
    if type(values["updates_enabled"]) is not bool:
        raise TypeError
    checked = dict(values)
    for name, value in values.items():
        if type(value) is str and (
            value != value.strip()
            or value != unicodedata.normalize("NFC", value)
            or _unsafe_text(value)
        ):
            raise TypeError
    for name in (
        "editor_profile_path",
        "editor_context_path",
        "editor_generation_path",
        "editor_output_directory",
    ):
        value = values[name]
        if value is not None:
            if type(value) is str:
                value = Path(value)
            if (
                not isinstance(value, Path)
                or not value.is_absolute()
                or _unsafe_text(str(value))
            ):
                raise TypeError
            checked[name] = value
    return checked


def _unsafe_text(value: str) -> bool:
    return not value or any(
        ord(char) < 32 or 127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF
        for char in value
    )


def _encode(settings: WindowsSettingsV1) -> bytes:
    values = {
        name: (str(value) if isinstance(value, Path) else value)
        for name in _NAMES
        for value in (object.__getattribute__(settings, name),)
    }
    return (
        json.dumps(
            values,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
            separators=(",", ": "),
        )
        + "\n"
    ).encode("utf-8")


__all__: tuple[str, ...] = ()
