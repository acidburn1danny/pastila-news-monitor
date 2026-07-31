"""M6C.6A Part 1 architecture and immutable-contract tests."""

import ast
import inspect

import pytest
from pydantic import ValidationError
from test_corrective_action_decision_contracts import _completed_integration

import pastila_scout.editor.qa.corrective_action.execution_plan as public_api
from pastila_scout.editor.qa.corrective_action import (
    CorrectiveActionDecisionRequest,
    CorrectiveActionDecisionService,
    build_standard_corrective_action_decision_policy,
)
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionMode,
    CorrectiveActionExecutionPlan,
    CorrectiveActionExecutionPlanDescriptor,
    CorrectiveActionExecutionPlanDiagnostic,
    CorrectiveActionExecutionPlanDiagnosticCode,
    CorrectiveActionExecutionPlanOutcome,
    CorrectiveActionExecutionPlanRequest,
    CorrectiveActionExecutionPlanResult,
    CorrectiveActionExecutionPlanStage,
    CorrectiveActionExecutionPlanType,
    CorrectiveActionExecutionPreconditions,
    build_execution_plan_report,
    build_standard_corrective_action_execution_plan_policy,
    render_execution_plan_report,
    serialize_execution_plan_report,
    validate_execution_plan,
    validate_execution_plan_policy,
    validate_execution_plan_request,
    validate_execution_plan_result,
)


def _decision_result():
    request = CorrectiveActionDecisionRequest.build(
        _completed_integration(),
        build_standard_corrective_action_decision_policy(),
    )
    return CorrectiveActionDecisionService().decide(request)


def _request():
    result = _decision_result()
    return CorrectiveActionExecutionPlanRequest.build(
        result, build_standard_corrective_action_execution_plan_policy()
    )


def _plan(request=None):
    request = request or _request()
    decision = request.decision_result.decision
    return CorrectiveActionExecutionPlan.build(
        plan_type=CorrectiveActionExecutionPlanType.NO_CORRECTIVE_EXECUTION,
        execution_mode=CorrectiveActionExecutionMode.NON_EXECUTABLE,
        required_capability=CorrectiveActionExecutionCapability.NONE,
        source_action=decision.action,
        source_reason=decision.reason,
        preconditions=CorrectiveActionExecutionPreconditions(),
        decision_result=request.decision_result,
        policy_fingerprint=request.planning_policy.policy_fingerprint,
        request_fingerprint=request.request_fingerprint,
    )


def _completed_result(plan=None):
    plan = plan or _plan()
    report = build_execution_plan_report(
        operational_outcome=CorrectiveActionExecutionPlanOutcome.COMPLETED,
        plan=plan,
        diagnostic=None,
        request_fingerprint=plan.request_fingerprint,
        policy_fingerprint=plan.policy_fingerprint,
        input_complete=True,
        decision_result_fingerprint=plan.decision_result.result_fingerprint,
    )
    return CorrectiveActionExecutionPlanResult.build(
        operational_outcome=CorrectiveActionExecutionPlanOutcome.COMPLETED,
        plan=plan,
        diagnostic=None,
        report=report,
    )


def test_public_inventory_and_taxonomies_are_complete() -> None:
    assert {
        "CorrectiveActionExecutionPlan",
        "CorrectiveActionExecutionPlanRequest",
        "CorrectiveActionExecutionPlanResult",
        "CorrectiveActionExecutionPlanPolicy",
    } <= set(public_api.__all__)
    assert {item.value for item in CorrectiveActionExecutionPlanType} == {
        "no_corrective_execution",
        "revise_draft",
        "regenerate_draft",
        "create_manual_review_request",
        "block_automatic_continuation",
    }
    assert len({item.value for item in CorrectiveActionExecutionMode}) == 3
    assert len({item.value for item in CorrectiveActionExecutionCapability}) == 5
    assert CorrectiveActionExecutionPlanDescriptor.build() == (
        CorrectiveActionExecutionPlanDescriptor.build()
    )


def test_contracts_and_nested_collections_are_immutable() -> None:
    descriptor = CorrectiveActionExecutionPlanDescriptor.build()
    request = _request()
    plan = _plan(request)
    with pytest.raises(ValidationError):
        descriptor.ownership = "execution"
    with pytest.raises(ValidationError):
        request.contract_version = "2"
    with pytest.raises(ValidationError):
        plan.preconditions.requires_original_draft = True
    assert isinstance(descriptor.non_responsibilities, tuple)


def test_authoritative_object_identity_is_preserved() -> None:
    decision_result = _decision_result()
    request = CorrectiveActionExecutionPlanRequest.build(
        decision_result, build_standard_corrective_action_execution_plan_policy()
    )
    plan = _plan(request)
    result = _completed_result(plan)
    assert request.decision_result is decision_result
    assert plan.decision_result is decision_result
    assert result.plan is plan


