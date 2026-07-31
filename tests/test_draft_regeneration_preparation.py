"""M6C.6C Part 2 deterministic preparation tests."""

from test_draft_regeneration_contracts import _executor_request, _input

from pastila_scout.editor.qa.corrective_action.executors.draft_regeneration import (
    DraftRegenerationInputResolver,
    DraftRegenerationPreparationOutcome,
    DraftRegenerationPreparationPhase,
    DraftRegenerationPreparationStatus,
    DraftRegenerationRequestFactory,
    build_draft_regeneration_preparation_report,
    build_standard_draft_regeneration_policy,
    serialize_draft_regeneration_preparation_report,
)


def _prepare():
    executor_request = _executor_request()
    regeneration_input = _input()
    result = DraftRegenerationRequestFactory(
        DraftRegenerationInputResolver(regeneration_input)
    ).prepare(executor_request, build_standard_draft_regeneration_policy())
    return executor_request, regeneration_input, result


def test_valid_preparation_preserves_every_authoritative_identity():
    executor_request, regeneration_input, result = _prepare()

    assert result.status is DraftRegenerationPreparationStatus.PREPARED
    assert result.operational_outcome is DraftRegenerationPreparationOutcome.COMPLETED
    assert result.executor_request is executor_request
    assert result.regeneration_request.executor_request is executor_request
    assert result.regeneration_request.regeneration_input is regeneration_input
    assert (
        result.controlled_generation_request is regeneration_input.generation_invocation
    )
    assert result.precondition_evaluation.request is result.regeneration_request
    assert result.diagnostic is None


def test_successful_lifecycle_is_canonical_and_reproducible():
    first = _prepare()[2]
    second = _prepare()[2]

    assert tuple(event.to_phase for event in first.terminal_state.events) == (
        DraftRegenerationPreparationPhase.RECEIVED,
        DraftRegenerationPreparationPhase.VALIDATING_EXECUTOR_REQUEST,
        DraftRegenerationPreparationPhase.RESOLVING_INPUT,
        DraftRegenerationPreparationPhase.BUILDING_REGENERATION_REQUEST,
        DraftRegenerationPreparationPhase.PROJECTING_GENERATION_REQUEST,
        DraftRegenerationPreparationPhase.EVALUATING_PRECONDITIONS,
        DraftRegenerationPreparationPhase.PREPARED,
    )
    assert first.result_fingerprint == second.result_fingerprint


def test_missing_authoritative_input_fails_closed_before_projection():
    request = _executor_request()
    result = DraftRegenerationRequestFactory(
        DraftRegenerationInputResolver(None)
    ).prepare(request, build_standard_draft_regeneration_policy())

    assert (
        result.operational_outcome
        is DraftRegenerationPreparationOutcome.FAILED_INPUT_RESOLUTION
    )
    assert result.status is DraftRegenerationPreparationStatus.FAILED
    assert result.regeneration_request is None
    assert result.controlled_generation_request is None
    assert result.precondition_evaluation is None
    assert result.terminal_state.phase is DraftRegenerationPreparationPhase.FAILED


def test_source_draft_is_optional_and_absence_is_deterministic():
    _, regeneration_input, result = _prepare()
    assert regeneration_input.source_draft is None
    assert result.status is DraftRegenerationPreparationStatus.PREPARED


def test_projector_and_evaluator_are_each_called_once_and_no_generation_exists():
    class ProjectorSpy:
        calls = 0

        def project(self, request):
            self.calls += 1
            return request.regeneration_input.generation_invocation

    class EvaluatorSpy:
        calls = 0

        def evaluate(self, request, generation_request):
            self.calls += 1
            from pastila_scout.editor.qa.corrective_action.executors.draft_regeneration import (
                DraftRegenerationPreconditionEvaluator,
            )

            return DraftRegenerationPreconditionEvaluator().evaluate(
                request, generation_request
            )

    projector, evaluator = ProjectorSpy(), EvaluatorSpy()
    result = DraftRegenerationRequestFactory(
        DraftRegenerationInputResolver(_input()),
        projector=projector,
        precondition_evaluator=evaluator,
    ).prepare(_executor_request(), build_standard_draft_regeneration_policy())

    assert result.status is DraftRegenerationPreparationStatus.PREPARED
    assert projector.calls == evaluator.calls == 1
    assert not hasattr(DraftRegenerationRequestFactory, "generate")
    assert not hasattr(DraftRegenerationRequestFactory, "execute")


def test_safe_report_is_deterministic_and_contains_no_editorial_content():
    result = _prepare()[2]
    report = build_draft_regeneration_preparation_report(result)
    serialized = serialize_draft_regeneration_preparation_report(report)

    assert serialized == serialize_draft_regeneration_preparation_report(report)
    for forbidden in ("draft prose", "prompt text", "provider response", "api_key"):
        assert forbidden not in serialized.casefold()
    assert report["final_phase"] == "prepared"
