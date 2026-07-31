"""M6C.5F Part 1 architecture and contract tests."""

import inspect

import pytest
from pydantic import ValidationError
from test_editorial_review_integration import _generation_case

import pastila_scout.editor.qa.corrective_action as public_api
from pastila_scout.editor.qa.corrective_action import (
    CorrectiveAction,
    CorrectiveActionDecision,
    CorrectiveActionDecisionDescriptor,
    CorrectiveActionDecisionOutcome,
    CorrectiveActionDecisionPolicy,
    CorrectiveActionDecisionReason,
    CorrectiveActionDecisionRequest,
    CorrectiveActionDecisionService,
    build_standard_corrective_action_decision_policy,
    render_corrective_action_decision_report,
    serialize_corrective_action_decision_report,
)
from pastila_scout.editor.qa.integration import (
    EditorialReviewIntegrationRequest,
    IntegrationStatus,
    build_standard_editorial_review_integration_service,
)


def _failed_integration():
    _, invocation = _generation_case()

    class FailingGenerator:
        def generate(self, **values):
            del values
            raise RuntimeError("API_KEY=fake-secret C:\\private\\draft.txt")

    return build_standard_editorial_review_integration_service(
        generator=FailingGenerator()
    ).execute(EditorialReviewIntegrationRequest(generation=invocation))


def _completed_integration():
    generator, invocation = _generation_case()
    return build_standard_editorial_review_integration_service(
        generator=generator
    ).execute(EditorialReviewIntegrationRequest(generation=invocation))


def test_public_contract_inventory_and_descriptor_are_stable() -> None:
    expected = {
        "CorrectiveAction",
        "CorrectiveActionDecision",
        "CorrectiveActionDecisionPolicy",
        "CorrectiveActionDecisionRequest",
        "CorrectiveActionDecisionResult",
        "CorrectiveActionDecisionService",
    }
    assert expected <= set(public_api.__all__)
    assert CorrectiveActionDecisionDescriptor.build() == (
        CorrectiveActionDecisionDescriptor.build()
    )


def test_policy_is_immutable_deterministic_and_minimal() -> None:
    first = build_standard_corrective_action_decision_policy()
    second = build_standard_corrective_action_decision_policy()

    assert first == second
    with pytest.raises(ValidationError):
        first.rejected_action = CorrectiveAction.REQUEST_MANUAL_REVIEW
    with pytest.raises(ValidationError):
        CorrectiveActionDecisionPolicy.build(
            rejected_action=CorrectiveAction.CONTINUE_WORKFLOW
        )
    with pytest.raises(ValidationError):
        CorrectiveActionDecisionPolicy.build(
            review_disabled_action=CorrectiveAction.REQUEST_REGENERATION
        )


def test_policy_and_request_corruption_are_rejected() -> None:
    integration = _failed_integration()
    policy = build_standard_corrective_action_decision_policy()
    with pytest.raises(ValidationError):
        CorrectiveActionDecisionPolicy.model_validate(
            {**policy.model_dump(), "policy_fingerprint": "sha256:bad"}
        )
    request = CorrectiveActionDecisionRequest.build(integration, policy)
    with pytest.raises(ValidationError):
        CorrectiveActionDecisionRequest.model_validate(
            {**request.model_dump(), "request_fingerprint": "sha256:bad"}
        )


def test_request_is_immutable_and_binds_only_authoritative_identities() -> None:
    integration = _failed_integration()
    policy = build_standard_corrective_action_decision_policy()
    first = CorrectiveActionDecisionRequest.build(integration, policy)
    second = CorrectiveActionDecisionRequest.build(integration, policy)

    assert first == second
    assert first.integration_result is integration
    with pytest.raises(ValidationError):
        first.contract_version = "2"
    assert "Fapt confirmat" not in first.request_fingerprint


