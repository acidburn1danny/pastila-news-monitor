"""Synchronous private adapter from the desktop facade to lower Scout."""

from __future__ import annotations

import inspect
from pathlib import Path
from types import FunctionType
from typing import NoReturn

from pastila_scout.desktop_application_v1 import (
    DesktopApplicationConfigurationError,
    DesktopApplicationExecutionError,
    DesktopApplicationFailureCodeV1,
    DesktopApplicationFailureV1,
    DesktopOperationStatusV1,
    DesktopReportReferenceV1,
    ScoutDesktopRequestV1,
    ScoutDesktopResultV1,
    reconstruct_desktop_report_reference,
    reconstruct_scout_desktop_request,
)
from pastila_scout.desktop_report_v1.models import _DesktopScoutReportInputV1
from pastila_scout.desktop_report_v1.service import _DesktopReportFacadeV1
from pastila_scout.poller import poll_once

from .models import _reconstruct_poll_result


class _ScoutDesktopOperationV1:
    __slots__ = (
        "_config_path",
        "_database_path",
        "_identity",
        "_report_facade",
        "_sources_path",
    )

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Scout desktop operations cannot be subclassed")

    def __init__(
        self,
        *,
        config_path: Path,
        sources_path: Path,
        database_path: Path,
        report_facade: _DesktopReportFacadeV1,
    ) -> None:
        if (
            type(config_path) is not type(Path())
            or type(sources_path) is not type(Path())
            or type(database_path) is not type(Path())
            or not _valid_report_facade(report_facade)
        ):
            raise DesktopApplicationConfigurationError() from None
        object.__setattr__(self, "_config_path", config_path)
        object.__setattr__(self, "_sources_path", sources_path)
        object.__setattr__(self, "_database_path", database_path)
        object.__setattr__(self, "_report_facade", report_facade)
        object.__setattr__(self, "_identity", id(report_facade))

    def run_scout(self, *, request: ScoutDesktopRequestV1) -> ScoutDesktopResultV1:
        valid_request = reconstruct_scout_desktop_request(request)
        config_path, sources_path, database_path, report_facade = _dependencies(self)

        lower = None
        failed = False
        try:
            lower = poll_once(
                config_path,
                database_path,
                sources_path=sources_path,
                max_article_age_hours_override=(
                    48.0
                    if valid_request.targeted_query is not None
                    else float(valid_request.period_days * 24)
                ),
                category=valid_request.category.value,
            )
            lower = _reconstruct_poll_result(lower)
        except KeyboardInterrupt, SystemExit, GeneratorExit:
            raise
        except Exception:  # noqa: BLE001 - lower details collapse at safe boundary
            failed = True
        if failed:
            del self, request, valid_request, config_path, database_path, report_facade
            del lower, failed
            raise DesktopApplicationExecutionError() from None

        status = {
            "success": DesktopOperationStatusV1.COMPLETED,
            "partial": DesktopOperationStatusV1.PARTIAL,
            "failed": DesktopOperationStatusV1.FAILED,
        }[lower.status]
        values = _result_values(valid_request, lower, status)
        if status is DesktopOperationStatusV1.FAILED:
            return ScoutDesktopResultV1(
                **values,
                report_reference=None,
                failure=DesktopApplicationFailureV1(
                    code=DesktopApplicationFailureCodeV1.SCOUT_EXECUTION_FAILED
                ),
            )

        reference = None
        failed = False
        try:
            reference = report_facade.generate_report(
                result=_DesktopScoutReportInputV1(
                    **{
                        name: value
                        for name, value in values.items()
                        if name != "targeted_candidate_ids"
                    }
                )
            )
            reference = reconstruct_desktop_report_reference(reference)
        except KeyboardInterrupt, SystemExit, GeneratorExit:
            raise
        except Exception:  # noqa: BLE001 - report details collapse at safe boundary
            failed = True
        if failed:
            del self, request, valid_request, config_path, database_path, report_facade
            del lower, status, values, reference, failed
            raise DesktopApplicationExecutionError() from None
        return ScoutDesktopResultV1(**values, report_reference=reference, failure=None)


def _result_values(request, lower, status) -> dict[str, object]:
    return {
        "operation_reference": request.operation_reference,
        "status": status,
        "sources_checked": lower.sources_checked,
        "sources_succeeded": lower.sources_succeeded,
        "sources_failed": lower.sources_failed,
        "articles_found": lower.articles_found,
        "articles_inserted": lower.articles_inserted,
        "duplicates_skipped": lower.duplicates_skipped,
        "failed_source_ids": lower.failed_source_ids,
        "executed_period_days": request.period_days,
        "executed_category": request.category,
        # U2 supplies relevance-scoped event identities. Until then, targeted
        # execution is intentionally empty rather than globally restored.
        "targeted_candidate_ids": (() if request.targeted_query is not None else None),
    }


def _valid_report_facade(value: object) -> bool:
    return (
        _safe_dependency_type(value)
        and _valid_method(
            value,
            "generate_report",
            "result",
            _DesktopScoutReportInputV1,
            DesktopReportReferenceV1,
        )
        and _valid_method(value, "open_report", "reference", str, None)
    )


def _valid_method(value, name, argument, annotation, returned) -> bool:
    try:
        method = inspect.getattr_static(type(value), name)
        if type(method) is not FunctionType:
            return False
        namespace = object.__getattribute__(method, "__dict__")
        if "__signature__" in namespace or "__wrapped__" in namespace:
            return False
        instance_namespace = _instance_namespace(value)
        if type(instance_namespace) is dict and name in instance_namespace:
            return False
        signature = inspect.signature(method, follow_wrapped=False)
        parameters = tuple(signature.parameters.values())
        expected_return = signature.return_annotation
        return (
            len(parameters) == 2
            and parameters[0].name == "self"
            and parameters[1].name == argument
            and parameters[1].kind is inspect.Parameter.KEYWORD_ONLY
            and parameters[1].annotation in (annotation, annotation.__name__)
            and expected_return
            in (returned, "None" if returned is None else returned.__name__)
        )
    except Exception:  # noqa: BLE001 - adversarial dependency state is rejected
        return False


def _safe_dependency_type(value: object) -> bool:
    try:
        dependency_type = type(value)
        return (
            inspect.getattr_static(dependency_type, "__getattribute__")
            is object.__getattribute__
            and inspect.getattr_static(dependency_type, "__getattr__", None) is None
        )
    except Exception:  # noqa: BLE001 - adversarial dependency state is rejected
        return False


def _instance_namespace(value: object) -> dict[str, object] | None:
    try:
        return object.__getattribute__(value, "__dict__")
    except AttributeError:
        return None


def _dependencies(operation):
    try:
        config = object.__getattribute__(operation, "_config_path")
        sources = object.__getattribute__(operation, "_sources_path")
        database = object.__getattribute__(operation, "_database_path")
        facade = object.__getattribute__(operation, "_report_facade")
        identity = object.__getattribute__(operation, "_identity")
        if (
            type(config) is not type(Path())
            or type(sources) is not type(Path())
            or type(database) is not type(Path())
            or identity != id(facade)
            or not _valid_report_facade(facade)
        ):
            raise TypeError
        return config, sources, database, facade
    except Exception:  # noqa: BLE001 - copied-invalid retained state is rejected
        raise DesktopApplicationConfigurationError() from None


__all__: tuple[str, ...] = ()
