"""Production composition around one already-authoritative planning result."""

from enum import StrEnum
from typing import Any

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionPlanResult,
    validate_execution_plan_result,
)
from pastila_scout.editor.qa.models import fingerprint

from .models import (
    CorrectiveActionExecutionContext,
    CorrectiveActionExecutionDispatchPolicy,
    CorrectiveActionExecutionDispatchRequest,
    CorrectiveActionExecutionDispatchResult,
)
from .service import CorrectiveActionExecutionDispatchService
from .state import CorrectiveActionExecutionDispatchState, validate_dispatch_state
from .validation import (
    validate_execution_context,
    validate_execution_dispatch_policy,
    validate_execution_dispatch_request,
    validate_execution_dispatch_result,
)

WORKFLOW_VERSION = "1"
WORKFLOW_DESCRIPTOR_VERSION = "1"


class CorrectiveActionExecutionDispatchWorkflowOutcome(StrEnum):
    """Composition outcome, separate from nested dispatch semantics."""

    COMPLETED = "completed"


class CorrectiveActionExecutionDispatchWorkflowRequest(FrozenModel):
    """Immutable workflow input preserving the exact planning result."""

    workflow_version: str = WORKFLOW_VERSION
    planning_result: CorrectiveActionExecutionPlanResult
    dispatch_policy: CorrectiveActionExecutionDispatchPolicy
    execution_context: CorrectiveActionExecutionContext
    request_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionDispatchWorkflowRequest:
        values.setdefault("workflow_version", WORKFLOW_VERSION)
        values["request_fingerprint"] = fingerprint(_workflow_request_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.workflow_version != WORKFLOW_VERSION:
            raise ValueError("unsupported dispatch workflow version")
        validate_execution_plan_result(self.planning_result)
        expected = fingerprint(
            _workflow_request_identity(self.model_dump(mode="python"))
        )
        if self.request_fingerprint != expected:
            raise ValueError("dispatch workflow request fingerprint is inconsistent")
        return self


class CorrectiveActionExecutionDispatchWorkflowDescriptor(FrozenModel):
    """Stable production-composition identity."""

    descriptor_version: str = WORKFLOW_DESCRIPTOR_VERSION
    workflow_id: str = "corrective-action-execution-dispatch.v1"
    descriptor_fingerprint: str

    @classmethod
    def standard(cls) -> CorrectiveActionExecutionDispatchWorkflowDescriptor:
        values = {
            "descriptor_version": WORKFLOW_DESCRIPTOR_VERSION,
            "workflow_id": "corrective-action-execution-dispatch.v1",
        }
        return cls(**values, descriptor_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def invariants(self):
        if self.descriptor_version != WORKFLOW_DESCRIPTOR_VERSION:
            raise ValueError("unsupported workflow descriptor version")
        expected = fingerprint(
            self.model_dump(exclude={"descriptor_fingerprint"}, mode="python")
        )
        if self.descriptor_fingerprint != expected:
            raise ValueError("workflow descriptor fingerprint is inconsistent")
        return self


class CorrectiveActionExecutionDispatchWorkflowResult(FrozenModel):
    """Immutable composition result preserving all runtime identities."""

    workflow_version: str = WORKFLOW_VERSION
    request: CorrectiveActionExecutionDispatchWorkflowRequest
    descriptor: CorrectiveActionExecutionDispatchWorkflowDescriptor
    operational_outcome: CorrectiveActionExecutionDispatchWorkflowOutcome
    dispatch_request: CorrectiveActionExecutionDispatchRequest
    dispatch_result: CorrectiveActionExecutionDispatchResult
    dispatch_state: CorrectiveActionExecutionDispatchState
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionDispatchWorkflowResult:
        values.setdefault("workflow_version", WORKFLOW_VERSION)
        values["result_fingerprint"] = fingerprint(_workflow_result_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.workflow_version != WORKFLOW_VERSION:
            raise ValueError("unsupported dispatch workflow result version")
        if self.dispatch_result.request is not self.dispatch_request:
            raise ValueError("workflow does not preserve dispatch request identity")
        if self.dispatch_request.planning_result is not self.request.planning_result:
            raise ValueError("workflow does not preserve planning-result identity")
        validate_dispatch_state(self.dispatch_state)
        expected = fingerprint(
            _workflow_result_identity(self.model_dump(mode="python"))
        )
        if self.result_fingerprint != expected:
            raise ValueError("dispatch workflow result fingerprint is inconsistent")
        return self


class CorrectiveActionExecutionDispatchWorkflowService:
    """Compose and invoke the dispatch service exactly once."""

    def __init__(
        self,
        dispatch_service: CorrectiveActionExecutionDispatchService,
        descriptor: CorrectiveActionExecutionDispatchWorkflowDescriptor | None = None,
    ) -> None:
        self._dispatch_service = dispatch_service
        self._descriptor = (
            descriptor or CorrectiveActionExecutionDispatchWorkflowDescriptor.standard()
        )

    def run(
        self, request: CorrectiveActionExecutionDispatchWorkflowRequest
    ) -> CorrectiveActionExecutionDispatchWorkflowResult:
        """Validate composition, dispatch once, and preserve its result unchanged."""

        validate_execution_dispatch_workflow_request(request)
        dispatch_request = CorrectiveActionExecutionDispatchRequest.build(
            request.planning_result,
            request.dispatch_policy,
            request.execution_context,
        )
        runtime = self._dispatch_service.dispatch_runtime(dispatch_request)
        return CorrectiveActionExecutionDispatchWorkflowResult.build(
            request=request,
            descriptor=self._descriptor,
            operational_outcome=(
                CorrectiveActionExecutionDispatchWorkflowOutcome.COMPLETED
            ),
            dispatch_request=dispatch_request,
            dispatch_result=runtime.result,
            dispatch_state=runtime.state,
        )


def validate_execution_dispatch_workflow_request(
    request: CorrectiveActionExecutionDispatchWorkflowRequest,
) -> None:
    """Validate workflow identity and every nested immutable input."""

    if not isinstance(request, CorrectiveActionExecutionDispatchWorkflowRequest):
        raise TypeError("invalid dispatch workflow request")
    request.invariants()
    validate_execution_dispatch_policy(request.dispatch_policy)
    validate_execution_context(request.execution_context)


def validate_execution_dispatch_workflow_result(
    result: CorrectiveActionExecutionDispatchWorkflowResult,
) -> None:
    """Validate workflow lineage, nested dispatch result, and lifecycle."""

    if not isinstance(result, CorrectiveActionExecutionDispatchWorkflowResult):
        raise TypeError("invalid dispatch workflow result")
    result.invariants()
    validate_execution_dispatch_workflow_request(result.request)
    validate_execution_dispatch_request(result.dispatch_request)
    validate_execution_dispatch_result(result.dispatch_result)
    validate_dispatch_state(result.dispatch_state)


def dispatch_corrective_action_execution(
    request: CorrectiveActionExecutionDispatchWorkflowRequest,
    workflow_service: CorrectiveActionExecutionDispatchWorkflowService,
) -> CorrectiveActionExecutionDispatchWorkflowResult:
    """Delegate once to the explicitly supplied production workflow."""

    return workflow_service.run(request)


def _workflow_request_identity(values):
    planning = values["planning_result"]
    policy = values["dispatch_policy"]
    context = values["execution_context"]
    return {
        "workflow_version": values["workflow_version"],
        "planning_result_fingerprint": _field(planning, "result_fingerprint"),
        "policy_fingerprint": _field(policy, "policy_fingerprint"),
        "context_fingerprint": _field(context, "context_fingerprint"),
    }


def _workflow_result_identity(values):
    return {
        "workflow_version": values["workflow_version"],
        "request_fingerprint": _field(values["request"], "request_fingerprint"),
        "descriptor_fingerprint": _field(
            values["descriptor"], "descriptor_fingerprint"
        ),
        "operational_outcome": values["operational_outcome"],
        "dispatch_result_fingerprint": _field(
            values["dispatch_result"], "result_fingerprint"
        ),
        "dispatch_state_fingerprint": _field(
            values["dispatch_state"], "state_fingerprint"
        ),
    }


def _field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)