@pytest.mark.parametrize(
    ("action", "reason"),
    (
        (
            CorrectiveAction.REQUEST_REGENERATION,
            CorrectiveActionDecisionReason.EDITORIAL_REGENERATION_REQUIRED,
        ),
        (
            CorrectiveAction.HALT_WORKFLOW,
            CorrectiveActionDecisionReason.EDITORIAL_REJECTED,
        ),
    ),
)
def test_decision_action_and_reason_are_separate(action, reason) -> None:
    integration = _failed_integration()
    policy = build_standard_corrective_action_decision_policy()
    decision = CorrectiveActionDecision.build(
        action=action,
        reason=reason,
        source_integration_fingerprint=integration.result_fingerprint,
        source_editorial_status=None,
        policy_fingerprint=policy.policy_fingerprint,
        policy_applied=reason is CorrectiveActionDecisionReason.EDITORIAL_REJECTED,
        decision_rule_id="test.contract",
    )

    assert decision.action is action and decision.reason is reason
    assert decision.decision_fingerprint.startswith("sha256:")


def test_upstream_failure_is_a_successful_halt_decision() -> None:
    integration = _failed_integration()
    request = CorrectiveActionDecisionRequest.build(
        integration, build_standard_corrective_action_decision_policy()
    )
    result = CorrectiveActionDecisionService().decide(request)

    assert integration.status is IntegrationStatus.FAILED_DURING_GENERATION
    assert result.operational_outcome is CorrectiveActionDecisionOutcome.COMPLETED
    assert result.decision.action is CorrectiveAction.HALT_WORKFLOW
    assert result.decision.reason is (
        CorrectiveActionDecisionReason.UPSTREAM_GENERATION_FAILED
    )
    assert result.integration_result is integration
    assert result.result_fingerprint.startswith("sha256:")


def test_invalid_decision_input_fails_without_fabricating_action() -> None:
    first = CorrectiveActionDecisionService().decide(object())
    second = CorrectiveActionDecisionService().decide(object())

    assert first == second
    assert first.operational_outcome is (
        CorrectiveActionDecisionOutcome.FAILED_INVALID_INPUT
    )
    assert first.decision is None and first.report.requested_action is None


def test_completed_state_is_mapped_by_authoritative_evaluator() -> None:
    integration = _completed_integration()
    request = CorrectiveActionDecisionRequest.build(
        integration, build_standard_corrective_action_decision_policy()
    )
    result = CorrectiveActionDecisionService().decide(request)

    assert integration.status is IntegrationStatus.COMPLETED
    assert result.operational_outcome is CorrectiveActionDecisionOutcome.COMPLETED
    assert result.decision.action is CorrectiveAction.CONTINUE_WORKFLOW
    assert not result.decision.policy_applied


def test_trace_reporting_and_serialization_are_deterministic_and_safe() -> None:
    integration = _failed_integration()
    request = CorrectiveActionDecisionRequest.build(
        integration, build_standard_corrective_action_decision_policy()
    )
    first = CorrectiveActionDecisionService().decide(request)
    second = CorrectiveActionDecisionService().decide(request)
    serialized = serialize_corrective_action_decision_report(first.report)
    rendered = render_corrective_action_decision_report(first.report)

    assert first == second
    assert tuple(item.sequence for item in first.trace) == tuple(
        range(len(first.trace))
    )
    assert serialized == serialize_corrective_action_decision_report(second.report)
    forbidden = (
        "fake-secret",
        "private",
        "draft.txt",
        "finding",
        "evidence",
        "prompt",
        "provider_response",
    )
    assert all(value not in serialized for value in forbidden)
    assert all(value not in rendered for value in forbidden)


def test_action_enums_do_not_conflate_execution_or_publication() -> None:
    values = tuple(item.value for item in CorrectiveAction)
    assert len(values) == len(set(values))
    assert "decision_failed" not in values and "workflow_failed" not in values
    assert not any("publish" in value for value in values)
    assert CorrectiveAction.CONTINUE_WORKFLOW.value == "continue_workflow"


def test_runtime_import_boundary_has_no_finding_or_upstream_service_access() -> None:
    source = "\n".join(
        inspect.getsource(module)
        for module in (
            public_api,
            __import__(
                "pastila_scout.editor.qa.corrective_action.service", fromlist=["x"]
            ),
        )
    )
    forbidden = (
        "EditorialFinding",
        "DeterministicRulesReviewer",
        "DeterministicReviewerPipeline",
        "EditorialReviewIntegrationService",
        "ControlledGenerator",
        "ApprovalPolicyEngine",
    )
    assert all(name not in source for name in forbidden)
