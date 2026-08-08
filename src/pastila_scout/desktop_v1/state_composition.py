"""Synchronous state-bound desktop composition."""

# ruff: noqa: BLE001

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import NoReturn

from pastila_scout.desktop_application_v1 import DesktopApplicationFacadeV1
from pastila_scout.desktop_editor_v1.composition import (
    _compose_desktop_application_facade_v1,
)
from pastila_scout.windows_state_v1.migrations import (
    DevelopmentMigrationPlanV1,
    _execute_development_state_migration_v1,
    _inspect_development_state_migration_applicability_v1,
)
from pastila_scout.windows_state_v1.paths import (
    WindowsApplicationPathsV1,
    _create_windows_application_directories_v1,
    _resolve_windows_application_paths_v1,
)
from pastila_scout.windows_state_v1.settings import _load_windows_settings_v1

from .settings import (
    _DesktopSettingsProjectionV1,
    _project_desktop_settings_v1,
    _reconstruct_desktop_settings_projection_v1,
    _select_scout_sources_path_v1,
)


class _DesktopStateConsumptionError(Exception):
    __slots__ = ("presentation_key",)

    def __init__(self, presentation_key: str = "state.error") -> None:
        super().__init__("Windows desktop state consumption failed.")
        self.presentation_key = presentation_key

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop state consumption errors cannot be subclassed")


class _DesktopStateCompositionV1:
    __slots__ = ("facade", "settings")

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop state compositions cannot be subclassed")

    def __init__(
        self,
        *,
        facade: DesktopApplicationFacadeV1,
        settings: _DesktopSettingsProjectionV1,
    ) -> None:
        if type(facade) is not DesktopApplicationFacadeV1:
            raise TypeError("Invalid desktop facade")
        object.__setattr__(self, "facade", facade)
        object.__setattr__(
            self, "settings", _reconstruct_desktop_settings_projection_v1(settings)
        )

    def __setattr__(self, name: str, value: object) -> NoReturn:
        del name, value
        raise TypeError("Desktop state compositions are immutable")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("Desktop state compositions do not support pickle")


def _compose_state_bound_desktop_application_v1(
    *,
    frozen: bool,
    environment: Mapping[str, str],
    development_root: Path | None,
    migration_consent: Callable[
        [WindowsApplicationPathsV1], DevelopmentMigrationPlanV1 | None
    ],
) -> _DesktopStateCompositionV1:
    paths = None
    settings = None
    failed = False
    try:
        if (
            type(frozen) is not bool
            or not isinstance(environment, Mapping)
            or not callable(migration_consent)
        ):
            raise TypeError
        bundled_root = None
        if frozen:
            if development_root is not None:
                raise TypeError
            bundled_root = (
                Path(environment["LOCALAPPDATA"]) / "Programs" / "PastilaScout" / "app"
            )
        elif not isinstance(development_root, Path):
            raise TypeError
        paths = _resolve_windows_application_paths_v1(
            frozen=frozen,
            environment=environment,
            bundled_application_root=bundled_root,
            development_root=development_root,
        )
        _create_windows_application_directories_v1(paths=paths)
        settings = _load_windows_settings_v1(
            path=paths.settings_path, defaults_path=paths.settings_defaults_path
        )
    except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        raise
    except Exception:
        failed = True
    if failed:
        del environment, development_root, migration_consent, paths, settings, failed
        raise _DesktopStateConsumptionError("state.error") from None

    if frozen:
        failed = False
        try:
            applicability = _inspect_development_state_migration_applicability_v1(
                destination=paths
            )
            if applicability.status == "development_root_required":
                plan = migration_consent(paths)
                if plan is not None:
                    if (
                        type(plan) is not DevelopmentMigrationPlanV1
                        or plan.status != "ready"
                    ):
                        raise TypeError
                    result = _execute_development_state_migration_v1(plan=plan)
                    if result.status != "completed":
                        raise ValueError
                    if result.settings_copied:
                        settings = _load_windows_settings_v1(
                            path=paths.settings_path,
                            defaults_path=paths.settings_defaults_path,
                        )
        except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
            raise
        except Exception:
            failed = True
        if failed:
            del (
                environment,
                development_root,
                migration_consent,
                paths,
                settings,
                failed,
            )
            raise _DesktopStateConsumptionError("migration.error") from None

    failed = False
    try:
        sources_path = _select_scout_sources_path_v1(paths=paths)
    except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        raise
    except Exception:
        failed = True
    if failed:
        del environment, development_root, migration_consent, paths, settings, failed
        raise _DesktopStateConsumptionError("sources.override.error") from None
    failed = False
    try:
        facade = _compose_desktop_application_facade_v1(
            config_path=paths.scout_application_config_path,
            sources_path=sources_path,
            database_path=paths.database_path,
            report_directory=paths.report_directory,
        )
        projection = _project_desktop_settings_v1(settings=settings)
        return _DesktopStateCompositionV1(facade=facade, settings=projection)
    except (KeyboardInterrupt, SystemExit, GeneratorExit, MemoryError):
        raise
    except Exception:
        failed = True
    if failed:
        del environment, development_root, migration_consent, paths, settings, failed
        raise _DesktopStateConsumptionError("startup.error") from None
    raise AssertionError("unreachable")


__all__: tuple[str, ...] = ()
