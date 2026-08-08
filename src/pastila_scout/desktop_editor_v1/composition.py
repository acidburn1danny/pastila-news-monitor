"""Sole private production desktop application facade composition."""

from __future__ import annotations

import os
from pathlib import Path
from typing import NoReturn

from pastila_scout.desktop_application_v1 import DesktopApplicationFacadeV1
from pastila_scout.desktop_report_v1.service import _DesktopReportFacadeV1
from pastila_scout.desktop_scout_v1.service import _ScoutDesktopOperationV1
from pastila_scout.editor_application_v1.runtime_composition import (
    _compose_editor_application_runtime_v1,
)

from .models import _DesktopApplicationCompositionErrorV1
from .service import _EditorDesktopOperationV1


def _open_desktop_report_v1(path: Path) -> None:
    if type(path) is not type(Path()):
        raise TypeError("path must be the platform's concrete Path type")
    os.startfile(path)  # type: ignore[attr-defined]


def _compose_desktop_application_facade_v1(
    *,
    config_path: Path,
    sources_path: Path,
    database_path: Path,
    report_directory: Path,
) -> DesktopApplicationFacadeV1:
    report_facade = scout_operation = editor_application = editor_operation = facade = (
        None
    )
    failed = False
    try:
        if not all(
            type(path) is type(Path())
            for path in (config_path, sources_path, database_path, report_directory)
        ):
            raise TypeError
        report_facade = _DesktopReportFacadeV1(
            report_directory=report_directory, opener=_open_desktop_report_v1
        )
        scout_operation = _ScoutDesktopOperationV1(
            config_path=config_path,
            sources_path=sources_path,
            database_path=database_path,
            report_facade=report_facade,
        )
        editor_application = _compose_editor_application_runtime_v1()
        editor_operation = _EditorDesktopOperationV1(application=editor_application)
        facade = DesktopApplicationFacadeV1(
            scout_operation=scout_operation,
            editor_operation=editor_operation,
            report_operation=report_facade,
        )
    except (KeyboardInterrupt, SystemExit, GeneratorExit):
        raise
    except Exception:  # noqa: BLE001 - construction details collapse at safe boundary
        failed = True
    if failed:
        del report_facade, scout_operation, editor_application, editor_operation, facade
        del failed
        _raise_composition()
    return facade


def _raise_composition() -> NoReturn:
    raise _DesktopApplicationCompositionErrorV1() from None


__all__: tuple[str, ...] = ()
