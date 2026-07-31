"""Version-2 planning-input transport into generic executor requests."""

import json
from typing import Any

from pydantic import SerializeAsAny, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionPlanResultV2,
    CorrectiveActionPlanningInput,
)
from pastila_scout.editor.qa.models import fingerprint

from .models import (
    CorrectiveActionExecutionContext,
    CorrectiveActionExecutorDescriptor,
    CorrectiveActionExecutorRequest,
)
from .validation import (
    validate_execution_context,
    validate_executor_descriptor,
    validate_executor_request,
)

EXECUTOR_REQUEST_TRANSPORT_VERSION = "2"


class CorrectiveActionExecutorRequestV2(FrozenModel):
    """Transport the exact planning input while retaining the exact v1 request."""

    request_version: str = EXECUTOR_REQUEST_TRANSPORT_VERSION
    legacy_request: CorrectiveActionExecutorRequest
    planning_result: CorrectiveActionExecutionPlanResultV2
    planning_input: SerializeAsAny[CorrectiveActionPlanningInput]
    request_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("request_version", EXECUTOR_REQUEST_TRANSPORT_VERSION)
        values["request_fingerprint"] = fingerprint(_identity(values))
        return cls.model_validate(values)

    @property
    def plan(self):
        return self.planning_result.plan

    @property
    def executor_descriptor(self):
        return self.legacy_request.executor_descriptor

    @property
    def execution_context(self):
        return self.legacy_request.execution_context

    @model_validator(mode="after")
    def invariants(self):
        if self.request_version != EXECUTOR_REQUEST_TRANSPORT_VERSION:
            raise ValueError("unsupported version-2 executor request")
        if (
            self.legacy_request.planning_result
            is not self.planning_result.legacy_result
        ):
            raise ValueError(
                "executor request does not preserve planning-result identity"
            )
        if self.legacy_request.plan is not self.plan.legacy_plan:
            raise ValueError("executor request does not preserve plan identity")
        if self.planning_input is not self.planning_result.planning_input:
            raise ValueError(
                "executor request does not preserve planning-input identity"
            )
        legacy_plan = self.legacy_request.plan
        if legacy_plan.source_action is not self.planning_input.corrective_action:
            raise ValueError("executor request planning-input action mismatch")
        if (
            legacy_plan.required_capability
            is not self.planning_input.required_capability
        ):
            raise ValueError("executor request planning-input capability mismatch")
        if (
            self.executor_descriptor.supported_capability
            is not self.planning_input.required_capability
        ):
            raise ValueError(
                "executor descriptor and planning-input capability mismatch"
            )
        if self.request_fingerprint != fingerprint(
            _identity(self.model_dump(mode="python"))
        ):
            raise ValueError("version-2 executor-request fingerprint is inconsistent")
        return self


def build_corrective_action_executor_request_v2(
    planning_result: CorrectiveActionExecutionPlanResultV2,
    executor_descriptor: CorrectiveActionExecutorDescriptor,
    execution_context: CorrectiveActionExecutionContext,
) -> CorrectiveActionExecutorRequestV2:
    """Dispatcher-owned pure construction without interpreting capability fields."""

    validate_executor_descriptor(executor_descriptor)
    validate_execution_context(execution_context)
    legacy_result = planning_result.legacy_result
    legacy_request = CorrectiveActionExecutorRequest.build(
        planning_result=legacy_result,
        plan=legacy_result.plan,
        executor_descriptor=executor_descriptor,
        execution_context=execution_context,
    )
    validate_executor_request(legacy_request)
    return CorrectiveActionExecutorRequestV2.build(
        legacy_request=legacy_request,
        planning_result=planning_result,
        planning_input=planning_result.planning_input,
    )


def build_executor_request_v2_report(
    request: CorrectiveActionExecutorRequestV2,
) -> dict[str, object]:
    """Project only capability-neutral transport metadata."""

    return {
        "report_version": "1",
        "executor_request_version": request.request_version,
        "planning_input_type": request.planning_input.input_type.value,
        "corrective_action": request.planning_input.corrective_action.value,
        "required_capability": request.planning_input.required_capability.value,
        "planning_input_fingerprint": request.planning_input.input_fingerprint,
        "planning_result_fingerprint": request.planning_result.result_fingerprint,
        "legacy_executor_request_fingerprint": request.legacy_request.request_fingerprint,
        "executor_request_fingerprint": request.request_fingerprint,
    }


def serialize_executor_request_v2_report(report: dict[str, object]) -> str:
    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate_executor_request_v2(value: CorrectiveActionExecutorRequestV2) -> None:
    if not isinstance(value, CorrectiveActionExecutorRequestV2):
        raise TypeError("invalid version-2 executor request")
    value.invariants()
    validate_executor_request(value.legacy_request)


def _identity(values):
    return {
        "request_version": values["request_version"],
        "legacy_request_fingerprint": _field(
            values["legacy_request"], "request_fingerprint"
        ),
        "planning_result_fingerprint": _field(
            values["planning_result"], "result_fingerprint"
        ),
        "planning_input_fingerprint": _field(
            values["planning_input"], "input_fingerprint"
        ),
    }


def _field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)
