"""M6C.6A Part 2 lifecycle, integrity, and service tests."""

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError
from test_corrective_action_execution_plan_mapping import _planning_request

from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionPlanDiagnosticCode,
    CorrectiveActionExecutionPlanEvaluator,
    CorrectiveActionExecutionPlanningLifecycle,
    CorrectiveActionExecutionPlanningState,
    CorrectiveActionExecutionPlanOutcome,
    CorrectiveActionExecutionPlanService,
    serialize_execution_plan_result,
    transition_planning_state,
)


def _successful_states():
    request = _planning_request(CorrectiveAction.CONTINUE_WORKFLOW)
    prepared = CorrectiveActionExecutionPlanningState.prepare(
        request_fingerprint=request.request_fingerprint,
        policy_fingerprint=request.planning_policy.policy_fingerprint,
        decision_result_fingerprint=request.decision_result.result_fingerprint,
    )
    validating = transition_planning_state(
        prepared, CorrectiveActionExecutionPlanningLifecycle.VALIDATING
    )
    planning = transition_planning_state(
        validating, CorrectiveActionExecutionPlanningLifecycle.PLANNING
    )
    planned = transition_planning_state(
        planning,
        CorrectiveActionExecutionPlanningLifecycle.PLANNED,
        plan_fingerprint="sha256:plan",
    )
    finalized = transition_planning_state(
        planned,
        CorrectiveActionExecutionPlanningLifecycle.FINALIZED,
        operational_outcome=CorrectiveActionExecutionPlanOutcome.COMPLETED,
    )
    return prepared, validating, planning, planned, finalized


def test_successful_lifecycle_is_revisioned_immutable_and_deterministic() -> None:
    states = _successful_states()
    assert tuple(state.revision for state in states) == (0, 1, 2, 3, 4)
    assert states[0].trace == ()
    assert tuple(event.sequence for event in states[-1].trace) == (0, 1, 2, 3)
    assert len({event.event_fingerprint for event in states[-1].trace}) == 4
    assert all(state.state_fingerprint.startswith("sha256:") for state in states)
    assert states == _successful_states()
    assert states[0].phase is CorrectiveActionExecutionPlanningLifecycle.PREPARED
    assert states[-1].phase is CorrectiveActionExecutionPlanningLifecycle.FINALIZED


@pytest.mark.parametrize(
    ("index", "target"),
    (
        (0, CorrectiveActionExecutionPlanningLifecycle.PLANNED),
        (1, CorrectiveActionExecutionPlanningLifecycle.FINALIZED),
        (2, CorrectiveActionExecutionPlanningLifecycle.FINALIZED),
        (3, CorrectiveActionExecutionPlanningLifecycle.FAILED),
        (4, CorrectiveActionExecutionPlanningLifecycle.PLANNING),
    ),
)
def test_invalid_and_terminal_transitions_are_rejected_without_mutation(
    index, target
) -> None:
    state = _successful_states()[index]
    before = state.model_dump(mode="python")
    with pytest.raises(ValueError, match="transition"):
        transition_planning_state(state, target)
    assert state.model_dump(mode="python") == before


def test_validation_and_planning_failure_paths_end_failed() -> None:
    prepared, validating, planning, _, _ = _successful_states()
    for state in (validating, planning):
        failed = transition_planning_state(
            state,
            CorrectiveActionExecutionPlanningLifecycle.FAILED,
            operational_outcome=(
                CorrectiveActionExecutionPlanOutcome.FAILED_INVALID_INPUT
            ),
            diagnostic_code=(
                CorrectiveActionExecutionPlanDiagnosticCode.INVALID_REQUEST
            ),
        )
        assert failed.phase is CorrectiveActionExecutionPlanningLifecycle.FAILED
        assert failed.revision == state.revision + 1
    assert prepared.revision == 0


class SpyEvaluator(CorrectiveActionExecutionPlanEvaluator):
    def __init__(self, *, fail=False):
        self.calls = 0
        self.fail = fail

    def evaluate(self, request):
        self.calls += 1
        if self.fail:
            raise RuntimeError("API_KEY=secret C:\\private\\draft.txt")
        return super().evaluate(request)


def test_service_invokes_evaluator_exactly_once_for_valid_request() -> None:
    evaluator = SpyEvaluator()
    request = _planning_request(CorrectiveAction.REQUEST_REGENERATION)
    result = CorrectiveActionExecutionPlanService(evaluator).plan(request)
    assert evaluator.calls == 1
    assert result.plan.decision_result is request.decision_result
    assert result.report.final_lifecycle_phase == "finalized"
    assert result.report.lifecycle_revision == 4


