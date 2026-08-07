"""Synchronous private adapter from the desktop facade to the Editor application."""

from __future__ import annotations

from typing import NoReturn

from pastila_scout.desktop_application_v1 import (
    DesktopApplicationConfigurationError,
    DesktopApplicationExecutionError,
    EditorDesktopRequestV1,
    EditorDesktopResultV1,
    reconstruct_editor_desktop_request,
)
from pastila_scout.editor_application_v1 import EditorApplicationCoordinatorV1
from pastila_scout.editor_application_v1.application import _validated_dependencies
from pastila_scout.editor_application_v1.models import reconstruct_application_result


class _EditorDesktopOperationV1:
    __slots__ = ("_application", "_identity")

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Editor desktop operations cannot be subclassed")

    def __init__(self, *, application: EditorApplicationCoordinatorV1) -> None:
        invalid = False
        try:
            if type(application) is not EditorApplicationCoordinatorV1:
                raise TypeError
            _validated_dependencies(application)
        except Exception:  # noqa: BLE001 - copied-invalid dependency is rejected
            invalid = True
        if invalid:
            del self, application, invalid
            _raise_configuration()
        object.__setattr__(self, "_application", application)
        object.__setattr__(self, "_identity", id(application))

    def run_editor(self, *, request: EditorDesktopRequestV1) -> EditorDesktopResultV1:
        valid_request = application = result = None
        invalid = False
        try:
            valid_request = reconstruct_editor_desktop_request(request)
            application = _application(self)
        except DesktopApplicationConfigurationError:
            invalid = True
        if invalid:
            del self, request, valid_request, application, result, invalid
            _raise_configuration()

        failed = False
        try:
            result = application.execute(request=valid_request.application_request)
        except (KeyboardInterrupt, SystemExit, GeneratorExit):
            raise
        except Exception:  # noqa: BLE001 - lower details collapse at safe boundary
            failed = True
        if failed:
            del self, request, valid_request, application, result, invalid, failed
            _raise_execution()

        invalid = False
        try:
            result = reconstruct_application_result(result)
            if (
                result.operation_reference
                != valid_request.application_request.operation_reference
            ):
                raise DesktopApplicationConfigurationError
            desktop_result = EditorDesktopResultV1(application_result=result)
        except Exception:  # noqa: BLE001 - invalid lower result is isolated
            invalid = True
            desktop_result = None
        if invalid:
            del self, request, valid_request, application, result, invalid, failed
            del desktop_result
            _raise_configuration()
        return desktop_result


def _application(
    operation: _EditorDesktopOperationV1,
) -> EditorApplicationCoordinatorV1:
    invalid = False
    application = None
    try:
        application = object.__getattribute__(operation, "_application")
        identity = object.__getattribute__(operation, "_identity")
        if type(application) is not EditorApplicationCoordinatorV1 or identity != id(
            application
        ):
            raise TypeError
        _validated_dependencies(application)
    except Exception:  # noqa: BLE001 - copied-invalid retained state is rejected
        invalid = True
    if invalid:
        del operation, application, invalid
        _raise_configuration()
    return application


def _raise_configuration() -> NoReturn:
    raise DesktopApplicationConfigurationError() from None


def _raise_execution() -> NoReturn:
    raise DesktopApplicationExecutionError() from None


__all__: tuple[str, ...] = ()
