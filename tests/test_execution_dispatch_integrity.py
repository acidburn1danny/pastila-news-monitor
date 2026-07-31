"""M6C.6B Part 4 cross-contract integrity and privacy audit tests."""

import pytest
from pydantic import ValidationError
from test_corrective_action_execution_dispatch_contracts import (
    _context,
    _descriptor,
    _planning_result,
)

from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutionDispatchWorkflowRequest,
    CorrectiveActionExecutorBinding,
    CorrectiveActionExecutorBindings,
    CorrectiveActionExecutorRegistry,
    build_standard_corrective_action_execution_dispatch_policy,
    validate_execution_dispatch_workflow_request,
    validate_executor_bindings,
)
from pastila_scout.editor.qa.models import fingerprint


class _MutableDescriptorExecutor:
    def __init__(self, descriptor):
        self.advertised_descriptor = descriptor

    @property
    def descriptor(self):
        return self.advertised_descriptor

    def execute(self, request):  # pragma: no cover - audit never invokes
        raise AssertionError


def test_binding_revalidation_detects_post_construction_descriptor_change() -> None:
    plan_result = _planning_result(CorrectiveAction.REQUEST_REGENERATION)
    descriptor = _descriptor(plan_result.plan)
    executor = _MutableDescriptorExecutor(descriptor)
    registry = CorrectiveActionExecutorRegistry.build((descriptor,))
    bindings = CorrectiveActionExecutorBindings.build(
        registry, (CorrectiveActionExecutorBinding(descriptor, executor),)
    )
    other = _descriptor(_planning_result(CorrectiveAction.REQUEST_MANUAL_REVIEW).plan)
    executor.advertised_descriptor = other
    with pytest.raises(ValueError, match="descriptor identity"):
        validate_executor_bindings(bindings)


def test_bindings_reject_equal_but_reconstructed_registry_descriptor() -> None:
    plan_result = _planning_result(CorrectiveAction.REQUEST_REGENERATION)
    descriptor = _descriptor(plan_result.plan)
    reconstructed = type(descriptor).model_validate(descriptor.model_dump())
    executor = _MutableDescriptorExecutor(reconstructed)
    registry = CorrectiveActionExecutorRegistry.build((descriptor,))
    with pytest.raises(ValueError, match="exactly cover"):
        CorrectiveActionExecutorBindings.build(
            registry,
            (CorrectiveActionExecutorBinding(reconstructed, executor),),
        )


def test_workflow_validator_revalidates_nested_policy_and_context() -> None:
    planning = _planning_result(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    )
    policy = build_standard_corrective_action_execution_dispatch_policy()
    context = _context()
    request = CorrectiveActionExecutionDispatchWorkflowRequest.build(
        planning_result=planning,
        dispatch_policy=policy,
        execution_context=context,
    )
    corrupt_policy = policy.model_copy(update={"policy_fingerprint": "sha256:bad"})
    identity = {
        "workflow_version": request.workflow_version,
        "planning_result_fingerprint": planning.result_fingerprint,
        "policy_fingerprint": corrupt_policy.policy_fingerprint,
        "context_fingerprint": context.context_fingerprint,
    }
    forged = request.model_copy(
        update={
            "dispatch_policy": corrupt_policy,
            "request_fingerprint": fingerprint(identity),
        }
    )
    forged.invariants()  # Outer identity alone is internally consistent.
    with pytest.raises(ValueError, match="integrity validation"):
        validate_execution_dispatch_workflow_request(forged)


def test_authoritative_runtime_contracts_are_frozen() -> None:
    planning = _planning_result(CorrectiveAction.REQUEST_REGENERATION)
    request = CorrectiveActionExecutionDispatchWorkflowRequest.build(
        planning_result=planning,
        dispatch_policy=build_standard_corrective_action_execution_dispatch_policy(),
        execution_context=_context(),
    )
    with pytest.raises(ValidationError):
        request.request_fingerprint = "sha256:bad"
