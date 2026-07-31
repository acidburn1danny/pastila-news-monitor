"""Focused offline tests for M6C.5C reviewer-pipeline behavior."""

from pastila_scout.editor.generation import DraftAssembler
from pastila_scout.editor.generation.models import CommentaryBlockResult, DraftStory
from pastila_scout.editor.qa import (
    NoOpEditorialReviewer,
    ReviewerCapabilities,
    ReviewerCapability,
    ScriptedEditorialReviewer,
)
from pastila_scout.editor.qa.manifest import EditorialReviewManifest, ReviewerPlan
from pastila_scout.editor.qa.models import fingerprint
from pastila_scout.editor.qa.pipeline import (
    DeterministicReviewerPipeline,
    ReviewerRegistry,
    build_execution_report,
    build_m6c5a_execution_state,
    render_execution_report,
)
from pastila_scout.editor.qa.pipeline.models import (
    ReviewerExecutionStatus,
    ReviewerPipelinePolicy,
    ReviewerPipelineRequest,
    ReviewerPipelineStatus,
)
from pastila_scout.editor.qa.rules import (
    DeterministicEditorialRulePolicy,
    DeterministicRulesReviewer,
)

CAPABILITIES = ReviewerCapabilities(values=(ReviewerCapability.STRUCTURE,))


