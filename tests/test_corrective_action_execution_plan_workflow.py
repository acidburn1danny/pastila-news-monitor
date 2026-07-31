"""M6C.6A Part 3 production-composition tests."""

import ast
from pathlib import Path

from test_corrective_action_execution_plan_mapping import _decision_result

from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionPlanOutcome,
    CorrectiveActionExecutionPlanService,
    CorrectiveActionPlanningWorkflowDescriptor,
    CorrectiveActionPlanningWorkflowRequest,
    CorrectiveActionPlanningWorkflowService,
    CorrectiveActionPlanningWorkflowStatus,
    build_standard_corrective_action_execution_plan_policy,
    build_standard_corrective_action_execution_planning_service,
    generate_execution_plan,
    render_corrective_action_planning_workflow_report,
    serialize_corrective_action_planning_workflow_report,
)


class SpyPlanningService:
    def __init__(self, *, fail=False):
        self.calls = 0
        self.fail = fail
        self.delegate = CorrectiveActionExecutionPlanService()
        self.result = None

    def plan(self, request):
        self.calls += 1
        if self.fail:
            raise RuntimeError("API_KEY=secret C:\\private\\draft.txt")
        self.result = self.delegate.plan(request)
        return self.result


def _workflow_request(action=CorrectiveAction.CONTINUE_WORKFLOW, **policy_values):
    policy = build_standard_corrective_action_execution_plan_policy()
    if policy_values:
        policy = policy.build(**policy_values)
    return CorrectiveActionPlanningWorkflowRequest.build(
        _decision_result(action), policy
    )


def test_workflow_success_invokes_planning_once_and_preserves_identity() -> None:
    planning_service = SpyPlanningService()
    workflow = CorrectiveActionPlanningWorkflowService(
        planning_service=planning_service
    )
    request = _workflow_request(CorrectiveAction.REQUEST_REGENERATION)
    result = workflow.execute(request)
    assert planning_service.calls == 1
    assert result.workflow_status is CorrectiveActionPlanningWorkflowStatus.COMPLETED
    assert result.decision_result is request.decision_result
    assert result.plan_result is planning_service.result
    assert result.plan_result.plan.decision_result is request.decision_result
    assert result.plan_result.operational_outcome is (
        CorrectiveActionExecutionPlanOutcome.COMPLETED
    )


def test_invalid_workflow_request_never_invokes_planning() -> None:
    planning_service = SpyPlanningService()
    result = CorrectiveActionPlanningWorkflowService(
        planning_service=planning_service
    ).execute(object())
    assert planning_service.calls == 0
    assert result.workflow_status is (
        CorrectiveActionPlanningWorkflowStatus.FAILED_INVALID_INPUT
    )
    assert result.plan_result is None and result.decision_result is None


def test_planning_failure_is_a_completed_well_formed_workflow() -> None:
    planning_service = SpyPlanningService()
    request = _workflow_request(
        CorrectiveAction.HALT_WORKFLOW,
        halt_is_non_executable=False,
    )
    result = CorrectiveActionPlanningWorkflowService(
        planning_service=planning_service
    ).execute(request)
    assert planning_service.calls == 1
    assert result.workflow_status is CorrectiveActionPlanningWorkflowStatus.COMPLETED
    assert result.plan_result.operational_outcome is (
        CorrectiveActionExecutionPlanOutcome.FAILED_POLICY_VALIDATION
    )
    assert result.plan_result.plan is None
    assert result.report.planning_outcome == "failed_policy_validation"


def test_unexpected_composition_failure_is_sanitized() -> None:
    service = SpyPlanningService(fail=True)
    result = CorrectiveActionPlanningWorkflowService(planning_service=service).execute(
        _workflow_request()
    )
    assert service.calls == 1
    assert result.workflow_status is (
        CorrectiveActionPlanningWorkflowStatus.FAILED_INTERNAL
    )
    serialized = result.model_dump_json()
    assert "secret" not in serialized and "private" not in serialized


def test_descriptor_builder_and_results_are_deterministic() -> None:
    assert CorrectiveActionPlanningWorkflowDescriptor.build() == (
        CorrectiveActionPlanningWorkflowDescriptor.build()
    )
    first = build_standard_corrective_action_execution_planning_service().execute(
        _workflow_request()
    )
    second = build_standard_corrective_action_execution_planning_service().execute(
        _workflow_request()
    )
    assert first.result_fingerprint == second.result_fingerprint
    assert first.report == second.report


def test_helper_delegates_to_supplied_workflow_without_planning_logic() -> None:
    class WorkflowSpy:
        def __init__(self):
            self.calls = 0
            self.request = None

        def execute(self, request):
            self.calls += 1
            self.request = request
            return "delegated"

    spy = WorkflowSpy()
    decision_result = _decision_result(CorrectiveAction.NO_ACTION)
    result = generate_execution_plan(decision_result, workflow_service=spy)
    assert result == "delegated" and spy.calls == 1
    assert spy.request.decision_result is decision_result


def test_workflow_reporting_and_serialization_are_safe_and_deterministic() -> None:
    result = build_standard_corrective_action_execution_planning_service().execute(
        _workflow_request(CorrectiveAction.REQUEST_REVISION)
    )
    serialized = serialize_corrective_action_planning_workflow_report(result.report)
    rendered = render_corrective_action_planning_workflow_report(result.report)
    assert serialized == serialize_corrective_action_planning_workflow_report(
        result.report
    )
    assert result.plan_result.result_fingerprint in serialized
    forbidden = (
        "integration_result",
        "episode_draft",
        "finding",
        "evidence",
        "prompt",
        "provider_response",
        "credential",
    )
    assert all(token not in serialized.casefold() for token in forbidden)
    assert all(token not in rendered.casefold() for token in forbidden)


def test_part_three_has_no_executor_or_infrastructure_imports() -> None:
    package = Path("src/pastila_scout/editor/qa/corrective_action/execution_plan")
    imported = set()
    for path in package.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
    forbidden = (
        "executor",
        "dispatcher",
        "publication",
        "queue",
        "notification",
        "database",
        "pastila_scout.cli",
        "openai",
        "httpx",
    )
    assert all(not any(token in module for module in imported) for token in forbidden)
