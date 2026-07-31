"""M6C.6B Part 1 immutable dispatch-contract tests."""

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError
from test_corrective_action_execution_plan_mapping import _planning_request

import pastila_scout.editor.qa.corrective_action.execution_dispatch as public_api
from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionAuthorizationState,
    CorrectiveActionExecutionContext,
    CorrectiveActionExecutionDispatchDescriptor,
    CorrectiveActionExecutionDispatchDiagnostic,
    CorrectiveActionExecutionDispatchDiagnosticCategory,
    CorrectiveActionExecutionDispatchDiagnosticCode,
    CorrectiveActionExecutionDispatchOutcome,
    CorrectiveActionExecutionDispatchPolicy,
    CorrectiveActionExecutionDispatchRequest,
    CorrectiveActionExecutionDispatchResult,
    CorrectiveActionExecutionDispatchStatus,
    CorrectiveActionExecutionStatus,
    CorrectiveActionExecutor,
    CorrectiveActionExecutorDescriptor,
    CorrectiveActionExecutorOutcome,
    CorrectiveActionExecutorRequest,
    CorrectiveActionExecutorResult,
    build_execution_dispatch_report,
    build_standard_corrective_action_execution_dispatch_policy,
    render_execution_dispatch_report,
    serialize_execution_dispatch_report,
    validate_execution_context,
    validate_execution_dispatch_policy,
    validate_execution_dispatch_request,
    validate_execution_dispatch_result,
    validate_executor_descriptor,
    validate_executor_request,
    validate_executor_result,
)
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionPlanService,
    CorrectiveActionExecutionPlanType,
)


def _planning_result(action=CorrectiveAction.CONTINUE_WORKFLOW, **policy_values):
    return CorrectiveActionExecutionPlanService().plan(
        _planning_request(action, **policy_values)
    )


def _context(authorization=CorrectiveActionAuthorizationState.NOT_REQUIRED):
    return CorrectiveActionExecutionContext.build(
        authorization_state=authorization,
        dispatch_attempt_id="dispatch-attempt.1",
    )


def _dispatch_request(
    action=CorrectiveAction.CONTINUE_WORKFLOW,
    *,
    authorization=CorrectiveActionAuthorizationState.NOT_REQUIRED,
    **planning_policy,
):
    result = _planning_result(action, **planning_policy)
    return CorrectiveActionExecutionDispatchRequest.build(
        result,
        build_standard_corrective_action_execution_dispatch_policy(),
        _context(authorization),
    )


def _descriptor(plan, *, automatic=True, human=True):
    return CorrectiveActionExecutorDescriptor.build(
        executor_id=f"{plan.plan_type.value.replace('_', '-')}.v1",
        supported_capability=plan.required_capability,
        supported_plan_types=(plan.plan_type,),
        supports_automatic_invocation=automatic,
        supports_human_gated_invocation=human,
    )


def _executor_request(dispatch_request, descriptor):
    return CorrectiveActionExecutorRequest.build(
        planning_result=dispatch_request.planning_result,
        plan=dispatch_request.planning_result.plan,
        executor_descriptor=descriptor,
        execution_context=dispatch_request.execution_context,
    )


def _diagnostic(
    code, category=CorrectiveActionExecutionDispatchDiagnosticCategory.VALIDATION
):
    return CorrectiveActionExecutionDispatchDiagnostic.build(
        code=code,
        category=category,
        safe_message="The dispatch contract could not complete this operation.",
    )


def _dispatch_result(
    request,
    *,
    outcome,
    status,
    descriptor=None,
    executor_request=None,
    executor_result=None,
    diagnostic=None,
):
    report = build_execution_dispatch_report(
        request=request,
        operational_outcome=outcome,
        dispatch_status=status,
        executor_descriptor=descriptor,
        executor_request=executor_request,
        executor_result=executor_result,
        diagnostic=diagnostic,
    )
    return CorrectiveActionExecutionDispatchResult.build(
        request=request,
        operational_outcome=outcome,
        dispatch_status=status,
        executor_descriptor=descriptor,
        executor_request=executor_request,
        executor_result=executor_result,
        diagnostic=diagnostic,
        report=report,
    )