def _draft():
    story = DraftStory(
        story_id=1,
        factual_summary="Fapt confirmat.",
        commentary_blocks=(
            CommentaryBlockResult(
                block_type="commentary",
                text="Comentariu.",
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
        episode_id="e1",
        story_order=(1,),
        opening="Deschidere.",
        stories=(story,),
        transitions=(),
        closing="Închidere.",
        cta=None,
    )


def _manifest(ids=("a", "b")):
    return EditorialReviewManifest.build(
        tuple(
            ReviewerPlan(
                reviewer_id=item,
                reviewer_version="1",
                capabilities=CAPABILITIES,
                target_component_ids=("opening",),
                required=True,
            )
            for item in ids
        )
    )


def _dependent_manifest():
    manifest = _manifest()
    review_items = [item for item in manifest.items if item.operation == "review"]
    first, second = review_items
    second = second.model_copy(update={"dependencies": (first.manifest_item_id,)})
    other = [item for item in manifest.items if item.operation != "review"]
    items = (first, second, *other)
    return EditorialReviewManifest(
        items=items,
        manifest_fingerprint=fingerprint(
            tuple(item.model_dump(mode="python") for item in items)
        ),
    )


def _reviewer(name, responses=None):
    if responses is None:
        return NoOpEditorialReviewer(name, "1", CAPABILITIES)
    return ScriptedEditorialReviewer(
        name, responses, reviewer_version="1", capabilities=CAPABILITIES
    )


def test_independent_execution_is_deterministic_and_report_is_operational():
    registry = ReviewerRegistry.build((_reviewer("b"), _reviewer("a")))
    request = ReviewerPipelineRequest(
        episode_draft=_draft(), review_manifest=_manifest()
    )
    first = DeterministicReviewerPipeline(registry).execute(request)
    second = DeterministicReviewerPipeline(registry).execute(request)
    assert first == second
    assert first.status is ReviewerPipelineStatus.COMPLETED
    assert tuple(item.reviewer_id for item in first.execution_outcomes) == ("a", "b")
    text = render_execution_report(build_execution_report(first))
    assert "Status: completed" in text and "Deschidere" not in text


def test_failed_dependency_is_skipped_and_independent_failure_is_sanitized():
    failing = _reviewer("a", (RuntimeError("SECRET exception"),))
    dependent = _reviewer("b")
    result = DeterministicReviewerPipeline(
        ReviewerRegistry.build((failing, dependent))
    ).execute(
        ReviewerPipelineRequest(
            episode_draft=_draft(), review_manifest=_dependent_manifest()
        )
    )
    assert tuple(item.status for item in result.execution_outcomes) == (
        ReviewerExecutionStatus.FAILED,
        ReviewerExecutionStatus.SKIPPED,
    )
    assert result.execution_outcomes[1].skip_code == "DEPENDENCY_UNSATISFIED"
    assert "SECRET" not in result.model_dump_json()
    assert result.status is ReviewerPipelineStatus.FAILED
    assert dependent.calls == []


def test_fail_fast_skips_remaining_reviewers():
    failing = _reviewer("a", (RuntimeError("boom"),))
    untouched = _reviewer("b")
    request = ReviewerPipelineRequest(
        episode_draft=_draft(),
        review_manifest=_manifest(),
        pipeline_policy=ReviewerPipelinePolicy(continue_after_required_failure=False),
    )
    result = DeterministicReviewerPipeline(
        ReviewerRegistry.build((failing, untouched))
    ).execute(request)
    assert result.execution_outcomes[1].skip_code == "PIPELINE_HALTED_BY_POLICY"
    assert untouched.calls == []


def test_partial_selection_is_canonical_and_includes_dependency_closure():
    pipeline = DeterministicReviewerPipeline(
        ReviewerRegistry.build((_reviewer("a"), _reviewer("b")))
    )
    base = ReviewerPipelineRequest(
        episode_draft=_draft(), review_manifest=_dependent_manifest()
    )
    plan, _, _ = pipeline.prepare(base)
    target = plan.execution_units[1].execution_id
    request = base.model_copy(update={"requested_execution_ids": (target,)})
    result = pipeline.execute(request)
    assert len(result.coverage.selected_execution_ids) == 2
    assert result.coverage.dependency_execution_ids == (
        plan.execution_units[0].execution_id,
    )


def test_registry_input_order_does_not_change_identity():
    first = ReviewerRegistry.build((_reviewer("a"), _reviewer("b")))
    second = ReviewerRegistry.build((_reviewer("b"), _reviewer("a")))
    assert first.registry_fingerprint == second.registry_fingerprint


def test_m6c5b_reviewer_findings_are_preserved_without_aggregation():
    reviewer = DeterministicRulesReviewer()
    manifest = EditorialReviewManifest.build(
        (
            ReviewerPlan(
                reviewer_id=reviewer.reviewer_id,
                reviewer_version=reviewer.reviewer_version,
                capabilities=reviewer.capabilities,
                target_component_ids=("opening", "story-01", "closing", "teleprompter"),
                required=True,
            ),
        )
    )
    pipeline = DeterministicReviewerPipeline(ReviewerRegistry.build((reviewer,)))
    request = ReviewerPipelineRequest(episode_draft=_draft(), review_manifest=manifest)
    plan, _, _ = pipeline.prepare(request)
    result = pipeline.execute(request)
    assert result.status is ReviewerPipelineStatus.COMPLETED
    assert result.accepted_review_results == (
        result.execution_outcomes[0].review_result,
    )
    handoff = build_m6c5a_execution_state(result, plan)
    assert handoff.review_results == result.accepted_review_results


def test_pipeline_accepts_transition_finding_as_operational_completion():
    reviewer = DeterministicRulesReviewer(
        DeterministicEditorialRulePolicy(transition_max_words=1)
    )
    manifest = EditorialReviewManifest.build(
        (
            ReviewerPlan(
                reviewer_id=reviewer.reviewer_id,
                reviewer_version=reviewer.reviewer_version,
                capabilities=reviewer.capabilities,
                target_component_ids=("transition-01-02",),
                required=True,
            ),
        )
    )
    request = ReviewerPipelineRequest(
        episode_draft=_two_story_draft(), review_manifest=manifest
    )
    result = DeterministicReviewerPipeline(ReviewerRegistry.build((reviewer,))).execute(
        request
    )
    outcome = result.execution_outcomes[0]
    assert outcome.status is ReviewerExecutionStatus.COMPLETED
    assert outcome.failure_code is None
    finding = next(
        item
        for item in outcome.review_result.findings
        if item.issue_code == "runtime.transition-too-long"
    )
    assert finding.location.component_id == "transition-01-02"
    assert finding.location.transition_from_story_position == 1
    assert finding.location.transition_to_story_position == 2


def _two_story_draft():
    from pastila_scout.editor.generation.models import DraftTransition

    base = _draft()
    second = base.stories[0].model_copy(update={"story_id": 2})
    return DraftAssembler().assemble(
        episode_id="two-story",
        story_order=(1, 2),
        opening=base.opening,
        stories=(base.stories[0], second),
        transitions=(
            DraftTransition(from_story_id=1, to_story_id=2, text="Mai departe."),
        ),
        closing=base.closing,
        cta=None,
    )


def test_pipeline_accepts_multiple_repaired_mechanical_findings_without_aggregation():
    base = _draft()
    block = (
        base.stories[0]
        .commentary_blocks[0]
        .model_copy(update={"text": "TODO  Ce urmează!!!!"})
    )
    story = base.stories[0].model_copy(update={"commentary_blocks": (block,)})
    draft = DraftAssembler().assemble(
        episode_id="mechanical-findings",
        story_order=(1,),
        opening=base.opening,
        stories=(story,),
        transitions=(),
        closing=base.closing,
        cta=None,
    )
    reviewer = DeterministicRulesReviewer()
    manifest = EditorialReviewManifest.build(
        (
            ReviewerPlan(
                reviewer_id=reviewer.reviewer_id,
                reviewer_version=reviewer.reviewer_version,
                capabilities=reviewer.capabilities,
                target_component_ids=("story-01",),
                required=True,
            ),
        )
    )
    request = ReviewerPipelineRequest(episode_draft=draft, review_manifest=manifest)
    pipeline = DeterministicReviewerPipeline(ReviewerRegistry.build((reviewer,)))
    first = pipeline.execute(request)
    second = pipeline.execute(request)
    outcome = first.execution_outcomes[0]
    assert outcome.status is ReviewerExecutionStatus.COMPLETED
    assert outcome.failure_code is None
    codes = tuple(item.issue_code for item in outcome.review_result.findings)
    assert "language.placeholder-detected" in codes
    assert "language.excessive-consecutive-punctuation" in codes
    assert "language.repeated-inline-whitespace" in codes
    assert len(codes) == len(
        {item.finding_id for item in outcome.review_result.findings}
    )
    assert first.result_fingerprint == second.result_fingerprint
