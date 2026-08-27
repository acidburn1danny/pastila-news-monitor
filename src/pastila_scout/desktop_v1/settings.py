"""Passive projection and source selection for desktop Windows state."""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import NoReturn

from pastila_scout.config import load_sources_config
from pastila_scout.windows_state_v1.paths import (
    WindowsApplicationPathsV1,
    _reconstruct_windows_application_paths_v1,
)
from pastila_scout.windows_state_v1.settings import (
    WindowsSettingsV1,
    _reconstruct_windows_settings_v1,
)

from .source_settings import _rebase_scout_sources_override_v1


@dataclass(frozen=True, slots=True, init=False, repr=False)
class _DesktopSettingsProjectionV1:
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
    editor_default_model: str
    editor_timeout_seconds: float
    editor_output_directory: Path | None
    updates_enabled: bool

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop settings projections cannot be subclassed")

    def __init__(self, **values: object) -> None:
        names = tuple(item.name for item in fields(type(self)))
        if tuple(values) != names:
            raise TypeError("Invalid desktop settings projection")
        valid = _reconstruct_windows_settings_v1(WindowsSettingsV1(**values))
        for name in names:
            value = object.__getattribute__(valid, name)
            object.__setattr__(self, name, value)

    def __repr__(self) -> str:
        return (
            "_DesktopSettingsProjectionV1("
            f"schema_version={self.schema_version!r}, "
            f"scout_period_days={self.scout_period_days!r}, "
            f"scout_category={self.scout_category!r}, paths=<redacted>, "
            "editor_model=<redacted>)"
        )

    def __copy__(self):
        return _reconstruct_desktop_settings_projection_v1(self)

    def __deepcopy__(self, memo):
        del memo
        return _reconstruct_desktop_settings_projection_v1(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("Desktop settings projections do not support pickle")


def _project_desktop_settings_v1(
    *, settings: WindowsSettingsV1
) -> _DesktopSettingsProjectionV1:
    valid = _reconstruct_windows_settings_v1(settings)
    return _DesktopSettingsProjectionV1(
        **{
            item.name: object.__getattribute__(valid, item.name)
            for item in fields(WindowsSettingsV1)
        }
    )


def _reconstruct_desktop_settings_projection_v1(
    value: object,
) -> _DesktopSettingsProjectionV1:
    if type(value) is not _DesktopSettingsProjectionV1:
        raise TypeError("Invalid desktop settings projection")
    return _DesktopSettingsProjectionV1(
        **{
            item.name: object.__getattribute__(value, item.name)
            for item in fields(_DesktopSettingsProjectionV1)
        }
    )


def _select_scout_sources_path_v1(*, paths: WindowsApplicationPathsV1) -> Path:
    valid = _reconstruct_windows_application_paths_v1(paths)
    selected = _rebase_scout_sources_override_v1(
        canonical_path=valid.bundled_source_path,
        override_path=valid.source_override_path,
    )
    if (
        type(selected) is not type(Path())
        or not selected.is_absolute()
        or not selected.is_file()
        or selected.is_symlink()
        or getattr(selected.stat(follow_symlinks=False), "st_file_attributes", 0)
        & 0x400
    ):
        raise ValueError("Invalid Scout source authority")
    load_sources_config(selected)
    return selected


__all__: tuple[str, ...] = ()