def test_public_inventory_enums_and_architecture_are_stable() -> None:
    expected = {
        "CorrectiveActionExecutionDispatchPolicy",
        "CorrectiveActionExecutionDispatchRequest",
        "CorrectiveActionExecutionContext",
        "CorrectiveActionExecutor",
        "CorrectiveActionExecutorDescriptor",
        "CorrectiveActionExecutorRequest",
        "CorrectiveActionExecutorResult",
        "CorrectiveActionExecutionDispatchResult",
    }
    assert expected <= set(public_api.__all__)
    assert len({item.value for item in CorrectiveActionExecutionDispatchStatus}) == 7
    assert len({item.value for item in CorrectiveActionExecutionDispatchOutcome}) == 9
    assert len({item.value for item in CorrectiveActionAuthorizationState}) == 5
    assert CorrectiveActionExecutionDispatchDescriptor.build() == (
        CorrectiveActionExecutionDispatchDescriptor.build()
    )


def test_policy_is_minimal_immutable_deterministic_and_semantically_fixed() -> None:
    first = build_standard_corrective_action_execution_dispatch_policy()
    second = build_standard_corrective_action_execution_dispatch_policy()
    assert first == second
    with pytest.raises(ValidationError):
        first.allow_automatic_dispatch = False
    with pytest.raises(ValidationError, match="exact capability"):
        CorrectiveActionExecutionDispatchPolicy.build(
            require_exact_capability_match=False
        )
    with pytest.raises(ValidationError, match="non-executable"):
        CorrectiveActionExecutionDispatchPolicy.build(
            treat_non_executable_as_completed=False
        )
    changed = CorrectiveActionExecutionDispatchPolicy.build(
        allow_automatic_dispatch=False
    )
    assert changed.policy_fingerprint != first.policy_fingerprint


def test_execution_context_is_narrow_safe_immutable_and_deterministic() -> None:
    first = _context(CorrectiveActionAuthorizationState.GRANTED)
    second = _context(CorrectiveActionAuthorizationState.GRANTED)
    assert first == second
    with pytest.raises(ValidationError):
        first.authorization_state = CorrectiveActionAuthorizationState.DENIED
    for identifier in ("../private", "API KEY", "secret-token.v1", "MixedCase"):
        with pytest.raises(ValidationError):
            CorrectiveActionExecutionContext.build(
                authorization_state=CorrectiveActionAuthorizationState.UNKNOWN,
                dispatch_attempt_id=identifier,
            )


def test_dispatch_request_preserves_complete_planning_result_identity() -> None:
    planning_result = _planning_result(CorrectiveAction.CONTINUE_WORKFLOW)
    request = CorrectiveActionExecutionDispatchRequest.build(
        planning_result,
        build_standard_corrective_action_execution_dispatch_policy(),
        _context(),
    )
    assert request.planning_result is planning_result
    assert set(type(request).model_fields) == {
        "contract_version",
        "planning_result",
        "policy",
        "execution_context",
        "request_fingerprint",
    }
    validate_execution_dispatch_request(request)


def test_executor_descriptor_requires_exact_capability_and_canonical_plan_types() -> (
    None
):
    plan = _planning_result(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    ).plan
    descriptor = _descriptor(plan)
    assert descriptor.supported_plan_types == (plan.plan_type,)
    with pytest.raises(ValidationError, match="incompatible"):
        CorrectiveActionExecutorDescriptor.build(
            executor_id="wrong-capability.v1",
            supported_capability=plan.required_capability,
            supported_plan_types=(CorrectiveActionExecutionPlanType.REGENERATE_DRAFT,),
            supports_automatic_invocation=True,
            supports_human_gated_invocation=False,
        )
    with pytest.raises(ValidationError, match="unique"):
        CorrectiveActionExecutorDescriptor.build(
            executor_id="duplicate-plans.v1",
            supported_capability=plan.required_capability,
            supported_plan_types=(plan.plan_type, plan.plan_type),
            supports_automatic_invocation=True,
            supports_human_gated_invocation=False,
        )


def test_executor_request_preserves_identity_and_enforces_authorization() -> None:
    dispatch_request = _dispatch_request(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    )
    descriptor = _descriptor(dispatch_request.planning_result.plan)
    request = _executor_request(dispatch_request, descriptor)
    assert request.planning_result is dispatch_request.planning_result
    assert request.plan is dispatch_request.planning_result.plan
    assert request.executor_descriptor is descriptor
    validate_executor_request(request)

    human_dispatch = _dispatch_request(
        CorrectiveAction.REQUEST_REGENERATION,
        authorization=CorrectiveActionAuthorizationState.REQUIRED_NOT_GRANTED,
    )
    with pytest.raises(ValidationError, match="granted"):
        _executor_request(
            human_dispatch, _descriptor(human_dispatch.planning_result.plan)
        )


