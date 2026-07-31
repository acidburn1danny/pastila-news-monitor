"""M6C.5F Part 3 production composition tests."""

from test_editorial_review_integration import _generation_case

from pastila_scout.editor.qa.corrective_action import (
    CorrectiveAction,
    CorrectiveActionDecisionOutcome,
    EditorialDecisionWorkflowRequest,
    EditorialDecisionWorkflowStatus,
    build_standard_corrective_action_decision_policy,
    build_standard_editorial_decision_workflow_service,
    render_editorial_decision_workflow_report,
    serialize_editorial_decision_workflow_report,
)
from pastila_scout.editor.qa.integration import EditorialReviewIntegrationRequest


def _request(invocation):
    return EditorialDecisionWorkflowRequest.build(
        EditorialReviewIntegrationRequest(generation=invocation),
        build_standard_corrective_action_decision_policy(),
    )


def test_real_generation_review_and_decision_workflow_preserves_identity() -> None:
    generator, invocation = _generation_case()
    result = build_standard_editorial_decision_workflow_service(
        generator=generator
    ).execute(_request(invocation))

    assert result.status is EditorialDecisionWorkflowStatus.COMPLETED
    assert result.integration_result is result.decision_result.integration_result
    assert result.decision_result.decision.action is CorrectiveAction.CONTINUE_WORKFLOW
    assert result.report.requested_action == "continue_workflow"


def test_upstream_generation_failure_still_produces_completed_halt_decision() -> None:
    _, invocation = _generation_case()

    class FailingGenerator:
        calls = 0

        def generate(self, **values):
            del values
            self.calls += 1
            raise RuntimeError("private provider response")

    generator = FailingGenerator()
    result = build_standard_editorial_decision_workflow_service(
        generator=generator
    ).execute(_request(invocation))

    assert generator.calls == 1
    assert result.status is EditorialDecisionWorkflowStatus.COMPLETED
    assert result.decision_result.operational_outcome is (
        CorrectiveActionDecisionOutcome.COMPLETED
    )
    assert result.decision_result.decision.action is CorrectiveAction.HALT_WORKFLOW


def test_composition_invokes_each_dependency_once_in_order() -> None:
    generator, invocation = _generation_case()
    calls = []
    real = build_standard_editorial_decision_workflow_service(generator=generator)
    integration_service = real.integration_service
    decision_service = real.decision_service

    class IntegrationSpy:
        def execute(self, request):
            calls.append("integration")
            return integration_service.execute(request)

    class DecisionSpy:
        def decide(self, request):
            calls.append("decision")
            return decision_service.decide(request)

    real.integration_service = IntegrationSpy()
    real.decision_service = DecisionSpy()
    result = real.execute(_request(invocation))

    assert result.status is EditorialDecisionWorkflowStatus.COMPLETED
    assert calls == ["integration", "decision"]


def test_composition_is_deterministic_and_safe_to_serialize() -> None:
    first_generator, first_invocation = _generation_case()
    second_generator, second_invocation = _generation_case()
    first = build_standard_editorial_decision_workflow_service(
        generator=first_generator
    ).execute(_request(first_invocation))
    second = build_standard_editorial_decision_workflow_service(
        generator=second_generator
    ).execute(_request(second_invocation))

    assert first == second
    serialized = serialize_editorial_decision_workflow_report(first.report)
    rendered = render_editorial_decision_workflow_report(first.report)
    assert serialized == serialize_editorial_decision_workflow_report(second.report)
    assert "Fapt confirmat" not in serialized
    assert "finding" not in serialized and "provider" not in rendered


def test_integration_exception_stops_before_decision() -> None:
    _, invocation = _generation_case()

    class FailingIntegration:
        def execute(self, request):
            del request
            raise RuntimeError("secret")

    class DecisionSpy:
        calls = 0

        def decide(self, request):
            del request
            self.calls += 1

    decision = DecisionSpy()
    from pastila_scout.editor.qa.corrective_action import (
        EditorialDecisionWorkflowService,
    )

    result = EditorialDecisionWorkflowService(
        integration_service=FailingIntegration(), decision_service=decision
    ).execute(_request(invocation))

    assert result.status is EditorialDecisionWorkflowStatus.FAILED_DURING_INTEGRATION
    assert decision.calls == 0
    assert "secret" not in result.model_dump_json()
