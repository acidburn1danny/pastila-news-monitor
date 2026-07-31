"""Capability-neutral version-2 corrective-action execution runtime."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from pydantic import Field, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
)
from pastila_scout.editor.qa.corrective_action.models import CorrectiveAction
from pastila_scout.editor.qa.models import fingerprint

from .input_transport import (
    CorrectiveActionExecutorRequestV2,
    validate_executor_request_v2,
)

RUNTIME_VERSION = "1"


class CorrectiveActionExecutionResponseStatus(StrEnum):
    SUCCESS = "success"
    CAPABILITY_PREPARATION_FAILED = "capability_preparation_failed"
    CAPABILITY_NOT_EXECUTABLE = "capability_not_executable"
    CAPABILITY_EXECUTION_FAILED = "capability_execution_failed"
    INVALID_CAPABILITY_EXECUTION_RESULT = "invalid_capability_execution_result"
    CORRECTIVE_ACTION_ROUTING_FAILED = "corrective_action_routing_failed"
    INTERNAL_CORRECTIVE_ACTION_EXECUTION_FAILURE = (
        "internal_corrective_action_execution_failure"
    )


class CorrectiveActionExecutionPhaseV2(StrEnum):
    CREATED = "created"
    REQUEST_VALIDATED = "request_validated"
    CAPABILITY_RESOLVED = "capability_resolved"
    PREPARING = "preparing"
    PREPARED = "prepared"
    EXECUTING = "executing"
    EXECUTED = "executed"
    RESULT_VALIDATED = "result_validated"
    COMPLETED = "completed"
    FAILED = "failed"


class CorrectiveActionExecutionResponse(FrozenModel):
    """Immutable generic response retaining an exact capability result."""

    contract_version: str = RUNTIME_VERSION
    request: CorrectiveActionExecutorRequestV2 | None = Field(default=None, repr=False)
    capability: CorrectiveActionExecutionCapability | None = None
    action: CorrectiveAction | None = None
    status: CorrectiveActionExecutionResponseStatus
    lifecycle: tuple[CorrectiveActionExecutionPhaseV2, ...]
    preparation_fingerprint: str | None = None
    execution_fingerprint: str | None = None
    capability_result: Any = Field(default=None, repr=False)
    diagnostic_code: str | None = None
    response_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("contract_version", RUNTIME_VERSION)
        values.setdefault("request", None)
        values.setdefault("capability", None)
        values.setdefault("action", None)
        values.setdefault("preparation_fingerprint", None)
        values.setdefault("execution_fingerprint", None)
        values.setdefault("capability_result", None)
        values.setdefault("diagnostic_code", None)
        values["response_fingerprint"] = fingerprint(_response_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != RUNTIME_VERSION:
            raise ValueError("unsupported corrective-action response version")
        if self.lifecycle[0] is not CorrectiveActionExecutionPhaseV2.CREATED:
            raise ValueError("corrective-action lifecycle must start at created")
        terminal = self.lifecycle[-1]
        expected = (
            CorrectiveActionExecutionPhaseV2.COMPLETED
            if self.status is CorrectiveActionExecutionResponseStatus.SUCCESS
            else CorrectiveActionExecutionPhaseV2.FAILED
        )
        if terminal is not expected:
            raise ValueError("corrective-action lifecycle terminal is inconsistent")
        if self.status is CorrectiveActionExecutionResponseStatus.SUCCESS and (
            self.request is None
            or self.capability is None
            or self.action is None
            or self.capability_result is None
            or self.execution_fingerprint is None
        ):
            raise ValueError("successful corrective-action response is incomplete")
        if self.capability_result is not None and (
            self.execution_fingerprint is None
            or getattr(self.capability_result, "execution_fingerprint", None)
            != self.execution_fingerprint
        ):
            raise ValueError("capability-result execution lineage is inconsistent")
        if self.response_fingerprint != fingerprint(
            _response_identity(self.model_dump(mode="python"))
        ):
            raise ValueError("corrective-action response fingerprint is inconsistent")
        return self


class CorrectiveActionExecutionSafeReport(FrozenModel):
    """Content-free projection of the version-2 integration response."""

    report_version: str = RUNTIME_VERSION
    capability: str
    action: str
    status: str
    lifecycle: tuple[str, ...]
    request_fingerprint: str
    planning_input_fingerprint: str
    preparation_fingerprint: str | None
    execution_fingerprint: str | None
    response_fingerprint: str
    diagnostic_code: str | None
    report_fingerprint: str

    @classmethod
    def build(cls, response: CorrectiveActionExecutionResponse):
        values = {
            "report_version": RUNTIME_VERSION,
            "capability": (
                response.capability.value if response.capability else "unknown"
            ),
            "action": response.action.value if response.action else "unknown",
            "status": response.status.value,
            "lifecycle": tuple(item.value for item in response.lifecycle),
            "request_fingerprint": (
                response.request.request_fingerprint
                if response.request
                else "unavailable"
            ),
            "planning_input_fingerprint": (
                response.request.planning_input.input_fingerprint
                if response.request
                else "unavailable"
            ),
            "preparation_fingerprint": response.preparation_fingerprint,
            "execution_fingerprint": response.execution_fingerprint,
            "response_fingerprint": response.response_fingerprint,
            "diagnostic_code": response.diagnostic_code,
        }
        return cls(**values, report_fingerprint=fingerprint(values))


class CorrectiveActionV2Integration(Protocol):
    def execute(
        self, request: CorrectiveActionExecutorRequestV2
    ) -> CorrectiveActionExecutionResponse: ...


@dataclass(frozen=True, slots=True)
class CorrectiveActionV2Binding:
    capability: CorrectiveActionExecutionCapability
    action: CorrectiveAction
    integration: CorrectiveActionV2Integration


@dataclass(frozen=True, slots=True)
class CorrectiveActionExecutionDispatcherV2:
    """Resolve immutable typed bindings without inspecting capability internals."""

    bindings: tuple[CorrectiveActionV2Binding, ...]

    def __post_init__(self) -> None:
        canonical = tuple(
            sorted(
                self.bindings,
                key=lambda item: (item.capability.value, item.action.value),
            )
        )
        keys = tuple((item.capability, item.action) for item in canonical)
        if len(keys) != len(set(keys)):
            raise ValueError("ambiguous version-2 executor registration")
        object.__setattr__(self, "bindings", canonical)

    def dispatch(
        self, request: CorrectiveActionExecutorRequestV2
    ) -> CorrectiveActionExecutionResponse:
        if not isinstance(request, CorrectiveActionExecutorRequestV2):
            return _routing_failure(None, "invalid_executor_request")
        try:
            validate_executor_request_v2(request)
        except (TypeError, ValueError):
            return _routing_failure(None, "invalid_executor_request")
        capability = request.planning_input.required_capability
        action = request.planning_input.corrective_action
        matches = tuple(
            item
            for item in self.bindings
            if item.capability is capability and item.action is action
        )
        if len(matches) != 1:
            return _routing_failure(request, "capability_route_not_found")
        try:
            response = matches[0].integration.execute(request)
        except Exception:  # noqa: BLE001 - sanitized outer integration boundary
            return _failure_response(
                request,
                CorrectiveActionExecutionResponseStatus.INTERNAL_CORRECTIVE_ACTION_EXECUTION_FAILURE,
                "integration_internal_failure",
                (
                    CorrectiveActionExecutionPhaseV2.CREATED,
                    CorrectiveActionExecutionPhaseV2.REQUEST_VALIDATED,
                    CorrectiveActionExecutionPhaseV2.CAPABILITY_RESOLVED,
                    CorrectiveActionExecutionPhaseV2.FAILED,
                ),
            )
        try:
            validate_execution_response(
                response,
                request=request,
                capability=capability,
                action=action,
            )
        except (TypeError, ValueError):
            return _failure_response(
                request,
                CorrectiveActionExecutionResponseStatus.INTERNAL_CORRECTIVE_ACTION_EXECUTION_FAILURE,
                "invalid_integration_response",
                (
                    CorrectiveActionExecutionPhaseV2.CREATED,
                    CorrectiveActionExecutionPhaseV2.REQUEST_VALIDATED,
                    CorrectiveActionExecutionPhaseV2.CAPABILITY_RESOLVED,
                    CorrectiveActionExecutionPhaseV2.FAILED,
                ),
            )
        return response


def validate_execution_response(
    response: CorrectiveActionExecutionResponse,
    *,
    request: CorrectiveActionExecutorRequestV2 | None = None,
    capability: CorrectiveActionExecutionCapability | None = None,
    action: CorrectiveAction | None = None,
) -> None:
    """Validate response integrity and optional dispatcher-owned lineage."""

    if not isinstance(response, CorrectiveActionExecutionResponse):
        raise TypeError("invalid corrective-action execution response")
    response.invariants()
    if request is not None and response.request is not request:
        raise ValueError("corrective-action response request identity mismatch")
    if capability is not None and response.capability is not capability:
        raise ValueError("corrective-action response capability mismatch")
    if action is not None and response.action is not action:
        raise ValueError("corrective-action response action mismatch")


def build_execution_safe_report(
    response: CorrectiveActionExecutionResponse,
) -> CorrectiveActionExecutionSafeReport:
    return CorrectiveActionExecutionSafeReport.build(response)


def serialize_execution_safe_report(report: CorrectiveActionExecutionSafeReport) -> str:
    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _routing_failure(request: Any, code: str) -> CorrectiveActionExecutionResponse:
    if request is None:
        return CorrectiveActionExecutionResponse.build(
            status=CorrectiveActionExecutionResponseStatus.CORRECTIVE_ACTION_ROUTING_FAILED,
            lifecycle=(
                CorrectiveActionExecutionPhaseV2.CREATED,
                CorrectiveActionExecutionPhaseV2.FAILED,
            ),
            diagnostic_code=code,
        )
    return _failure_response(
        request,
        CorrectiveActionExecutionResponseStatus.CORRECTIVE_ACTION_ROUTING_FAILED,
        code,
        (
            CorrectiveActionExecutionPhaseV2.CREATED,
            CorrectiveActionExecutionPhaseV2.FAILED,
        ),
    )


def _failure_response(request, status, code, lifecycle, **values):
    return CorrectiveActionExecutionResponse.build(
        request=request,
        capability=request.planning_input.required_capability,
        action=request.planning_input.corrective_action,
        status=status,
        lifecycle=lifecycle,
        diagnostic_code=code,
        **values,
    )


def _response_identity(values):
    return {
        "contract_version": values["contract_version"],
        "request_fingerprint": (
            _field(values["request"], "request_fingerprint")
            if values.get("request") is not None
            else None
        ),
        "capability": values["capability"],
        "action": values["action"],
        "status": values["status"],
        "lifecycle": values["lifecycle"],
        "preparation_fingerprint": values.get("preparation_fingerprint"),
        "execution_fingerprint": values.get("execution_fingerprint"),
        "diagnostic_code": values.get("diagnostic_code"),
    }


def _field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)