def test_executor_protocol_is_capability_neutral_and_structural() -> None:
    dispatch_request = _dispatch_request(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    )
    descriptor = _descriptor(dispatch_request.planning_result.plan)
    executor_request = _executor_request(dispatch_request, descriptor)

    class FakeExecutor:
        def __init__(self):
            self._descriptor = descriptor

        @property
        def descriptor(self):
            return self._descriptor

        def execute(self, request):
            return CorrectiveActionExecutorResult.build(
                executor_descriptor=self.descriptor,
                request=request,
                operational_outcome=CorrectiveActionExecutorOutcome.COMPLETED,
                execution_status=CorrectiveActionExecutionStatus.COMPLETED,
                diagnostic=None,
            )

    fake = FakeExecutor()
    assert isinstance(fake, CorrectiveActionExecutor)
    result = fake.execute(executor_request)
    assert result.request is executor_request
    assert result.executor_descriptor is descriptor


@pytest.mark.parametrize(
    ("outcome", "execution_status"),
    (
        (
            CorrectiveActionExecutorOutcome.FAILED_INVALID_REQUEST,
            CorrectiveActionExecutionStatus.NOT_STARTED,
        ),
        (
            CorrectiveActionExecutorOutcome.FAILED_PRECONDITION,
            CorrectiveActionExecutionStatus.NOT_STARTED,
        ),
        (
            CorrectiveActionExecutorOutcome.FAILED_AUTHORIZATION,
            CorrectiveActionExecutionStatus.NOT_STARTED,
        ),
        (
            CorrectiveActionExecutorOutcome.FAILED_INTERNAL,
            CorrectiveActionExecutionStatus.FAILED,
        ),
    ),
)
def test_generic_executor_failure_result_shapes(outcome, execution_status) -> None:
    dispatch_request = _dispatch_request(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    )
    descriptor = _descriptor(dispatch_request.planning_result.plan)
    request = _executor_request(dispatch_request, descriptor)
    result = CorrectiveActionExecutorResult.build(
        executor_descriptor=descriptor,
        request=request,
        operational_outcome=outcome,
        execution_status=execution_status,
        diagnostic=_diagnostic(
            CorrectiveActionExecutionDispatchDiagnosticCode.EXECUTOR_INVOCATION_FAILED,
            CorrectiveActionExecutionDispatchDiagnosticCategory.EXECUTOR,
        ),
    )
    assert result.request is request and result.diagnostic is not None


def test_non_dispatchable_and_authorization_gated_result_shapes() -> None:
    non_dispatchable = _dispatch_result(
        _dispatch_request(),
        outcome=CorrectiveActionExecutionDispatchOutcome.COMPLETED,
        status=CorrectiveActionExecutionDispatchStatus.NOT_DISPATCHABLE,
    )
    assert non_dispatchable.executor_descriptor is None
    assert not non_dispatchable.report.dispatch_eligible

    request = _dispatch_request(
        CorrectiveAction.REQUEST_REGENERATION,
        authorization=CorrectiveActionAuthorizationState.REQUIRED_NOT_GRANTED,
    )
    descriptor = _descriptor(request.planning_result.plan)
    gated = _dispatch_result(
        request,
        outcome=CorrectiveActionExecutionDispatchOutcome.COMPLETED,
        status=CorrectiveActionExecutionDispatchStatus.AWAITING_AUTHORIZATION,
        descriptor=descriptor,
        diagnostic=_diagnostic(
            CorrectiveActionExecutionDispatchDiagnosticCode.HUMAN_AUTHORIZATION_REQUIRED,
            CorrectiveActionExecutionDispatchDiagnosticCategory.AUTHORIZATION,
        ),
    )
    assert gated.executor_descriptor is descriptor
    assert gated.executor_request is None and gated.executor_result is None


@pytest.mark.parametrize(
    "code",
    (
        CorrectiveActionExecutionDispatchDiagnosticCode.EXECUTOR_NOT_FOUND,
        CorrectiveActionExecutionDispatchDiagnosticCode.AMBIGUOUS_EXECUTOR_MATCH,
    ),
)
def test_resolution_failure_contract_shapes(code) -> None:
    result = _dispatch_result(
        _dispatch_request(
            CorrectiveAction.REQUEST_REVISION,
            revision_requires_human_authorization=False,
        ),
        outcome=(CorrectiveActionExecutionDispatchOutcome.FAILED_CAPABILITY_RESOLUTION),
        status=CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED,
        diagnostic=_diagnostic(
            code, CorrectiveActionExecutionDispatchDiagnosticCategory.RESOLUTION
        ),
    )
    assert result.executor_request is None and result.executor_result is None


