"""Private atomic Scout report generation and catalog service."""

from __future__ import annotations

import hashlib
import inspect
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from types import FunctionType
from typing import NoReturn

from pastila_scout.desktop_application_v1 import (
    DesktopApplicationConfigurationError,
    DesktopApplicationExecutionError,
    DesktopReportReferenceV1,
    reconstruct_desktop_report_reference,
)

from .html import _render_report_html_v1
from .models import _DesktopScoutReportInputV1, _reconstruct_report_input


class _DesktopReportFacadeV1:
    __slots__ = ("_catalog", "_opener", "_opener_identity", "_report_directory")

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop report facades cannot be subclassed")

    def __init__(
        self, *, report_directory: Path, opener: Callable[[Path], None]
    ) -> None:
        if type(report_directory) is not type(Path()) or not _valid_opener(opener):
            raise DesktopApplicationConfigurationError() from None
        object.__setattr__(self, "_report_directory", report_directory)
        object.__setattr__(self, "_opener", opener)
        object.__setattr__(self, "_opener_identity", id(opener))
        object.__setattr__(self, "_catalog", {})

    def generate_report(
        self, *, result: _DesktopScoutReportInputV1
    ) -> DesktopReportReferenceV1:
        reference = None
        failed = False
        try:
            value = _reconstruct_report_input(result)
            directory, _, catalog = _dependencies(self)
            digest = hashlib.sha256(
                value.operation_reference.encode("utf-8")
            ).hexdigest()
            reference_value = "scout-report-v1:" + digest
            reference = DesktopReportReferenceV1(report_reference=reference_value)
            destination = directory / f"{digest}.html"
            if reference_value in catalog or destination.exists():
                raise FileExistsError
            content = _render_report_html_v1(report=value).encode("utf-8")
            _publish_no_replace(directory, destination, content)
            catalog[reference_value] = destination.resolve(strict=True)
            reference = reconstruct_desktop_report_reference(reference)
        except (KeyboardInterrupt, SystemExit, GeneratorExit):
            raise
        except Exception:  # noqa: BLE001 - filesystem details collapse at boundary
            failed = True
        if failed:
            del self, result, reference, failed
            raise DesktopApplicationExecutionError() from None
        return reference

    def open_report(self, *, reference: str) -> None:
        failed = False
        try:
            valid = DesktopReportReferenceV1(report_reference=reference)
            _, opener, catalog = _dependencies(self)
            path = catalog[valid.report_reference]
            opener(path)
        except (KeyboardInterrupt, SystemExit, GeneratorExit):
            raise
        except Exception:  # noqa: BLE001 - opener/catalog details collapse at boundary
            failed = True
        if failed:
            del self, reference, failed
            raise DesktopApplicationExecutionError() from None


def _publish_no_replace(directory: Path, destination: Path, content: bytes) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=directory, prefix=".scout-report-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def _valid_opener(value: object) -> bool:
    try:
        if type(value) is not FunctionType:
            return False
        signature = inspect.signature(value, follow_wrapped=False)
        parameters = tuple(signature.parameters.values())
        return (
            len(parameters) == 1
            and parameters[0].annotation in (Path, "Path")
            and signature.return_annotation in (None, "None")
        )
    except Exception:  # noqa: BLE001 - adversarial callable state is rejected
        return False


def _dependencies(facade):
    try:
        directory = object.__getattribute__(facade, "_report_directory")
        opener = object.__getattribute__(facade, "_opener")
        identity = object.__getattribute__(facade, "_opener_identity")
        catalog = object.__getattribute__(facade, "_catalog")
        if (
            type(directory) is not type(Path())
            or id(opener) != identity
            or not _valid_opener(opener)
            or type(catalog) is not dict
        ):
            raise TypeError
        return directory, opener, catalog
    except Exception:  # noqa: BLE001 - copied-invalid retained state is rejected
        raise DesktopApplicationConfigurationError() from None


__all__: tuple[str, ...] = ()
