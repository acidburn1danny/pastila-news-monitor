"""Focused tests for the deterministic Pastila Acida commentary blueprint."""

import json

from test_editorial_blueprint import pipeline

from pastila_scout.contracts.identity import assign_scout_input_identity
from pastila_scout.editor import CommentaryBlueprintBuilder
from pastila_scout.editor.commentary_models import (
    AudienceStrategy,
    CommentaryBeat,
    ComparisonDomain,
    HumorSensitivity,
    ProtectedTarget,
    SatireTarget,
    Sensitivity,
    Takeaway,
)


def commentary(specs, **kwargs):
    scout, selection_profile, episode_context, _, flow, generic = pipeline(
        specs, **kwargs
    )
    result = CommentaryBlueprintBuilder().build(
        scout,
        selection_profile,
        episode_context,
        flow,
        generic.blueprint,
    )
    return scout, selection_profile, episode_context, flow, generic, result


def test_political_hypocrisy_and_audience_conversation() -> None:
    *_, result = commentary(
        [{"event_id": 1, "categories": ["Politica"], "dimensions": {"absurdity": 9}}]
    )
    story = result.blueprint.stories[0]

    assert story.satire_targets[0] in {
        SatireTarget.HYPOCRISY,
        SatireTarget.PERFORMATIVE_POLITICS,
    }
    assert story.audience_strategy == AudienceStrategy.COLLECTIVE_QUESTION
    assert story.audience_voice == "audience_conversation"
    assert story.why_it_matters.primary == Takeaway.DEMOCRATIC_CONSEQUENCE


def test_economic_consequence_and_accessible_comparison() -> None:
    *_, result = commentary([{"event_id": 1, "categories": ["Economie"]}])
    story = result.blueprint.stories[0]

    assert story.why_it_matters.primary == Takeaway.ECONOMIC_CONSEQUENCE
    assert story.everyday_comparison.primary == ComparisonDomain.ANAF
    assert CommentaryBeat.EVERYDAY_COMPARISON in story.beats


def test_sensitive_tragedy_protects_victims_and_prioritizes_empathy() -> None:
    scout, selection_profile, episode_context, _, _, _ = commentary([{"event_id": 1}])
    data = scout.model_dump(mode="json", exclude={"report_id", "content_fingerprint"})
    data["ranked_events"][0]["extensions"] = {"sensitivity": "tragedy"}
    scout = assign_scout_input_identity(data)
    from pastila_scout.editor import (
        EditorialBlueprintBuilder,
        EpisodeFlowOptimizer,
        SelectionEngine,
    )

    selection = SelectionEngine().select(scout, selection_profile, episode_context)
    flow = EpisodeFlowOptimizer().optimize(
        scout, selection_profile, episode_context, selection
    )
    generic = EditorialBlueprintBuilder().build(
        scout, selection_profile, episode_context, flow
    )
    result = CommentaryBlueprintBuilder().build(
        scout, selection_profile, episode_context, flow, generic.blueprint
    )
    story = result.blueprint.stories[0]

    assert story.sensitivity == Sensitivity.TRAGEDY
    assert ProtectedTarget.VICTIMS in story.protected_targets
    assert story.empathy.humor_sensitivity == HumorSensitivity.PROHIBITED
    assert story.beats[:3] == (
        CommentaryBeat.FACTUAL_ANCHOR,
        CommentaryBeat.WHY_IT_MATTERS,
        CommentaryBeat.EMPATHY_ACKNOWLEDGMENT,
    )
    assert story.everyday_comparison.permitted is False


def test_transition_callback_evidence_and_optimized_order() -> None:
    scout, *_, result = commentary([{"event_id": 1}, {"event_id": 2}, {"event_id": 3}])

    assert result.blueprint.flow_order == result.trace.input_flow_order
    assert all(story.transition for story in result.blueprint.stories[:-1])
    assert result.blueprint.stories[-1].transition is None
    assert (
        result.blueprint.stories[-1].punchline.callback_event_id
        == result.blueprint.flow_order[0]
    )
    public = {
        (ref.source_id, ref.url, ref.title)
        for event in scout.ranked_events
        for ref in event.source_provenance
    }
    assert all(
        (ref.source_id, ref.url, ref.title) in public
        for story in result.blueprint.stories
        for ref in story.factual_summary.evidence_references
    )


def test_reproducibility_fallback_trace_and_public_output_immutability() -> None:
    *_, generic, first = commentary([{"event_id": 1}, {"event_id": 2}])
    scout, selection_profile, episode_context, flow, _, second = commentary(
        [{"event_id": 1}, {"event_id": 2}]
    )

    assert first.blueprint.model_dump(mode="json") == second.blueprint.model_dump(
        mode="json"
    )
    assert first.output.model_dump(mode="json") == generic.output.model_dump(
        mode="json"
    )
    assert first.trace.fallbacks
    assert json.dumps(first.blueprint.model_dump(mode="json"), ensure_ascii=False)
    assert scout and selection_profile and episode_context and flow


def test_backup_and_excluded_events_do_not_enter_main_commentary() -> None:
    *_, result = commentary(
        [{"event_id": 1}, {"event_id": 2}, {"event_id": 3}],
        target=2,
        backups=1,
    )
    assert len(result.blueprint.stories) == 2
    assert {story.event_id for story in result.blueprint.stories}.isdisjoint(
        {story.event_id for story in result.output.episode_proposal.backup_stories}
    )