def test_policy_request_and_plan_fingerprints_are_deterministic() -> None:
    decision_result = _decision_result()
    first_policy = build_standard_corrective_action_execution_plan_policy()
    second_policy = build_standard_corrective_action_execution_plan_policy()
    first_request = CorrectiveActionExecutionPlanRequest.build(
        decision_result, first_policy
    )
    second_request = CorrectiveActionExecutionPlanRequest.build(
        decision_result, second_policy
    )
    assert first_policy.policy_fingerprint == second_policy.policy_fingerprint
    assert first_request.request_fingerprint == second_request.request_fingerprint
    assert (
        _plan(first_request).plan_fingerprint == _plan(second_request).plan_fingerprint
    )
    changed = first_policy.build(regeneration_automatic_allowed=True)
    assert changed.policy_fingerprint != first_policy.policy_fingerprint


def test_tampered_fingerprints_and_unknown_versions_fail_closed() -> None:
    policy = build_standard_corrective_action_execution_plan_policy()
    with pytest.raises(ValidationError):
        type(policy).model_validate(
            {**policy.model_dump(), "policy_fingerprint": "sha256:bad"}
        )
    request = _request()
    with pytest.raises(ValidationError):
        type(request).model_validate(
            {**request.model_dump(), "contract_version": "999"}
        )
    plan = _plan(request)
    with pytest.raises(ValidationError):
        type(plan).model_validate(
            {**plan.model_dump(), "plan_fingerprint": "sha256:bad"}
        )


def test_mode_capability_and_authorization_consistency_fail_closed() -> None:
    plan = _plan()
    values = plan.model_dump(exclude={"plan_fingerprint"}, mode="python")
    values["automatic_execution_allowed"] = True
    with pytest.raises(ValidationError):
        CorrectiveActionExecutionPlan.build(**values)
    values = plan.model_dump(exclude={"plan_fingerprint"}, mode="python")
    values["required_capability"] = CorrectiveActionExecutionCapability.DRAFT_REVISION
    with pytest.raises(ValidationError):
        CorrectiveActionExecutionPlan.build(**values)


def test_completed_and_failed_results_are_strictly_separated() -> None:
    plan = _plan()
    completed = _completed_result(plan)
    validate_execution_plan_result(completed)
    with pytest.raises(ValidationError):
        CorrectiveActionExecutionPlanResult.build(
            operational_outcome=(
                CorrectiveActionExecutionPlanOutcome.FAILED_INVALID_INPUT
            ),
            plan=plan,
            diagnostic=None,
            report=completed.report,
        )

    diagnostic = CorrectiveActionExecutionPlanDiagnostic.build(
        code=CorrectiveActionExecutionPlanDiagnosticCode.INVALID_REQUEST,
        safe_message="The planning request is invalid.",
        stage=CorrectiveActionExecutionPlanStage.REQUEST_VALIDATION,
    )
    report = build_execution_plan_report(
        operational_outcome=(CorrectiveActionExecutionPlanOutcome.FAILED_INVALID_INPUT),
        plan=None,
        diagnostic=diagnostic,
        request_fingerprint=None,
        policy_fingerprint=None,
        input_complete=False,
    )
    failed = CorrectiveActionExecutionPlanResult.build(
        operational_outcome=(CorrectiveActionExecutionPlanOutcome.FAILED_INVALID_INPUT),
        plan=None,
        diagnostic=diagnostic,
        report=report,
    )
    assert failed.plan is None and failed.diagnostic is diagnostic


def test_validators_preserve_lineage_and_reject_inconsistent_request() -> None:
    request = _request()
    plan = _plan(request)
    validate_execution_plan_policy(request.planning_policy)
    validate_execution_plan_request(request)
    validate_execution_plan(plan, request)
    other_request = _request()
    with pytest.raises(ValueError, match="identity"):
        validate_execution_plan(plan, other_request)


def test_safe_report_is_deterministic_and_contains_no_upstream_content() -> None:
    report = _completed_result().report
    serialized = serialize_execution_plan_report(report)
    rendered = render_execution_plan_report(report)
    assert serialized == serialize_execution_plan_report(report)
    forbidden = (
        "episode_draft",
        "article",
        "finding",
        "evidence",
        "recommendation",
        "prompt",
        "provider",
        "credential",
    )
    assert all(token not in serialized.casefold() for token in forbidden)
    assert all(token not in rendered.casefold() for token in forbidden)


def test_execution_plan_package_has_no_forbidden_dependencies_or_service() -> None:
    modules = (
        public_api,
        __import__(
            "pastila_scout.editor.qa.corrective_action.execution_plan.models",
            fromlist=["x"],
        ),
        __import__(
            "pastila_scout.editor.qa.corrective_action.execution_plan.validation",
            fromlist=["x"],
        ),
    )
    source = "\n".join(inspect.getsource(module) for module in modules)
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = (
        "openai",
        "sqlite",
        "httpx",
        "EditorialFinding",
        "GeneratorProvider",
        "ReviewerPipeline",
        "queue_adapter",
        "publication",
        "notification",
        "pastila_scout.cli",
    )
    assert all(
        not any(token in module_name for module_name in imported) for token in forbidden
    )