def test_executor_completed_and_failed_dispatch_shapes_preserve_identity() -> None:
    request = _dispatch_request(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    )
    descriptor = _descriptor(request.planning_result.plan)
    executor_request = _executor_request(request, descriptor)
    completed_executor = CorrectiveActionExecutorResult.build(
        executor_descriptor=descriptor,
        request=executor_request,
        operational_outcome=CorrectiveActionExecutorOutcome.COMPLETED,
        execution_status=CorrectiveActionExecutionStatus.COMPLETED,
        diagnostic=None,
    )
    completed = _dispatch_result(
        request,
        outcome=CorrectiveActionExecutionDispatchOutcome.COMPLETED,
        status=CorrectiveActionExecutionDispatchStatus.EXECUTOR_COMPLETED,
        descriptor=descriptor,
        executor_request=executor_request,
        executor_result=completed_executor,
    )
    assert completed.request is request
    assert completed.executor_request is executor_request
    assert completed.executor_result is completed_executor
    validate_execution_dispatch_result(completed)

    failed_executor = CorrectiveActionExecutorResult.build(
        executor_descriptor=descriptor,
        request=executor_request,
        operational_outcome=CorrectiveActionExecutorOutcome.FAILED_INTERNAL,
        execution_status=CorrectiveActionExecutionStatus.FAILED,
        diagnostic=_diagnostic(
            CorrectiveActionExecutionDispatchDiagnosticCode.EXECUTOR_INVOCATION_FAILED,
            CorrectiveActionExecutionDispatchDiagnosticCategory.EXECUTOR,
        ),
    )
    failed = _dispatch_result(
        request,
        outcome=CorrectiveActionExecutionDispatchOutcome.COMPLETED,
        status=CorrectiveActionExecutionDispatchStatus.EXECUTOR_FAILED,
        descriptor=descriptor,
        executor_request=executor_request,
        executor_result=failed_executor,
    )
    assert failed.report.diagnostic_code is (
        CorrectiveActionExecutionDispatchDiagnosticCode.EXECUTOR_INVOCATION_FAILED
    )


def test_internal_failure_shape_and_report_consistency() -> None:
    request = _dispatch_request(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    )
    result = _dispatch_result(
        request,
        outcome=CorrectiveActionExecutionDispatchOutcome.FAILED_INTERNAL,
        status=CorrectiveActionExecutionDispatchStatus.DISPATCH_FAILED,
        diagnostic=_diagnostic(
            CorrectiveActionExecutionDispatchDiagnosticCode.DISPATCH_INTERNAL_FAILURE,
            CorrectiveActionExecutionDispatchDiagnosticCategory.INTERNAL,
        ),
    )
    values = result.report.model_dump(exclude={"report_fingerprint"}, mode="python")
    values["plan_type"] = CorrectiveActionExecutionPlanType.REGENERATE_DRAFT
    contradictory = type(result.report).build(**values)
    with pytest.raises(ValidationError, match="contradicts"):
        CorrectiveActionExecutionDispatchResult.build(
            request=request,
            operational_outcome=result.operational_outcome,
            dispatch_status=result.dispatch_status,
            executor_descriptor=None,
            executor_request=None,
            executor_result=None,
            diagnostic=result.diagnostic,
            report=contradictory,
        )


def test_fingerprints_versions_and_unknown_values_fail_closed() -> None:
    request = _dispatch_request()
    with pytest.raises(ValidationError):
        CorrectiveActionExecutionDispatchRequest.model_validate(
            {**request.model_dump(), "request_fingerprint": "sha256:bad"}
        )
    with pytest.raises(ValidationError):
        CorrectiveActionExecutionDispatchRequest.model_validate(
            {**request.model_dump(), "contract_version": "999"}
        )
    values = request.execution_context.model_dump()
    values["authorization_state"] = "maybe"
    with pytest.raises(ValidationError):
        CorrectiveActionExecutionContext.model_validate(values)


