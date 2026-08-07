"""Injected synchronous services for the desktop application facade."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from types import FunctionType
from typing import NoReturn, Protocol

from pastila_scout.editor_application_v1 import EditorApplicationStatusV1

from .errors import (
    DesktopApplicationConfigurationError,
    DesktopApplicationExecutionError,
)
from .models import (
    DesktopOperationKindV1,
    DesktopOperationStatusV1,
    DesktopProgressEventV1,
    DesktopProgressStageV1,
    DesktopReportReferenceV1,
    EditorDesktopRequestV1,
    EditorDesktopResultV1,
    ScoutDesktopRequestV1,
    ScoutDesktopResultV1,
    reconstruct_desktop_report_reference,
    reconstruct_editor_desktop_request,
    reconstruct_editor_desktop_result,
    reconstruct_scout_desktop_request,
    reconstruct_scout_desktop_result,
)


def _isolated_configuration[**P, R](method: Callable[P, R]) -> Callable[P, R]:
    def isolated(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return method(*args, **kwargs)
        except DesktopApplicationConfigurationError:
            pass
        del args, kwargs
        _raise_configuration()

    return isolated


class ScoutDesktopOperationV1(Protocol):
    """One injected Scout desktop application operation."""

    def run_scout(self, *, request: ScoutDesktopRequestV1) -> ScoutDesktopResultV1: ...


class EditorDesktopOperationV1(Protocol):
    """One injected Editor desktop application operation."""

    def run_editor(
        self, *, request: EditorDesktopRequestV1
    ) -> EditorDesktopResultV1: ...


class DesktopReportOperationV1(Protocol):
    """Open one opaque desktop report reference through its owning catalog."""

    def open_report(self, *, reference: str) -> None: ...


class DesktopProgressSinkV1(Protocol):
    """Receive one facade-owned progress event synchronously."""

    def publish(self, *, event: DesktopProgressEventV1) -> None: ...


class DesktopApplicationFacadeV1:
    """Validate and delegate exactly one selected desktop application operation."""

    __slots__ = (
        "_editor_operation",
        "_identity",
        "_report_operation",
        "_scout_operation",
    )

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop application facades cannot be subclassed")

    def __init__(
        self,
        *,
        scout_operation: ScoutDesktopOperationV1,
        editor_operation: EditorDesktopOperationV1,
        report_operation: DesktopReportOperationV1,
    ) -> None:
        if (
            not _valid_method(
                scout_operation,
                "run_scout",
                "ScoutDesktopRequestV1",
                "ScoutDesktopResultV1",
            )
            or not _valid_method(
                editor_operation,
                "run_editor",
                "EditorDesktopRequestV1",
                "EditorDesktopResultV1",
            )
            or not _valid_report_method(report_operation)
        ):
            del self, scout_operation, editor_operation, report_operation
            _raise_configuration()
        object.__setattr__(self, "_scout_operation", scout_operation)
        object.__setattr__(self, "_editor_operation", editor_operation)
        object.__setattr__(self, "_report_operation", report_operation)
        object.__setattr__(
            self,
            "_identity",
            (id(scout_operation), id(editor_operation), id(report_operation)),
        )

    def run_scout(
        self,
        *,
        request: ScoutDesktopRequestV1,
        progress_sink: DesktopProgressSinkV1,
    ) -> ScoutDesktopResultV1:
        valid = None
        invalid = False
        try:
            valid = reconstruct_scout_desktop_request(request)
        except DesktopApplicationConfigurationError:
            invalid = True
        if invalid:
            del self, request, progress_sink, valid, invalid
            _raise_configuration()
        dependencies = _validated_dependencies(self)
        if not _valid_sink(progress_sink):
            del self, request, progress_sink, valid, invalid, dependencies
            _raise_configuration()
        reference = valid.operation_reference
        if not _publish(
            progress_sink,
            reference,
            DesktopOperationKindV1.SCOUT,
            DesktopProgressStageV1.ACCEPTED,
        ) or not _publish(
            progress_sink,
            reference,
            DesktopOperationKindV1.SCOUT,
            DesktopProgressStageV1.RUNNING,
        ):
            del self, request, progress_sink, valid, invalid, dependencies, reference
            _raise_execution()
        scout, editor, report = dependencies
        result = None
        failed = False
        try:
            result = scout.run_scout(request=valid)
            result = reconstruct_scout_desktop_result(result)
            if result.operation_reference != reference:
                raise TypeError
        except Exception:  # noqa: BLE001 - lower details collapse at this boundary
            failed = True
        if failed:
            _publish(
                progress_sink,
                reference,
                DesktopOperationKindV1.SCOUT,
                DesktopProgressStageV1.FAILED,
            )
            del self, request, progress_sink, valid, invalid, dependencies
            del reference, scout, editor, report, result, failed
            _raise_execution()
        terminal = _scout_terminal(result.status)
        if not _publish(
            progress_sink, reference, DesktopOperationKindV1.SCOUT, terminal
        ):
            del self, request, progress_sink, valid, invalid, dependencies
            del reference, scout, editor, report, result, failed, terminal
            _raise_execution()
        del self, request, progress_sink, valid, invalid, dependencies
        del reference, scout, editor, report, failed, terminal
        return result

    def run_editor(
        self,
        *,
        request: EditorDesktopRequestV1,
        progress_sink: DesktopProgressSinkV1,
    ) -> EditorDesktopResultV1:
        valid = None
        invalid = False
        try:
            valid = reconstruct_editor_desktop_request(request)
        except DesktopApplicationConfigurationError:
            invalid = True
        if invalid:
            del self, request, progress_sink, valid, invalid
            _raise_configuration()
        dependencies = _validated_dependencies(self)
        if not _valid_sink(progress_sink):
            del self, request, progress_sink, valid, invalid, dependencies
            _raise_configuration()
        nested_request = valid.application_request
        reference = object.__getattribute__(nested_request, "operation_reference")
        if not _publish(
            progress_sink,
            reference,
            DesktopOperationKindV1.EDITOR,
            DesktopProgressStageV1.ACCEPTED,
        ) or not _publish(
            progress_sink,
            reference,
            DesktopOperationKindV1.EDITOR,
            DesktopProgressStageV1.RUNNING,
        ):
            del self, request, progress_sink, valid, invalid, dependencies
            del nested_request, reference
            _raise_execution()
        scout, editor, report = dependencies
        result = None
        failed = False
        try:
            result = editor.run_editor(request=valid)
            result = reconstruct_editor_desktop_result(result)
            nested_result = result.application_result
            if (
                object.__getattribute__(nested_result, "operation_reference")
                != reference
            ):
                raise TypeError
        except Exception:  # noqa: BLE001 - lower details collapse at this boundary
            failed = True
            nested_result = None
        if failed:
            _publish(
                progress_sink,
                reference,
                DesktopOperationKindV1.EDITOR,
                DesktopProgressStageV1.FAILED,
            )
            del self, request, progress_sink, valid, invalid, dependencies
            del nested_request, reference, scout, editor, report, result, failed
            del nested_result
            _raise_execution()
        terminal = _editor_terminal(object.__getattribute__(nested_result, "status"))
        if not _publish(
            progress_sink, reference, DesktopOperationKindV1.EDITOR, terminal
        ):
            del self, request, progress_sink, valid, invalid, dependencies
            del nested_request, reference, scout, editor, report, result, failed
            del nested_result, terminal
            _raise_execution()
        del self, request, progress_sink, valid, invalid, dependencies
        del nested_request, reference, scout, editor, report, failed, nested_result
        del terminal
        return result

    def open_report(self, *, reference: str) -> None:
        valid = None
        invalid = False
        try:
            valid = DesktopReportReferenceV1(report_reference=reference)
            valid = reconstruct_desktop_report_reference(valid)
        except DesktopApplicationConfigurationError:
            invalid = True
        if invalid:
            del self, reference, valid, invalid
            _raise_configuration()
        scout, editor, report = _validated_dependencies(self)
        failed = False
        try:
            if report.open_report(reference=valid.report_reference) is not None:
                raise TypeError
        except Exception:  # noqa: BLE001 - report details collapse at this boundary
            failed = True
        if failed:
            del self, reference, valid, invalid, scout, editor, report, failed
            _raise_execution()
        del self, reference, valid, invalid, scout, editor, report, failed

    @_isolated_configuration
    def __repr__(self) -> str:
        _validated_dependencies(self)
        return "DesktopApplicationFacadeV1(dependencies=<injected>)"

    @_isolated_configuration
    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return False
        left = _validated_dependencies(self)
        right = _validated_dependencies(other)
        return all(a is b for a, b in zip(left, right, strict=True))

    @_isolated_configuration
    def __copy__(self) -> DesktopApplicationFacadeV1:
        scout, editor, report = _validated_dependencies(self)
        return DesktopApplicationFacadeV1(
            scout_operation=scout,
            editor_operation=editor,
            report_operation=report,
        )

    @_isolated_configuration
    def __deepcopy__(self, memo: dict[int, object]) -> DesktopApplicationFacadeV1:
        del memo
        return self.__copy__()

    def __reduce__(self) -> NoReturn:
        _pickle_error()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _pickle_error()

    def __getstate__(self) -> NoReturn:
        _pickle_error()


def _annotation_matches(value: object, expected: object, name: str) -> bool:
    return value is expected or (type(value) is str and value == name)


def _valid_method(
    dependency: object, method: str, request_name: str, result_name: str
) -> bool:
    try:
        dependency_type = type(dependency)
        if (
            inspect.getattr_static(dependency_type, "__getattribute__")
            is not object.__getattribute__
            or inspect.getattr_static(dependency_type, "__getattr__", None) is not None
        ):
            return False
        static = inspect.getattr_static(dependency_type, method)
        if type(static) is not FunctionType:
            return False
        namespace = object.__getattribute__(static, "__dict__")
        if "__signature__" in namespace or "__wrapped__" in namespace:
            return False
        instance_namespace = _instance_namespace(dependency)
        if type(instance_namespace) is dict and method in instance_namespace:
            return False
        signature = inspect.signature(static, follow_wrapped=False)
        parameters = tuple(signature.parameters.values())
        return (
            len(parameters) == 2
            and parameters[0].name == "self"
            and parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and parameters[1].name == "request"
            and parameters[1].kind is inspect.Parameter.KEYWORD_ONLY
            and _annotation_matches(
                parameters[1].annotation,
                globals()[request_name],
                request_name,
            )
            and _annotation_matches(
                signature.return_annotation,
                globals()[result_name],
                result_name,
            )
        )
    except Exception:  # noqa: BLE001 - adversarial dependency state is rejected
        return False


def _valid_report_method(dependency: object) -> bool:
    try:
        dependency_type = type(dependency)
        if (
            inspect.getattr_static(dependency_type, "__getattribute__")
            is not object.__getattribute__
            or inspect.getattr_static(dependency_type, "__getattr__", None) is not None
        ):
            return False
        static = inspect.getattr_static(dependency_type, "open_report")
        if type(static) is not FunctionType:
            return False
        namespace = object.__getattribute__(static, "__dict__")
        if "__signature__" in namespace or "__wrapped__" in namespace:
            return False
        instance_namespace = _instance_namespace(dependency)
        if type(instance_namespace) is dict and "open_report" in instance_namespace:
            return False
        signature = inspect.signature(static, follow_wrapped=False)
        parameters = tuple(signature.parameters.values())
        return (
            len(parameters) == 2
            and parameters[0].name == "self"
            and parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and parameters[1].name == "reference"
            and parameters[1].kind is inspect.Parameter.KEYWORD_ONLY
            and _annotation_matches(parameters[1].annotation, str, "str")
            and signature.return_annotation in (None, "None")
        )
    except Exception:  # noqa: BLE001 - adversarial dependency state is rejected
        return False


def _valid_sink(sink: object) -> bool:
    try:
        sink_type = type(sink)
        if (
            inspect.getattr_static(sink_type, "__getattribute__")
            is not object.__getattribute__
            or inspect.getattr_static(sink_type, "__getattr__", None) is not None
        ):
            return False
        static = inspect.getattr_static(sink_type, "publish")
        if type(static) is not FunctionType:
            return False
        namespace = object.__getattribute__(static, "__dict__")
        if "__signature__" in namespace or "__wrapped__" in namespace:
            return False
        instance_namespace = _instance_namespace(sink)
        if type(instance_namespace) is dict and "publish" in instance_namespace:
            return False
        signature = inspect.signature(static, follow_wrapped=False)
        parameters = tuple(signature.parameters.values())
        return (
            len(parameters) == 2
            and parameters[0].name == "self"
            and parameters[0].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and parameters[1].name == "event"
            and parameters[1].kind is inspect.Parameter.KEYWORD_ONLY
            and _annotation_matches(
                parameters[1].annotation,
                DesktopProgressEventV1,
                "DesktopProgressEventV1",
            )
            and signature.return_annotation in (None, "None")
        )
    except Exception:  # noqa: BLE001 - adversarial sink state is rejected
        return False


def _validated_dependencies(
    facade: DesktopApplicationFacadeV1,
) -> tuple[ScoutDesktopOperationV1, EditorDesktopOperationV1, DesktopReportOperationV1]:
    scout = editor = report = identity = None
    invalid = False
    try:
        scout = object.__getattribute__(facade, "_scout_operation")
        editor = object.__getattribute__(facade, "_editor_operation")
        report = object.__getattribute__(facade, "_report_operation")
        identity = object.__getattribute__(facade, "_identity")
        if (
            type(identity) is not tuple
            or identity != (id(scout), id(editor), id(report))
            or not _valid_method(
                scout,
                "run_scout",
                "ScoutDesktopRequestV1",
                "ScoutDesktopResultV1",
            )
            or not _valid_method(
                editor,
                "run_editor",
                "EditorDesktopRequestV1",
                "EditorDesktopResultV1",
            )
            or not _valid_report_method(report)
        ):
            raise TypeError
    except Exception:  # noqa: BLE001 - copied-invalid retained state is rejected
        invalid = True
    if invalid:
        del facade, scout, editor, report, identity, invalid
        _raise_configuration()
    del facade, identity, invalid
    return scout, editor, report


def _publish(sink, reference, operation, stage) -> bool:
    event = None
    valid = False
    try:
        event = DesktopProgressEventV1(
            operation_reference=reference, operation=operation, stage=stage
        )
        valid = sink.publish(event=event) is None
    except Exception:  # noqa: BLE001 - sink details collapse at this boundary
        valid = False
    del sink, reference, operation, stage, event
    return valid


def _scout_terminal(status: DesktopOperationStatusV1) -> DesktopProgressStageV1:
    return {
        DesktopOperationStatusV1.COMPLETED: DesktopProgressStageV1.COMPLETED,
        DesktopOperationStatusV1.PARTIAL: DesktopProgressStageV1.PARTIAL,
        DesktopOperationStatusV1.FAILED: DesktopProgressStageV1.FAILED,
    }[status]


def _instance_namespace(value: object) -> dict[str, object] | None:
    try:
        namespace = object.__getattribute__(value, "__dict__")
    except AttributeError:
        return None
    return namespace if type(namespace) is dict else None


def _editor_terminal(status: EditorApplicationStatusV1) -> DesktopProgressStageV1:
    return {
        EditorApplicationStatusV1.COMPLETED: DesktopProgressStageV1.COMPLETED,
        EditorApplicationStatusV1.FAILED: DesktopProgressStageV1.FAILED,
        EditorApplicationStatusV1.CANCELLED: DesktopProgressStageV1.CANCELLED,
    }[status]


def _raise_configuration() -> NoReturn:
    raise DesktopApplicationConfigurationError() from None


def _raise_execution() -> NoReturn:
    raise DesktopApplicationExecutionError() from None


def _pickle_error() -> NoReturn:
    raise TypeError("DesktopApplicationFacadeV1 does not support pickle")


__all__ = (
    "DesktopApplicationFacadeV1",
    "DesktopProgressSinkV1",
    "DesktopReportOperationV1",
    "EditorDesktopOperationV1",
    "ScoutDesktopOperationV1",
)
