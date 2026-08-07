"""Private validation helpers for lower Scout results."""

from __future__ import annotations

from pastila_scout.desktop_application_v1 import DesktopApplicationConfigurationError
from pastila_scout.poller import PollResult

_MAX_COUNTER = 2**63 - 1


def _reconstruct_poll_result(value: object) -> PollResult:
    """Validate the maintained lower result without repairing its authority."""

    invalid = False
    try:
        if type(value) is not PollResult:
            raise TypeError
        counters = tuple(
            object.__getattribute__(value, name)
            for name in (
                "sources_checked",
                "sources_succeeded",
                "sources_failed",
                "articles_found",
                "articles_inserted",
                "duplicates_skipped",
            )
        )
        checked, succeeded, failed, found, inserted, duplicates = counters
        failed_ids = object.__getattribute__(value, "failed_source_ids")
        status = object.__getattribute__(value, "status")
        if (
            any(
                type(item) is not int or not 0 <= item <= _MAX_COUNTER
                for item in counters
            )
            or checked != succeeded + failed
            or type(failed_ids) is not tuple
            or len(failed_ids) != failed
            or inserted > found
            or inserted + duplicates > found
            or type(status) is not str
            or not _valid_status(status, succeeded, failed)
        ):
            raise TypeError
        # Facade construction is the maintained scalar authority for every ID.
        from pastila_scout.desktop_application_v1 import (
            DesktopOperationStatusV1,
            ScoutDesktopCategoryV1,
            ScoutDesktopResultV1,
        )

        ScoutDesktopResultV1(
            operation_reference="validation",
            status={
                "success": DesktopOperationStatusV1.COMPLETED,
                "partial": DesktopOperationStatusV1.PARTIAL,
                "failed": DesktopOperationStatusV1.FAILED,
            }[status],
            sources_checked=checked,
            sources_succeeded=succeeded,
            sources_failed=failed,
            articles_found=found,
            articles_inserted=inserted,
            duplicates_skipped=duplicates,
            failed_source_ids=failed_ids,
            executed_period_days=1,
            executed_category=ScoutDesktopCategoryV1.ALL,
            report_reference=None,
            failure=(None if status != "failed" else _failure()),
        )
        result = value
    except Exception:  # noqa: BLE001 - malformed lower authority is isolated
        invalid = True
        result = None
    if invalid:
        del value, result, invalid
        raise DesktopApplicationConfigurationError() from None
    return result


def _failure():
    from pastila_scout.desktop_application_v1 import (
        DesktopApplicationFailureCodeV1,
        DesktopApplicationFailureV1,
    )

    return DesktopApplicationFailureV1(
        code=DesktopApplicationFailureCodeV1.SCOUT_EXECUTION_FAILED
    )


def _valid_status(status: object, succeeded: int, failed: int) -> bool:
    return (
        status == "success"
        and failed == 0
        or status == "partial"
        and succeeded > 0
        and failed > 0
        or status == "failed"
        and succeeded == 0
        and failed > 0
    )


__all__: tuple[str, ...] = ()
