"""High-value freeze-audit regressions for M6C.6A."""

import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError
from test_corrective_action_execution_plan_mapping import _planning_request
from test_corrective_action_execution_plan_workflow import _workflow_request

from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionPlan,
    CorrectiveActionExecutionPlanResult,
    CorrectiveActionExecutionPlanService,
    CorrectiveActionExecutionPlanType,
    CorrectiveActionExecutionPreconditions,
    CorrectiveActionPlanningWorkflowDiagnostic,
    CorrectiveActionPlanningWorkflowDiagnosticCode,
    CorrectiveActionPlanningWorkflowReport,
    CorrectiveActionPlanningWorkflowResult,
    build_standard_corrective_action_execution_planning_service,
)


def test_noncanonical_typed_preconditions_fail_closed() -> None:
    request = _planning_request(
        CorrectiveAction.REQUEST_REVISION,
        revision_requires_human_authorization=False,
    )
    plan = CorrectiveActionExecutionPlanService().plan(request).plan
    values = plan.model_dump(exclude={"plan_fingerprint"}, mode="python")
    values["preconditions"] = CorrectiveActionExecutionPreconditions()
    with pytest.raises(ValidationError, match="preconditions"):
        CorrectiveActionExecutionPlan.build(**values)


def test_planning_report_cannot_contradict_authoritative_plan() -> None:
    result = CorrectiveActionExecutionPlanService().plan(
        _planning_request(CorrectiveAction.CONTINUE_WORKFLOW)
    )
    values = result.report.model_dump(exclude={"report_fingerprint"}, mode="python")
    values["plan_type"] = CorrectiveActionExecutionPlanType.REVISE_DRAFT
    contradictory = type(result.report).build(**values)
    with pytest.raises(ValidationError, match="contradicts"):
        CorrectiveActionExecutionPlanResult.build(
            operational_outcome=result.operational_outcome,
            plan=result.plan,
            diagnostic=None,
            report=contradictory,
        )


def test_workflow_report_cannot_contradict_authoritative_planning_result() -> None:
    workflow = build_standard_corrective_action_execution_planning_service().execute(
        _workflow_request()
    )
    values = workflow.report.model_dump(exclude={"report_fingerprint"}, mode="python")
    values["planning_outcome"] = "failed_internal"
    contradictory = CorrectiveActionPlanningWorkflowReport.build(**values)
    with pytest.raises(ValidationError, match="contradicts"):
        CorrectiveActionPlanningWorkflowResult.build(
            descriptor=workflow.descriptor,
            workflow_status=workflow.workflow_status,
            decision_result=workflow.decision_result,
            plan_result=workflow.plan_result,
            diagnostic=None,
            report=contradictory,
        )


def test_workflow_diagnostic_rejects_secret_and_path_content() -> None:
    with pytest.raises(ValidationError, match="unsafe"):
        CorrectiveActionPlanningWorkflowDiagnostic.build(
            code=(
                CorrectiveActionPlanningWorkflowDiagnosticCode.INTERNAL_WORKFLOW_FAILURE
            ),
            safe_message="API_KEY=secret C:\\private\\draft.txt",
        )


def test_one_mapping_owner_and_no_reverse_upstream_dependency() -> None:
    package = Path("src/pastila_scout/editor/qa/corrective_action/execution_plan")
    owners = []
    for path in package.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        if "CorrectiveAction.CONTINUE_WORKFLOW" in source:
            owners.append(path.name)
    assert owners == ["evaluation.py"]

    upstream_modules = (
        "models.py",
        "policy.py",
        "evaluation.py",
        "state.py",
        "service.py",
        "composition.py",
        "reporting.py",
        "__init__.py",
    )
    upstream = Path("src/pastila_scout/editor/qa/corrective_action")
    for name in upstream_modules:
        source = (upstream / name).read_text(encoding="utf-8")
        assert "execution_plan" not in source


def test_convenience_helpers_delegate_without_mapping_duplication() -> None:
    from pastila_scout.editor.qa.corrective_action.execution_plan import (
        generate_execution_plan,
        plan_corrective_action_execution,
    )

    for helper in (generate_execution_plan, plan_corrective_action_execution):
        source = inspect.getsource(helper)
        assert "CorrectiveAction." not in source
        assert "REVISE_DRAFT" not in source
