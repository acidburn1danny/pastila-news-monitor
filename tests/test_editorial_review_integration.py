"""End-to-end M6C.5E generation-to-review integration tests."""

import pytest
from pydantic import ValidationError
from test_controlled_generation import (
    authored_story_result,
    config,
    context_from_pipeline,
    profile_from_pipeline,
)
from test_voice_model import voice_pipeline

from pastila_scout.editor.generation import (
    ControlledGenerator,
    ScriptedLanguageModelProvider,
)
from pastila_scout.editor.qa.integration import (
    ControlledGenerationInvocation,
    EditorialReviewIntegrationPolicy,
    EditorialReviewIntegrationRequest,
    IntegrationStatus,
    build_standard_editorial_review_integration_service,
    generate_and_review_episode,
    render_integration_report,
    serialize_integration_report,
)
from pastila_scout.editor.qa.orchestration import (
    build_standard_editorial_review_orchestrator,
)


def _generation_case(*, story_text: str | None = None):
    scout, flow, generic, commentary, voice = voice_pipeline([{"event_id": 7}])
    story_id = commentary.blueprint.flow_order[0]
    # The provider boundary accepts only authored content. Application-owned
    # story and blueprint identities are deterministically rebound after parse.
    story = authored_story_result(story_id, 1)
    if story_text is not None:
        story["commentary_blocks"][0]["text"] = story_text
    responses = [
        story,
        {
            "text": "Deschidere controlată.",
            "referenced_story_ids": [story_id],
            "opening_mechanism": "fact_first",
            "declared_plan_references": ["opening"],
        },
        {
            "text": "Închidere controlată.",
            "closing_mechanism": "reflection",
            "declared_plan_references": ["closing"],
        },
    ]
    invocation = ControlledGenerationInvocation(
        scout_input=scout,
        selection_profile=profile_from_pipeline(scout),
        episode_context=context_from_pipeline(scout),
        flow_result=flow,
        editorial_blueprint=generic.blueprint,
        commentary_blueprint=commentary.blueprint,
        voice_plan=voice.plan,
    )
    return (
        ControlledGenerator(ScriptedLanguageModelProvider(responses), config=config()),
        invocation,
    )


def test_standard_flow_uses_real_generator_and_real_review_pipeline() -> None:
    generator, invocation = _generation_case()
    result = build_standard_editorial_review_integration_service(
        generator=generator
    ).execute(EditorialReviewIntegrationRequest(generation=invocation))

    assert result.status is IntegrationStatus.COMPLETED
    assert result.generation_result is not None
    assert result.review_result is not None
    assert result.review_result.pipeline_result is not None
    assert result.review_result.editorial_result is not None
    assert result.draft_fingerprint == result.review_result.draft_fingerprint
    assert result.report.completeness.review_invoked
    assert result.report.completeness.review_completed


def test_editorial_regeneration_requirement_is_not_integration_failure() -> None:
    generator, invocation = _generation_case(story_text="TODO")
    result = build_standard_editorial_review_integration_service(
        generator=generator
    ).execute(EditorialReviewIntegrationRequest(generation=invocation))

    assert result.status is IntegrationStatus.COMPLETED
    assert result.review_result is not None
    assert result.review_result.editorial_result is not None
    assert result.review_result.editorial_result.decision.status.value == (
        "requires_regeneration"
    )


def test_generation_failure_is_sanitized_and_never_invokes_review() -> None:
    _, invocation = _generation_case()

    class FailingGenerator:
        def generate(self, **values):
            del values
            raise RuntimeError("SECRET provider failure")

    class ReviewSpy:
        calls = 0

        def review(self, request):
            del request
            self.calls += 1

    reviewer = ReviewSpy()
    result = build_standard_editorial_review_integration_service(
        generator=FailingGenerator(), review_orchestrator=reviewer
    ).execute(EditorialReviewIntegrationRequest(generation=invocation))

    assert result.status is IntegrationStatus.FAILED_DURING_GENERATION
    assert reviewer.calls == 0
    assert result.generation_result is None and result.review_result is None
    assert "SECRET" not in result.model_dump_json()
    assert result.diagnostics[0].code == "GENERATION_INVOCATION_FAILED"


def test_review_failure_preserves_generation_and_records_invocation() -> None:
    generator, invocation = _generation_case()

    class FailingReview:
        def review(self, request):
            del request
            raise RuntimeError("SECRET review failure")

    result = build_standard_editorial_review_integration_service(
        generator=generator, review_orchestrator=FailingReview()
    ).execute(EditorialReviewIntegrationRequest(generation=invocation))

    assert result.status is IntegrationStatus.FAILED_DURING_REVIEW
    assert result.generation_result is not None and result.review_result is None
    assert result.report.completeness.review_invoked
    assert not result.report.completeness.review_completed
    assert "SECRET" not in result.model_dump_json()