def test_all_contract_fingerprint_tampering_fails_closed() -> None:
    request = _dispatch_request(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    )
    descriptor = _descriptor(request.planning_result.plan)
    executor_request = _executor_request(request, descriptor)
    executor_result = CorrectiveActionExecutorResult.build(
        executor_descriptor=descriptor,
        request=executor_request,
        operational_outcome=CorrectiveActionExecutorOutcome.COMPLETED,
        execution_status=CorrectiveActionExecutionStatus.COMPLETED,
        diagnostic=None,
    )
    dispatch_result = _dispatch_result(
        request,
        outcome=CorrectiveActionExecutionDispatchOutcome.COMPLETED,
        status=CorrectiveActionExecutionDispatchStatus.EXECUTOR_COMPLETED,
        descriptor=descriptor,
        executor_request=executor_request,
        executor_result=executor_result,
    )
    cases = (
        (
            validate_execution_dispatch_policy,
            request.policy.model_copy(update={"policy_fingerprint": "sha256:bad"}),
        ),
        (
            validate_execution_context,
            request.execution_context.model_copy(
                update={"context_fingerprint": "sha256:bad"}
            ),
        ),
        (
            validate_executor_descriptor,
            descriptor.model_copy(update={"descriptor_fingerprint": "sha256:bad"}),
        ),
        (
            validate_executor_request,
            executor_request.model_copy(update={"request_fingerprint": "sha256:bad"}),
        ),
        (
            validate_executor_result,
            executor_result.model_copy(update={"result_fingerprint": "sha256:bad"}),
        ),
        (
            validate_execution_dispatch_result,
            dispatch_result.model_copy(update={"result_fingerprint": "sha256:bad"}),
        ),
    )
    for validator, value in cases:
        with pytest.raises(ValueError):
            validator(value)


def test_failed_planning_result_cannot_become_completed_dispatch() -> None:
    failed_planning = CorrectiveActionExecutionPlanService().plan(object())
    request = CorrectiveActionExecutionDispatchRequest.build(
        failed_planning,
        build_standard_corrective_action_execution_dispatch_policy(),
        _context(),
    )
    report = build_execution_dispatch_report(
        request=request,
        operational_outcome=CorrectiveActionExecutionDispatchOutcome.COMPLETED,
        dispatch_status=CorrectiveActionExecutionDispatchStatus.NOT_DISPATCHABLE,
        executor_descriptor=None,
        executor_request=None,
        executor_result=None,
        diagnostic=None,
    )
    with pytest.raises(ValidationError, match="failed planning"):
        CorrectiveActionExecutionDispatchResult.build(
            request=request,
            operational_outcome=CorrectiveActionExecutionDispatchOutcome.COMPLETED,
            dispatch_status=CorrectiveActionExecutionDispatchStatus.NOT_DISPATCHABLE,
            executor_descriptor=None,
            executor_request=None,
            executor_result=None,
            diagnostic=None,
            report=report,
        )


def test_nested_upstream_fingerprint_tampering_is_not_repaired() -> None:
    request = _dispatch_request()
    bad_planning = request.planning_result.model_copy(
        update={"result_fingerprint": "sha256:bad"}
    )
    with pytest.raises(ValidationError):
        CorrectiveActionExecutionDispatchRequest.build(
            bad_planning, request.policy, request.execution_context
        )


def test_safe_reporting_serialization_and_diagnostics_exclude_content() -> None:
    result = _dispatch_result(
        _dispatch_request(),
        outcome=CorrectiveActionExecutionDispatchOutcome.COMPLETED,
        status=CorrectiveActionExecutionDispatchStatus.NOT_DISPATCHABLE,
    )
    serialized = serialize_execution_dispatch_report(result.report)
    rendered = render_execution_dispatch_report(result.report)
    assert serialized == serialize_execution_dispatch_report(result.report)
    forbidden = (
        "integration_result",
        "decision_result",
        "draft",
        "finding",
        "evidence",
        "prompt",
        "provider",
        "credential",
        "queue",
    )
    assert all(value not in serialized.casefold() for value in forbidden)
    assert all(value not in rendered.casefold() for value in forbidden)
    with pytest.raises(ValidationError, match="unsafe"):
        CorrectiveActionExecutionDispatchDiagnostic.build(
            code=(
                CorrectiveActionExecutionDispatchDiagnosticCode.DISPATCH_INTERNAL_FAILURE
            ),
            category=CorrectiveActionExecutionDispatchDiagnosticCategory.INTERNAL,
            safe_message="API_KEY=secret C:\\private\\draft.txt",
        )


def test_dispatch_package_has_no_dispatcher_or_infrastructure_imports() -> None:
    package = Path("src/pastila_scout/editor/qa/corrective_action/execution_dispatch")
    imported = set()
    names = {path.name for path in package.glob("*.py")}
    assert not names & {
        "execution.py",
        "adapters.py",
        "providers.py",
    }
    for path in package.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
    forbidden = (
        "openai",
        "httpx",
        "database",
        "queue",
        "notification",
        "publication",
        "pastila_scout.cli",
        "reviewer",
        "provider",
    )
    assert all(not any(value in module for module in imported) for value in forbidden)
    upstream = Path("src/pastila_scout/editor/qa/corrective_action/execution_plan")
    assert all(
        "execution_dispatch" not in path.read_text(encoding="utf-8")
        for path in upstream.glob("*.py")
    )