def test_early_and_policy_failures_invoke_evaluator_zero_times() -> None:
    evaluator = SpyEvaluator()
    invalid = CorrectiveActionExecutionPlanService(evaluator).plan(object())
    conflict = CorrectiveActionExecutionPlanService(evaluator).plan(
        _planning_request(CorrectiveAction.HALT_WORKFLOW, halt_is_non_executable=False)
    )
    assert evaluator.calls == 0
    assert invalid.plan is None and conflict.plan is None
    assert invalid.report.final_lifecycle_phase == "failed"


def test_unexpected_evaluator_failure_is_safe_and_has_no_plan() -> None:
    evaluator = SpyEvaluator(fail=True)
    result = CorrectiveActionExecutionPlanService(evaluator).plan(
        _planning_request(CorrectiveAction.REQUEST_REVISION)
    )
    assert evaluator.calls == 1
    assert result.operational_outcome is (
        CorrectiveActionExecutionPlanOutcome.FAILED_INTERNAL
    )
    assert result.plan is None
    rendered = result.model_dump_json()
    assert "secret" not in rendered and "private" not in rendered


def test_safe_result_serialization_exposes_projection_only() -> None:
    result = CorrectiveActionExecutionPlanService().plan(
        _planning_request(CorrectiveAction.CONTINUE_WORKFLOW)
    )
    serialized = serialize_execution_plan_result(result)
    assert result.result_fingerprint in serialized
    assert "integration_result" not in serialized
    assert '"decision_result":' not in serialized
    assert "finding" not in serialized


def test_tampered_policy_and_request_fingerprints_fail_closed() -> None:
    request = _planning_request(CorrectiveAction.CONTINUE_WORKFLOW)
    bad_policy = request.planning_policy.model_copy(
        update={"policy_fingerprint": "sha256:bad"}
    )
    bad_policy_request = request.model_copy(update={"planning_policy": bad_policy})
    policy_result = CorrectiveActionExecutionPlanService().plan(bad_policy_request)
    assert policy_result.plan is None
    assert policy_result.diagnostic.code is (
        CorrectiveActionExecutionPlanDiagnosticCode.POLICY_FINGERPRINT_MISMATCH
    )

    bad_request = request.model_copy(update={"request_fingerprint": "sha256:bad"})
    request_result = CorrectiveActionExecutionPlanService().plan(bad_request)
    assert request_result.plan is None
    assert request_result.diagnostic.code is (
        CorrectiveActionExecutionPlanDiagnosticCode.REQUEST_FINGERPRINT_MISMATCH
    )


def test_unknown_request_and_policy_versions_do_not_default_to_plan() -> None:
    request = _planning_request(CorrectiveAction.CONTINUE_WORKFLOW)
    unknown_request = request.model_copy(update={"contract_version": "999"})
    result = CorrectiveActionExecutionPlanService().plan(unknown_request)
    assert result.operational_outcome is (
        CorrectiveActionExecutionPlanOutcome.FAILED_UNSUPPORTED_CONTRACT
    )
    assert result.plan is None

    policy = request.planning_policy.model_copy(update={"policy_version": "999"})
    unknown_policy = request.model_copy(update={"planning_policy": policy})
    result = CorrectiveActionExecutionPlanService().plan(unknown_policy)
    assert result.operational_outcome is (
        CorrectiveActionExecutionPlanOutcome.FAILED_UNSUPPORTED_CONTRACT
    )
    assert result.plan is None


def test_state_and_event_fingerprint_tampering_is_rejected() -> None:
    state = _successful_states()[1]
    with pytest.raises(ValidationError):
        type(state).model_validate(
            {**state.model_dump(), "state_fingerprint": "sha256:bad"}
        )
    event = state.trace[0]
    with pytest.raises(ValidationError):
        type(event).model_validate(
            {**event.model_dump(), "event_fingerprint": "sha256:bad"}
        )


def test_part_two_modules_have_no_forbidden_runtime_imports() -> None:
    package = Path("src/pastila_scout/editor/qa/corrective_action/execution_plan")
    imported = set()
    for path in package.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
    forbidden = (
        "openai",
        "httpx",
        "sqlite",
        "database",
        "queue",
        "notification",
        "publication",
        "pastila_scout.cli",
        "corrective_action.service",
        "qa.integration.service",
        "reviewer",
    )
    assert all(not any(token in module for module in imported) for token in forbidden)