def test_review_can_be_explicitly_disabled_without_losing_generation() -> None:
    generator, invocation = _generation_case()
    result = build_standard_editorial_review_integration_service(
        generator=generator
    ).execute(
        EditorialReviewIntegrationRequest(
            generation=invocation,
            integration_policy=EditorialReviewIntegrationPolicy(
                require_review_after_generation=False
            ),
        )
    )

    assert result.status is IntegrationStatus.COMPLETED_WITHOUT_REVIEW
    assert result.generation_result is not None and result.review_result is None
    assert result.report.completeness.limited_completion


def test_equivalent_runs_are_deterministic_and_convenience_delegates() -> None:
    first_generator, first_invocation = _generation_case()
    second_generator, second_invocation = _generation_case()
    first = build_standard_editorial_review_integration_service(
        generator=first_generator
    ).execute(EditorialReviewIntegrationRequest(generation=first_invocation))
    second = generate_and_review_episode(
        generator=second_generator, generation=second_invocation
    )

    assert first == second
    assert first.result_fingerprint == second.result_fingerprint
    assert "Status: completed" in render_integration_report(first.report)
    assert "Fapt confirmat" not in render_integration_report(first.report)


def test_generation_invocation_preserves_typed_public_inputs() -> None:
    _, invocation = _generation_case()
    arguments = invocation.keyword_arguments()

    assert arguments["scout_input"] is invocation.scout_input
    assert arguments["flow_result"] is invocation.flow_result
    assert arguments["voice_plan"] is invocation.voice_plan
    assert "static_cta_content" not in invocation.model_dump(mode="python")


def test_invalid_generation_result_is_rejected_before_review() -> None:
    _, invocation = _generation_case()

    class InvalidGenerator:
        def generate(self, **values):
            del values
            return object()

    result = build_standard_editorial_review_integration_service(
        generator=InvalidGenerator(),
        review_orchestrator=build_standard_editorial_review_orchestrator(),
    ).execute(EditorialReviewIntegrationRequest(generation=invocation))

    assert result.status is IntegrationStatus.FAILED_DURING_GENERATION
    assert result.review_result is None
    assert result.diagnostics[0].code == "GENERATION_RESULT_INVALID"


def test_request_is_frozen_and_rejects_duplicate_execution_ids() -> None:
    _, invocation = _generation_case()
    request = EditorialReviewIntegrationRequest(generation=invocation)

    with pytest.raises(ValidationError):
        request.requested_execution_ids = ("x",)
    with pytest.raises(ValidationError):
        EditorialReviewIntegrationRequest(
            generation=invocation, requested_execution_ids=("x", "x")
        )


def test_safe_serialization_is_deterministic_unicode_safe_and_content_free() -> None:
    generator, invocation = _generation_case(story_text="Conținut secret românesc")
    result = build_standard_editorial_review_integration_service(
        generator=generator
    ).execute(EditorialReviewIntegrationRequest(generation=invocation))

    first = serialize_integration_report(result.report)
    assert first == serialize_integration_report(result.report)
    assert "Conținut secret românesc" not in first
    assert "factual_summary" not in first and "findings" not in first


def test_review_request_values_pass_unchanged_to_m6c5d() -> None:
    generator, invocation = _generation_case()
    standard = build_standard_editorial_review_orchestrator()
    generation_result = generator.generate(**invocation.keyword_arguments())
    manifest = standard.manifest_provider.resolve(
        generation_result.draft,
        EditorialReviewIntegrationRequest(generation=invocation).orchestration_policy,
    )
    requested_id = manifest.items[0].manifest_item_id

    class StaticGenerator:
        def generate(self, **values):
            del values
            return generation_result

    class CapturingOrchestrator:
        request = None

        def review(self, request):
            self.request = request
            return standard.review(request)

    capturing = CapturingOrchestrator()
    request = EditorialReviewIntegrationRequest(
        generation=invocation,
        review_manifest=manifest,
        requested_execution_ids=(requested_id,),
    )
    result = build_standard_editorial_review_integration_service(
        generator=StaticGenerator(), review_orchestrator=capturing
    ).execute(request)

    assert result.review_result is not None
    assert capturing.request.manifest is manifest
    assert capturing.request.requested_execution_ids == request.requested_execution_ids
    assert capturing.request.pipeline_policy is request.pipeline_policy
    assert capturing.request.orchestration_policy is request.orchestration_policy
    assert capturing.request.approval_policy is request.approval_policy


def test_valid_m6c5d_operational_failure_is_preserved_without_editorial_outcome() -> (
    None
):
    generator, invocation = _generation_case()

    class FailingPipeline:
        def execute(self, request):
            del request
            raise RuntimeError("nested secret")

    orchestrator = build_standard_editorial_review_orchestrator(
        pipeline=FailingPipeline()
    )
    result = build_standard_editorial_review_integration_service(
        generator=generator, review_orchestrator=orchestrator
    ).execute(EditorialReviewIntegrationRequest(generation=invocation))

    assert result.status is IntegrationStatus.FAILED_DURING_REVIEW
    assert result.review_result is not None
    assert result.review_result.status.value == "failed_before_pipeline"
    assert result.review_result.editorial_result is None
    assert result.report.editorial_status is None
    assert "nested secret" not in result.model_dump_json()
