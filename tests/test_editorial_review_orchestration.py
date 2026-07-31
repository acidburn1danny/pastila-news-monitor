"""End-to-end M6C.5D orchestration tests."""

from pastila_scout.editor.generation import DraftAssembler
from pastila_scout.editor.generation.models import CommentaryBlockResult, DraftStory
from pastila_scout.editor.qa.models import ApprovalStatus
from pastila_scout.editor.qa.orchestration import (
    EditorialReviewOrchestrationPolicy,
    EditorialReviewOrchestrationRequest,
    OrchestrationStatus,
    build_standard_editorial_review_orchestrator,
    render_orchestration_report,
    review_episode_draft,
)


def _draft(text="Comentariu normal."):
    story = DraftStory(
        story_id=7,
        factual_summary="Fapt confirmat.",
        commentary_blocks=(
            CommentaryBlockResult(
                block_type="commentary",
                text=text,
                sequence=1,
                source_fact_ids=("f1",),
                blueprint_intent_ids=("i1",),
                voice_plan_ids=("v1",),
                satire_target_ids=(),
                protected_target_ids=(),
            ),
        ),
        ending="Final.",
    )
    return DraftAssembler().assemble(
        episode_id="episod-1",
        story_order=(7,),
        opening="Deschidere.",
        stories=(story,),
        transitions=(),
        closing="Închidere.",
        cta=None,
    )


def test_standard_orchestration_is_deterministic_and_lossless():
    request = EditorialReviewOrchestrationRequest(draft=_draft())
    orchestrator = build_standard_editorial_review_orchestrator()
    first = orchestrator.review(request)
    second = orchestrator.review(request)
    assert first == second
    assert first.status is OrchestrationStatus.COMPLETED
    assert first.pipeline_result.accepted_review_results == (
        first.editorial_result.report.review_results
    )
    assert first.report.handoff_performed
    summary = render_orchestration_report(first.report)
    assert "Status: completed" in summary and "Fapt confirmat" not in summary


def test_blocking_editorial_finding_does_not_become_operational_failure():
    result = review_episode_draft(_draft("TODO"))
    assert result.status is OrchestrationStatus.COMPLETED
    assert result.pipeline_result.status.value == "completed"
    assert (
        result.editorial_result.decision.status is ApprovalStatus.REQUIRES_REGENERATION
    )
    assert any(
        item.issue_code == "language.placeholder-detected"
        for item in result.editorial_result.report.findings
    )


def test_explicit_manifest_precedence_preserves_manifest_identity():
    orchestrator = build_standard_editorial_review_orchestrator()
    standard = orchestrator.manifest_provider.resolve(
        _draft(), EditorialReviewOrchestrationPolicy()
    )
    result = orchestrator.review(
        EditorialReviewOrchestrationRequest(draft=_draft(), manifest=standard)
    )
    assert result.manifest_fingerprint == standard.manifest_fingerprint


def test_pipeline_failure_is_sanitized_without_fabricated_editorial_result():
    class FailingPipeline:
        def execute(self, request):
            del request
            raise RuntimeError("SECRET failure")

    orchestrator = build_standard_editorial_review_orchestrator(
        pipeline=FailingPipeline()
    )
    result = orchestrator.review(EditorialReviewOrchestrationRequest(draft=_draft()))
    assert result.status is OrchestrationStatus.FAILED_BEFORE_PIPELINE
    assert result.pipeline_result is None and result.editorial_result is None
    assert "SECRET" not in result.model_dump_json()
    assert result.diagnostics[0].code == "PIPELINE_INVOCATION_FAILED"


def test_request_and_result_are_immutable_and_convenience_path_matches():
    request = EditorialReviewOrchestrationRequest(draft=_draft())
    direct = build_standard_editorial_review_orchestrator().review(request)
    convenient = review_episode_draft(_draft())
    assert direct.result_fingerprint == convenient.result_fingerprint
