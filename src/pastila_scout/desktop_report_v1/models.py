"""Private immutable Scout report values."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import NoReturn

from pastila_scout.desktop_application_v1 import (
    DesktopApplicationConfigurationError,
    DesktopOperationStatusV1,
    ScoutDesktopCategoryV1,
    ScoutDesktopResultV1,
)


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class _DesktopScoutReportInputV1:
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
    _seal: str

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop report inputs cannot be subclassed")

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
    ) -> None:
        values = (
            operation_reference,
            status,
            sources_checked,
            sources_succeeded,
            sources_failed,
            articles_found,
            articles_inserted,
            duplicates_skipped,
            failed_source_ids,
            executed_period_days,
            executed_category,
        )
        invalid = False
        try:
            ScoutDesktopResultV1(
                operation_reference=operation_reference,
                status=status,
                sources_checked=sources_checked,
                sources_succeeded=sources_succeeded,
                sources_failed=sources_failed,
                articles_found=articles_found,
                articles_inserted=articles_inserted,
                duplicates_skipped=duplicates_skipped,
                failed_source_ids=failed_source_ids,
                executed_period_days=executed_period_days,
                executed_category=executed_category,
                report_reference=None,
                failure=None,
            )
            if status not in (
                DesktopOperationStatusV1.COMPLETED,
                DesktopOperationStatusV1.PARTIAL,
            ):
                raise TypeError
        except Exception:  # noqa: BLE001 - finite constructor boundary
            invalid = True
        if invalid:
            del self, values, invalid
            raise DesktopApplicationConfigurationError() from None
        for name, value in zip(_FIELDS, values, strict=True):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_seal", _seal(values))

    def __repr__(self) -> str:
        valid = _reconstruct_report_input(self)
        return f"_DesktopScoutReportInputV1(status={valid.status.value!r}, operation_reference=<redacted>, failed_source_ids=<redacted>)"

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _values(
            _reconstruct_report_input(self)
        ) == _values(_reconstruct_report_input(other))

    def __copy__(self):
        return _reconstruct_report_input(self)

    def __deepcopy__(self, memo):
        del memo
        return _reconstruct_report_input(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("_DesktopScoutReportInputV1 does not support pickle")


_FIELDS = (
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
)


def _values(value):
    return tuple(object.__getattribute__(value, name) for name in _FIELDS)


def _seal(values) -> str:
    serial = tuple(item.value if hasattr(item, "value") else item for item in values)
    return hashlib.sha256(
        json.dumps(serial, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def _reconstruct_report_input(value: object) -> _DesktopScoutReportInputV1:
    rebuilt = None
    invalid = False
    try:
        if type(value) is not _DesktopScoutReportInputV1:
            raise TypeError
        rebuilt = _DesktopScoutReportInputV1(
            **dict(zip(_FIELDS, _values(value), strict=True))
        )
        if not hmac.compare_digest(
            object.__getattribute__(value, "_seal"),
            object.__getattribute__(rebuilt, "_seal"),
        ):
            raise TypeError
        return rebuilt
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        invalid = True
    if invalid:
        del value, rebuilt, invalid
        raise DesktopApplicationConfigurationError() from None
    return rebuilt


__all__: tuple[str, ...] = ()
