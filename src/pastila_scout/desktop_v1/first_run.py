"""Local-only first-run readiness for the desktop application."""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

from pastila_scout.active_project_v1 import ActiveProjectStoreV1
from pastila_scout.ai.provider import resolve_openai_api_key
from pastila_scout.config import SourceConfig, load_sources_config
from pastila_scout.windows_state_v1.settings import (
    WindowsSettingsV1,
    _save_windows_settings_v1,
)


@dataclass(frozen=True, slots=True)
class _DesktopReadinessV1:
    setup_required: bool
    provider_ready: bool
    enabled_sources: tuple[SourceConfig, ...]
    sources: tuple[SourceConfig, ...]
    output_directory: Path
    active_project: object | None
    project_warning: str | None


def _inspect_desktop_readiness_v1(
    *,
    settings: object,
    settings_path: Path,
    sources_path: Path,
    default_output_directory: Path,
    project_store: ActiveProjectStoreV1,
) -> _DesktopReadinessV1:
    sources = tuple(
        item for item in load_sources_config(sources_path).sources if item.enabled
    )
    output = settings.editor_output_directory or default_output_directory  # type: ignore[attr-defined]
    provider = settings.scout_provider  # type: ignore[attr-defined]
    provider_ready = (
        bool(resolve_openai_api_key())
        if provider == "openai"
        else bool(settings.ollama_base_url and settings.ollama_model)
    )  # type: ignore[attr-defined]
    project = None
    warning = None
    try:
        project = project_store.load()
    except OSError, ValueError, TypeError, KeyError, UnicodeError:
        warning = "Proiectul activ nu poate fi deschis. Fisierul a fost pastrat."
    return _DesktopReadinessV1(
        not settings_path.is_file()
        or not sources
        or settings.editor_output_directory is None,  # type: ignore[attr-defined]
        provider_ready,
        sources,
        load_sources_config(sources_path).sources,
        output,
        project,
        warning,
    )


def _complete_desktop_setup_v1(
    *,
    settings: object,
    settings_path: Path,
    provider: str,
    base_url: str,
    model: str,
    output_directory: Path,
) -> WindowsSettingsV1:
    values = {
        item.name: getattr(settings, item.name) for item in fields(WindowsSettingsV1)
    }
    values.update(
        scout_provider=provider,
        ollama_base_url=base_url.rstrip("/"),
        ollama_model=model,
        editor_provider=provider,
        editor_model=model,
        editor_output_directory=output_directory.resolve(),
    )
    completed = WindowsSettingsV1(**values)
    completed.editor_output_directory.mkdir(parents=True, exist_ok=True)
    _save_windows_settings_v1(path=settings_path, settings=completed)
    return completed


__all__: tuple[str, ...] = ()
