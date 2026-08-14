"""Strict immutable contracts for the desktop application facade."""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import NoReturn

from pastila_scout.editor_application_v1 import (
    EditorApplicationRequestV1,
    EditorApplicationResultV1,
)

from .errors import DesktopApplicationConfigurationError

_PERIODS = (1, 3, 7, 14, 30)
_MAX_COUNTER = 2**63 - 1


class DesktopOperationKindV1(StrEnum):
    SCOUT = "scout"
    EDITOR = "editor"

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _pickle_error(type(self).__name__)


class DesktopOperationStatusV1(StrEnum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _pickle_error(type(self).__name__)


class DesktopProgressStageV1(StrEnum):
    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _pickle_error(type(self).__name__)


class ScoutDesktopCategoryV1(StrEnum):
    POLITICA = "Politica"
    SOCIAL = "Social"
    CANCAN = "CanCan"
    EXTERNE = "Externe"
    DIVERSE = "Diverse"
    ALL = "all"

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _pickle_error(type(self).__name__)


class DesktopApplicationFailureCodeV1(StrEnum):
    SCOUT_EXECUTION_FAILED = "scout_execution_failed"

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _pickle_error(type(self).__name__)


def _raise_configuration() -> NoReturn:
    raise DesktopApplicationConfigurationError() from None


def _pickle_error(name: str) -> NoReturn:
    raise TypeError(f"{name} does not support pickle")


def _isolated_configuration[**P, R](method: Callable[P, R]) -> Callable[P, R]:
    def isolated(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return method(*args, **kwargs)
        except DesktopApplicationConfigurationError:
            pass
        del args, kwargs
        _raise_configuration()

    return isolated


def _valid_text(value: object) -> bool:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or not unicodedata.is_normalized("NFC", value)
    ):
        return False
    try:
        encoded = value.encode("utf-8")
    except UnicodeError:
        return False
    return 1 <= len(encoded) <= 120 and all(
        character != "\x00"
        and not 0 <= ord(character) <= 0x1F
        and not 0x7F <= ord(character) <= 0x9F
        and not 0xD800 <= ord(character) <= 0xDFFF
        for character in value
    )


def _counter(value: object) -> bool:
    return type(value) is int and 0 <= value <= _MAX_COUNTER


def _seal(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _same_seal(value: object, rebuilt: object) -> bool:
    return hmac.compare_digest(
        object.__getattribute__(value, "_seal"),
        object.__getattribute__(rebuilt, "_seal"),
    )


class _ValueSafety:
    __slots__ = ()

    def __reduce__(self) -> NoReturn:
        _pickle_error(type(self).__name__)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _pickle_error(type(self).__name__)

    def __getstate__(self) -> NoReturn:
        _pickle_error(type(self).__name__)


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class DesktopApplicationFailureV1(_ValueSafety):
    code: DesktopApplicationFailureCodeV1
    _seal: str

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop application values cannot be subclassed")

    def __init__(self, *, code: DesktopApplicationFailureCodeV1) -> None:
        if type(code) is not DesktopApplicationFailureCodeV1:
            del self, code
            _raise_configuration()
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "_seal", _seal((code.value,)))

    @property
    @_isolated_configuration
    def safe_message(self) -> str:
        reconstruct_desktop_application_failure(self)
        return "Scout execution failed."

    @_isolated_configuration
    def __repr__(self) -> str:
        valid = reconstruct_desktop_application_failure(self)
        return f"DesktopApplicationFailureV1(code={valid.code.value!r})"

    @_isolated_configuration
    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and (
            reconstruct_desktop_application_failure(self).code
            is reconstruct_desktop_application_failure(other).code
        )

    @_isolated_configuration
    def __copy__(self) -> DesktopApplicationFailureV1:
        return reconstruct_desktop_application_failure(self)

    @_isolated_configuration
    def __deepcopy__(self, memo: dict[int, object]) -> DesktopApplicationFailureV1:
        del memo
        return reconstruct_desktop_application_failure(self)


def reconstruct_desktop_application_failure(
    value: object,
) -> DesktopApplicationFailureV1:
    rebuilt = None
    try:
        if type(value) is not DesktopApplicationFailureV1:
            raise TypeError
        rebuilt = DesktopApplicationFailureV1(
            code=object.__getattribute__(value, "code")
        )
        if not _same_seal(value, rebuilt):
            raise TypeError
        return rebuilt
    except DesktopApplicationConfigurationError:
        del value, rebuilt
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        del value, rebuilt
        _raise_configuration()


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class DesktopReportReferenceV1(_ValueSafety):
    report_reference: str
    _seal: str

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop application values cannot be subclassed")

    def __init__(self, *, report_reference: str) -> None:
        if not _valid_text(report_reference):
            del self, report_reference
            _raise_configuration()
        object.__setattr__(self, "report_reference", report_reference)
        object.__setattr__(self, "_seal", _seal((report_reference,)))

    @_isolated_configuration
    def __repr__(self) -> str:
        reconstruct_desktop_report_reference(self)
        return "DesktopReportReferenceV1(report_reference=<redacted>)"

    @_isolated_configuration
    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and (
            reconstruct_desktop_report_reference(self).report_reference
            == reconstruct_desktop_report_reference(other).report_reference
        )

    @_isolated_configuration
    def __copy__(self) -> DesktopReportReferenceV1:
        return reconstruct_desktop_report_reference(self)

    @_isolated_configuration
    def __deepcopy__(self, memo: dict[int, object]) -> DesktopReportReferenceV1:
        del memo
        return reconstruct_desktop_report_reference(self)


def reconstruct_desktop_report_reference(value: object) -> DesktopReportReferenceV1:
    rebuilt = None
    try:
        if type(value) is not DesktopReportReferenceV1:
            raise TypeError
        rebuilt = DesktopReportReferenceV1(
            report_reference=object.__getattribute__(value, "report_reference")
        )
        if not _same_seal(value, rebuilt):
            raise TypeError
        return rebuilt
    except DesktopApplicationConfigurationError:
        del value, rebuilt
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        del value, rebuilt
        _raise_configuration()


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class ScoutDesktopRequestV1(_ValueSafety):
    operation_reference: str
    period_days: int
    category: ScoutDesktopCategoryV1
    targeted_query: str | None
    _seal: str

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop application values cannot be subclassed")

    def __init__(
        self,
        *,
        operation_reference: str,
        period_days: int,
        category: ScoutDesktopCategoryV1,
        targeted_query: str | None = None,
    ) -> None:
        if (
            not _valid_text(operation_reference)
            or type(period_days) is not int
            or period_days not in _PERIODS
            or type(category) is not ScoutDesktopCategoryV1
            or (
                targeted_query is not None
                and (
                    not _valid_text(targeted_query)
                    or targeted_query != targeted_query.strip()
                )
            )
        ):
            del self, operation_reference, period_days, category, targeted_query
            _raise_configuration()
        object.__setattr__(self, "operation_reference", operation_reference)
        object.__setattr__(self, "period_days", period_days)
        object.__setattr__(self, "category", category)
        object.__setattr__(self, "targeted_query", targeted_query)
        object.__setattr__(
            self,
            "_seal",
            _seal((operation_reference, period_days, category.value, targeted_query)),
        )

    @_isolated_configuration
    def __repr__(self) -> str:
        valid = reconstruct_scout_desktop_request(self)
        return (
            "ScoutDesktopRequestV1("
            f"operation_reference={valid.operation_reference!r}, "
            f"period_days={valid.period_days!r}, category={valid.category.value!r}, "
            f"targeted_query={'<redacted>' if valid.targeted_query is not None else None})"
        )

    @_isolated_configuration
    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _scout_request_values(
            reconstruct_scout_desktop_request(self)
        ) == _scout_request_values(reconstruct_scout_desktop_request(other))

    @_isolated_configuration
    def __copy__(self) -> ScoutDesktopRequestV1:
        return reconstruct_scout_desktop_request(self)

    @_isolated_configuration
    def __deepcopy__(self, memo: dict[int, object]) -> ScoutDesktopRequestV1:
        del memo
        return reconstruct_scout_desktop_request(self)


def _scout_request_values(value: ScoutDesktopRequestV1) -> tuple[object, ...]:
    return tuple(
        object.__getattribute__(value, field)
        for field in (
            "operation_reference",
            "period_days",
            "category",
            "targeted_query",
        )
    )


def reconstruct_scout_desktop_request(value: object) -> ScoutDesktopRequestV1:
    rebuilt = None
    try:
        if type(value) is not ScoutDesktopRequestV1:
            raise TypeError
        rebuilt = ScoutDesktopRequestV1(
            operation_reference=object.__getattribute__(value, "operation_reference"),
            period_days=object.__getattribute__(value, "period_days"),
            category=object.__getattribute__(value, "category"),
            targeted_query=object.__getattribute__(value, "targeted_query"),
        )
        if not _same_seal(value, rebuilt):
            raise TypeError
        return rebuilt
    except DesktopApplicationConfigurationError:
        del value, rebuilt
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        del value, rebuilt
        _raise_configuration()


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class EditorDesktopRequestV1(_ValueSafety):
    application_request: EditorApplicationRequestV1
    _seal: str

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop application values cannot be subclassed")

    def __init__(self, *, application_request: EditorApplicationRequestV1) -> None:
        valid = None
        try:
            if type(application_request) is not EditorApplicationRequestV1:
                raise TypeError
            valid = copy.copy(application_request)
            if type(valid) is not EditorApplicationRequestV1:
                raise TypeError
            reference = object.__getattribute__(valid, "operation_reference")
        except Exception:  # noqa: BLE001 - nested authority is isolated
            del self, application_request, valid
            _raise_configuration()
        object.__setattr__(self, "application_request", valid)
        object.__setattr__(self, "_seal", _seal((reference, id(valid))))

    @_isolated_configuration
    def __repr__(self) -> str:
        valid = reconstruct_editor_desktop_request(self)
        reference = object.__getattribute__(
            valid.application_request, "operation_reference"
        )
        return f"EditorDesktopRequestV1(operation_reference={reference!r}, content=<redacted>, path=<redacted>)"

    @_isolated_configuration
    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and (
            reconstruct_editor_desktop_request(self).application_request
            == reconstruct_editor_desktop_request(other).application_request
        )

    @_isolated_configuration
    def __copy__(self) -> EditorDesktopRequestV1:
        return EditorDesktopRequestV1(
            application_request=reconstruct_editor_desktop_request(
                self
            ).application_request
        )

    @_isolated_configuration
    def __deepcopy__(self, memo: dict[int, object]) -> EditorDesktopRequestV1:
        del memo
        return self.__copy__()


def reconstruct_editor_desktop_request(value: object) -> EditorDesktopRequestV1:
    nested = rebuilt = None
    try:
        if type(value) is not EditorDesktopRequestV1:
            raise TypeError
        nested = object.__getattribute__(value, "application_request")
        if type(nested) is not EditorApplicationRequestV1:
            raise TypeError
        validated = copy.copy(nested)
        if type(validated) is not EditorApplicationRequestV1:
            raise TypeError
        reference = object.__getattribute__(validated, "operation_reference")
        expected = _seal((reference, id(nested)))
        if not hmac.compare_digest(object.__getattribute__(value, "_seal"), expected):
            raise TypeError
        rebuilt = EditorDesktopRequestV1(application_request=validated)
        return rebuilt
    except DesktopApplicationConfigurationError:
        del value, nested, rebuilt
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        del value, nested, rebuilt
        _raise_configuration()


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class DesktopProgressEventV1(_ValueSafety):
    operation_reference: str
    operation: DesktopOperationKindV1
    stage: DesktopProgressStageV1
    _seal: str

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop application values cannot be subclassed")

    def __init__(
        self,
        *,
        operation_reference: str,
        operation: DesktopOperationKindV1,
        stage: DesktopProgressStageV1,
    ) -> None:
        valid_pair = not (
            (
                operation is DesktopOperationKindV1.SCOUT
                and stage is DesktopProgressStageV1.CANCELLED
            )
            or (
                operation is DesktopOperationKindV1.EDITOR
                and stage is DesktopProgressStageV1.PARTIAL
            )
        )
        if (
            not _valid_text(operation_reference)
            or type(operation) is not DesktopOperationKindV1
            or type(stage) is not DesktopProgressStageV1
            or not valid_pair
        ):
            del self, operation_reference, operation, stage
            _raise_configuration()
        object.__setattr__(self, "operation_reference", operation_reference)
        object.__setattr__(self, "operation", operation)
        object.__setattr__(self, "stage", stage)
        object.__setattr__(
            self, "_seal", _seal((operation_reference, operation.value, stage.value))
        )

    @_isolated_configuration
    def __repr__(self) -> str:
        valid = reconstruct_desktop_progress_event(self)
        return (
            "DesktopProgressEventV1("
            f"operation_reference={valid.operation_reference!r}, "
            f"operation={valid.operation.value!r}, stage={valid.stage.value!r})"
        )

    @_isolated_configuration
    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _progress_values(
            reconstruct_desktop_progress_event(self)
        ) == _progress_values(reconstruct_desktop_progress_event(other))

    @_isolated_configuration
    def __copy__(self) -> DesktopProgressEventV1:
        return reconstruct_desktop_progress_event(self)

    @_isolated_configuration
    def __deepcopy__(self, memo: dict[int, object]) -> DesktopProgressEventV1:
        del memo
        return reconstruct_desktop_progress_event(self)


def _progress_values(value: DesktopProgressEventV1) -> tuple[object, ...]:
    return tuple(
        object.__getattribute__(value, field)
        for field in ("operation_reference", "operation", "stage")
    )


def reconstruct_desktop_progress_event(value: object) -> DesktopProgressEventV1:
    rebuilt = None
    try:
        if type(value) is not DesktopProgressEventV1:
            raise TypeError
        rebuilt = DesktopProgressEventV1(
            operation_reference=object.__getattribute__(value, "operation_reference"),
            operation=object.__getattribute__(value, "operation"),
            stage=object.__getattribute__(value, "stage"),
        )
        if not _same_seal(value, rebuilt):
            raise TypeError
        return rebuilt
    except DesktopApplicationConfigurationError:
        del value, rebuilt
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        del value, rebuilt
        _raise_configuration()


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class ScoutDesktopResultV1(_ValueSafety):
    operation_reference: str
    status: DesktopOperationStatusV1
    sources_checked: int
    sources_succeeded: int
    sources_failed: int
    articles_found: int
    articles_inserted: int
    duplicates_skipped: int
    failed_source_ids: tuple[str, ...]
    executed_period_days: int
    executed_category: ScoutDesktopCategoryV1
    targeted_candidate_ids: tuple[int, ...] | None
    report_reference: DesktopReportReferenceV1 | None
    failure: DesktopApplicationFailureV1 | None
    _seal: str

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop application values cannot be subclassed")

    def __init__(
        self,
        *,
        operation_reference: str,
        status: DesktopOperationStatusV1,
        sources_checked: int,
        sources_succeeded: int,
        sources_failed: int,
        articles_found: int,
        articles_inserted: int,
        duplicates_skipped: int,
        failed_source_ids: tuple[str, ...],
        executed_period_days: int,
        executed_category: ScoutDesktopCategoryV1,
        targeted_candidate_ids: tuple[int, ...] | None = None,
        report_reference: DesktopReportReferenceV1 | None,
        failure: DesktopApplicationFailureV1 | None,
    ) -> None:
        report = valid_failure = None
        try:
            counters = (
                sources_checked,
                sources_succeeded,
                sources_failed,
                articles_found,
                articles_inserted,
                duplicates_skipped,
            )
            if (
                not _valid_text(operation_reference)
                or type(status) is not DesktopOperationStatusV1
                or any(not _counter(item) for item in counters)
                or type(failed_source_ids) is not tuple
                or any(not _valid_text(item) for item in failed_source_ids)
                or type(executed_period_days) is not int
                or type(executed_category) is not ScoutDesktopCategoryV1
                or (
                    targeted_candidate_ids is not None
                    and (
                        type(targeted_candidate_ids) is not tuple
                        or any(
                            type(item) is not int or item <= 0
                            for item in targeted_candidate_ids
                        )
                        or len(targeted_candidate_ids)
                        != len(set(targeted_candidate_ids))
                    )
                )
                or executed_period_days not in _PERIODS
            ):
                raise TypeError
            report = (
                None
                if report_reference is None
                else reconstruct_desktop_report_reference(report_reference)
            )
            valid_failure = (
                None
                if failure is None
                else reconstruct_desktop_application_failure(failure)
            )
            if not _valid_scout_result(
                status,
                counters,
                failed_source_ids,
                report,
                valid_failure,
            ):
                raise TypeError
            values = (
                operation_reference,
                status,
                *counters,
                failed_source_ids,
                executed_period_days,
                executed_category,
                targeted_candidate_ids,
                report,
                valid_failure,
            )
            seal = _seal(_scout_result_seal(values))
        except Exception:  # noqa: BLE001 - finite constructor validation boundary
            del self, report, valid_failure
            del operation_reference, status, sources_checked, sources_succeeded
            del sources_failed, articles_found, articles_inserted, duplicates_skipped
            del failed_source_ids, executed_period_days, executed_category
            del targeted_candidate_ids
            del report_reference, failure
            _raise_configuration()
        for name, value in zip(_SCOUT_RESULT_FIELDS, values, strict=True):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_seal", seal)

    @_isolated_configuration
    def __repr__(self) -> str:
        valid = reconstruct_scout_desktop_result(self)
        return (
            "ScoutDesktopResultV1("
            f"operation_reference={valid.operation_reference!r}, "
            f"status={valid.status.value!r})"
        )

    @_isolated_configuration
    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _scout_result_seal(
            _scout_result_values(reconstruct_scout_desktop_result(self))
        ) == _scout_result_seal(
            _scout_result_values(reconstruct_scout_desktop_result(other))
        )

    @_isolated_configuration
    def __copy__(self) -> ScoutDesktopResultV1:
        return reconstruct_scout_desktop_result(self)

    @_isolated_configuration
    def __deepcopy__(self, memo: dict[int, object]) -> ScoutDesktopResultV1:
        del memo
        return reconstruct_scout_desktop_result(self)


_SCOUT_RESULT_FIELDS = (
    "operation_reference",
    "status",
    "sources_checked",
    "sources_succeeded",
    "sources_failed",
    "articles_found",
    "articles_inserted",
    "duplicates_skipped",
    "failed_source_ids",
    "executed_period_days",
    "executed_category",
    "targeted_candidate_ids",
    "report_reference",
    "failure",
)


def _valid_scout_result(status, counters, failed_ids, report, failure) -> bool:
    checked, succeeded, failed, found, inserted, duplicates = counters
    common = (
        succeeded + failed == checked
        and len(failed_ids) == failed
        and inserted <= found
        and inserted + duplicates <= found
    )
    if status is DesktopOperationStatusV1.COMPLETED:
        return common and failed == 0 and failure is None
    if status is DesktopOperationStatusV1.PARTIAL:
        return common and succeeded > 0 and failed > 0 and failure is None
    if status is DesktopOperationStatusV1.FAILED:
        return (
            common
            and succeeded == 0
            and failed > 0
            and report is None
            and failure is not None
            and failure.code is DesktopApplicationFailureCodeV1.SCOUT_EXECUTION_FAILED
        )
    return False


def _scout_result_values(value: ScoutDesktopResultV1) -> tuple[object, ...]:
    return tuple(object.__getattribute__(value, name) for name in _SCOUT_RESULT_FIELDS)


def _scout_result_seal(values: tuple[object, ...]) -> tuple[object, ...]:
    *prefix, report, failure = values
    return (
        *(item.value if isinstance(item, StrEnum) else item for item in prefix),
        None if report is None else report.report_reference,
        None if failure is None else failure.code.value,
    )


def reconstruct_scout_desktop_result(value: object) -> ScoutDesktopResultV1:
    rebuilt = None
    try:
        if type(value) is not ScoutDesktopResultV1:
            raise TypeError
        values = _scout_result_values(value)
        rebuilt = ScoutDesktopResultV1(
            **dict(zip(_SCOUT_RESULT_FIELDS, values, strict=True))
        )
        if not _same_seal(value, rebuilt):
            raise TypeError
        return rebuilt
    except DesktopApplicationConfigurationError:
        del value, rebuilt
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        del value, rebuilt
        _raise_configuration()


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class EditorDesktopResultV1(_ValueSafety):
    application_result: EditorApplicationResultV1
    _seal: str

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop application values cannot be subclassed")

    def __init__(self, *, application_result: EditorApplicationResultV1) -> None:
        valid = None
        try:
            if type(application_result) is not EditorApplicationResultV1:
                raise TypeError
            valid = copy.copy(application_result)
            if type(valid) is not EditorApplicationResultV1:
                raise TypeError
            reference = object.__getattribute__(valid, "operation_reference")
            status = object.__getattribute__(valid, "status")
        except Exception:  # noqa: BLE001 - nested authority is isolated
            del self, application_result, valid
            _raise_configuration()
        object.__setattr__(self, "application_result", valid)
        object.__setattr__(self, "_seal", _seal((reference, status.value, id(valid))))

    @_isolated_configuration
    def __repr__(self) -> str:
        valid = reconstruct_editor_desktop_result(self).application_result
        return f"EditorDesktopResultV1(status={valid.status.value!r}, content=<redacted>, path=<redacted>)"

    @_isolated_configuration
    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and (
            reconstruct_editor_desktop_result(self).application_result
            == reconstruct_editor_desktop_result(other).application_result
        )

    @_isolated_configuration
    def __copy__(self) -> EditorDesktopResultV1:
        return EditorDesktopResultV1(
            application_result=reconstruct_editor_desktop_result(
                self
            ).application_result
        )

    @_isolated_configuration
    def __deepcopy__(self, memo: dict[int, object]) -> EditorDesktopResultV1:
        del memo
        return self.__copy__()


def reconstruct_editor_desktop_result(value: object) -> EditorDesktopResultV1:
    nested = rebuilt = None
    try:
        if type(value) is not EditorDesktopResultV1:
            raise TypeError
        nested = object.__getattribute__(value, "application_result")
        if type(nested) is not EditorApplicationResultV1:
            raise TypeError
        validated = copy.copy(nested)
        if type(validated) is not EditorApplicationResultV1:
            raise TypeError
        reference = object.__getattribute__(validated, "operation_reference")
        status = object.__getattribute__(validated, "status")
        expected = _seal((reference, status.value, id(nested)))
        if not hmac.compare_digest(object.__getattribute__(value, "_seal"), expected):
            raise TypeError
        rebuilt = EditorDesktopResultV1(application_result=validated)
        return rebuilt
    except DesktopApplicationConfigurationError:
        del value, nested, rebuilt
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        del value, nested, rebuilt
        _raise_configuration()


__all__ = (
    "DesktopApplicationFailureCodeV1",
    "DesktopApplicationFailureV1",
    "DesktopOperationKindV1",
    "DesktopOperationStatusV1",
    "DesktopProgressEventV1",
    "DesktopProgressStageV1",
    "DesktopReportReferenceV1",
    "EditorDesktopRequestV1",
    "EditorDesktopResultV1",
    "ScoutDesktopCategoryV1",
    "ScoutDesktopRequestV1",
    "ScoutDesktopResultV1",
    "reconstruct_desktop_application_failure",
    "reconstruct_desktop_progress_event",
    "reconstruct_desktop_report_reference",
    "reconstruct_editor_desktop_request",
    "reconstruct_editor_desktop_result",
    "reconstruct_scout_desktop_request",
    "reconstruct_scout_desktop_result",
)
