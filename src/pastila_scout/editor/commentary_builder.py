"""Deterministic Pastila Acida commentary blueprint construction."""

from collections import defaultdict

from pastila_scout.contracts.editor_output import validate_editor_output_against_input
from pastila_scout.editor.blueprint_models import SafeFactField
from pastila_scout.editor.commentary_models import (
    CommentaryBlueprintTrace,
    CommentaryBuildResult,
    CommentaryDecision,
    CommentaryTransitionPlan,
    EpisodeCommentaryBlueprint,
    EverydayComparisonPlan,
    FactualSummaryPlan,
    ProhibitedJokeDirection,
    PunchlinePlan,
    RepeatedComparisonWarning,
    StoryCommentaryBlueprint,
    WhyItMattersPlan,
)
from pastila_scout.editor.commentary_rules import (
    AudienceConversationRule,
    CommentaryBeatRule,
    EmpathyRule,
    EpisodeConsistencyRule,
    EverydayComparisonRule,
    IronyMechanismRule,
    ProtectedTargetRule,
    PunchlinePlanRule,
    SatireTargetRule,
    SensitivityRule,
    WhyItMattersRule,
)
from pastila_scout.editor.commentary_validation import validate_commentary_blueprint


class CommentaryBlueprintBuilder:
    """Build private controlled commentary plans without generating language."""

    def __init__(self) -> None:
        self.sensitivity_rule = SensitivityRule()
        self.satire_rule = SatireTargetRule()
        self.protected_rule = ProtectedTargetRule()
        self.irony_rule = IronyMechanismRule()
        self.audience_rule = AudienceConversationRule()
        self.why_rule = WhyItMattersRule()
        self.comparison_rule = EverydayComparisonRule()
        self.empathy_rule = EmpathyRule()
        self.beat_rule = CommentaryBeatRule()
        self.punchline_rule = PunchlinePlanRule()
        self.consistency_rule = EpisodeConsistencyRule()

    def build(self, scout_input, profile, context, flow_result, editorial_blueprint):
        """Return unchanged public output, a private blueprint, and its trace."""
        output = flow_result.output
        validate_editor_output_against_input(
            output, scout_input, selection_profile=profile, episode_context=context
        )
        proposal = output.episode_proposal
        if proposal is None:
            raise ValueError("commentary blueprint requires an episode proposal")
        order = tuple(step.event_id for step in proposal.episode_flow)
        if order != editorial_blueprint.flow_order:
            raise ValueError("generic blueprint and optimized flow orders differ")
        event_map = {event.event_id: event for event in scout_input.ranked_events}
        segment_map = {
            segment.event_id: segment for segment in editorial_blueprint.segments
        }
        transition_map = {
            item.from_event_id: item for item in editorial_blueprint.transitions
        }
        decisions = []
        fallbacks = []
        stories = []
        for index, event_id in enumerate(order):
            event = event_map[event_id]
            segment = segment_map[event_id]
            sensitivity, fallback = self.sensitivity_rule.assign(event)
            if fallback:
                fallbacks.append(
                    _decision(
                        "SensitivityRule",
                        event_id,
                        "safest_explicit_metadata_fallback",
                        (sensitivity.value,),
                    )
                )
            targets = self.satire_rule.assign(event, segment.angles)
            protected = self.protected_rule.assign(event, sensitivity)
            primary, secondary = self.why_rule.assign(event)
            comparison, comparison_secondary, relationship, permitted = (
                self.comparison_rule.assign(event, sensitivity)
            )
            emotion, second_emotion, acknowledge, humor = self.empathy_rule.assign(
                protected, sensitivity, event
            )
            callback = order[0] if index == len(order) - 1 and len(order) > 2 else None
            punch_function, contradiction = self.punchline_rule.assign(
                targets[0], sensitivity, callback
            )
            transition = None
            if index + 1 < len(order):
                public_step = proposal.episode_flow[index + 1]
                generic_transition = transition_map[event_id]
                transition = CommentaryTransitionPlan(
                    next_event_id=order[index + 1],
                    expected_transition_type=public_step.expected_transition_type,
                    current_anchor=SafeFactField.CANONICAL_TITLE,
                    next_anchor=SafeFactField.CANONICAL_TITLE,
                    transition_intent=generic_transition.intent.value,
                    callback_event_id=(
                        order[0]
                        if generic_transition.intent.value == "callback_to_previous"
                        else None
                    ),
                    prohibited_repetition=(
                        "repeat_same_claim",
                        "repeat_same_comparison",
                        "reexplain_context",
                    ),
                )
            actors = (
                event.extensions.get("principal_actors", ()) if event.extensions else ()
            )
            if not isinstance(actors, (list, tuple)):
                actors = ()
            story = StoryCommentaryBlueprint(
                position=index + 1,
                event_id=event_id,
                sensitivity=sensitivity,
                factual_summary=FactualSummaryPlan(
                    mandatory_factual_points=(
                        SafeFactField.CANONICAL_TITLE,
                        SafeFactField.CANONICAL_SUMMARY,
                        SafeFactField.PUBLICATION_BOUNDS,
                    ),
                    principal_actors=tuple(str(item) for item in actors),
                    principal_actors_available=bool(actors),
                    central_event_id=event_id,
                    central_event_field=SafeFactField.CANONICAL_TITLE,
                    public_consequence=primary,
                    relevance=primary,
                    evidence_references=segment.evidence.provenance,
                    prohibited_unsupported_claims=(
                        "unsupported_causality",
                        "unverified_motive",
                        "invented_quote",
                        "source_conflation",
                    ),
                    target_sentence_count=2 if event.article_count > 1 else 1,
                ),
                satire_targets=targets,
                protected_targets=protected,
                irony_mechanisms=self.irony_rule.assign(targets, sensitivity),
                audience_strategy=self.audience_rule.assign(event),
                audience_voice="audience_conversation",
                why_it_matters=WhyItMattersPlan(primary=primary, secondary=secondary),
                everyday_comparison=EverydayComparisonPlan(
                    primary=comparison,
                    secondary=comparison_secondary,
                    relationship=relationship,
                    permitted=permitted,
                ),
                empathy={
                    "affected_people": protected,
                    "primary_emotion": emotion,
                    "secondary_emotion": second_emotion,
                    "explicit_acknowledgment_required": acknowledge,
                    "humor_sensitivity": humor,
                },
                beats=self.beat_rule.assign(
                    sensitivity, comparison, acknowledge, transition is not None
                ),
                punchline=PunchlinePlan(
                    function=punch_function,
                    target=targets[0],
                    core_contradiction=contradiction,
                    callback_event_id=callback,
                    intended_emotional_effect=emotion,
                    intended_memory_effect="retain_core_contradiction",
                    prohibited_directions=tuple(ProhibitedJokeDirection),
                ),
                transition=transition,
            )
            stories.append(story)
            for rule, values in (
                ("SatireTargetRule", tuple(x.value for x in targets)),
                ("WhyItMattersRule", (primary.value,)),
                ("CommentaryBeatRule", tuple(x.value for x in story.beats)),
            ):
                decisions.append(
                    _decision(rule, event_id, "controlled_value_assigned", values)
                )
        comparisons = defaultdict(list)
        for story in stories:
            if story.everyday_comparison.primary:
                comparisons[story.everyday_comparison.primary].append(story.event_id)
        repeated = tuple(
            RepeatedComparisonWarning(domain=domain, event_ids=tuple(ids))
            for domain, ids in sorted(
                comparisons.items(), key=lambda item: item[0].value
            )
            if len(ids) > 1
        )
        targets = [target for story in stories for target in story.satire_targets]
        emotions = [story.empathy.primary_emotion for story in stories]
        sensitive_count = sum(
            story.sensitivity.value not in ("ordinary", "elevated") for story in stories
        )
        blueprint = EpisodeCommentaryBlueprint(
            source_report_id=scout_input.report_id,
            flow_order=order,
            stories=tuple(stories),
            dominant_satire_target=self.consistency_rule.dominant(targets),
            dominant_audience_emotion=self.consistency_rule.dominant(emotions),
            seriousness_humor_balance=(
                "seriousness_dominant"
                if sensitive_count * 2 >= len(stories)
                else "balanced"
            ),
            repeated_comparison_warnings=repeated,
            callback_opportunities=tuple(
                (story.event_id, story.punchline.callback_event_id)
                for story in stories
                if story.punchline.callback_event_id
            ),
            opener_commentary_function=(
                "fact_first_anchor"
                if stories[0].sensitivity.value != "ordinary"
                else "shared_disbelief_entry"
            ),
            closer_commentary_function=(
                "callback_close"
                if stories[-1].punchline.callback_event_id
                else "consequence_close"
            ),
            prohibited_framing=(
                "presenter_voice",
                "journalist_voice",
                "political_voice",
                "academic_voice",
                "lecturer_voice",
                "unsupported_claims",
            ),
        )
        validate_commentary_blueprint(
            blueprint,
            scout_input,
            context,
            {story.event_id for story in proposal.backup_stories},
        )
        trace = CommentaryBlueprintTrace(
            input_flow_order=order,
            decisions=tuple(decisions),
            fallbacks=tuple(fallbacks),
            validation_checks=(
                "optimized_order",
                "public_evidence",
                "target_separation",
                "transition_cardinality",
                "sensitivity_safeguards",
                "main_story_membership",
            ),
        )
        return CommentaryBuildResult(output=output, blueprint=blueprint, trace=trace)


def _decision(rule, event_id, code, values):
    return CommentaryDecision(rule=rule, event_id=event_id, code=code, values=values)
