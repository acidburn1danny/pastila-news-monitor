"""Deterministic construction and validation of private editorial blueprints."""

from __future__ import annotations

from itertools import pairwise

from pastila_scout.contracts.editor_output import validate_editor_output_against_input
from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1
from pastila_scout.editor.blueprint_models import (
    BlueprintBuildResult,
    BlueprintDecision,
    BlueprintDecisionOutcome,
    BlueprintDecisionTrace,
    BlueprintReason,
    EditorialBlueprint,
    SegmentBlueprint,
    TransitionBlueprint,
)
from pastila_scout.editor.blueprint_rules import (
    ClosingBlueprintRule,
    ContinuityRule,
    EditorialAngleRule,
    EnergyCurveRule,
    EpisodeThemeRule,
    EvidenceDisciplineRule,
    NarrativeFunctionRule,
    OpeningBlueprintRule,
    SegmentIntentRule,
    TransitionIntentRule,
    closing_effect_for,
)
from pastila_scout.editor.flow_models import FlowOptimizationResult


class BlueprintValidationError(ValueError):
    """Raised when a private blueprint would violate public evidence boundaries."""


class EditorialBlueprintBuilder:
    """Apply controlled rules to a validated deterministic flow result."""

    def __init__(
        self,
        *,
        theme_rule: EpisodeThemeRule | None = None,
        intent_rule: SegmentIntentRule | None = None,
        angle_rule: EditorialAngleRule | None = None,
        function_rule: NarrativeFunctionRule | None = None,
        curve_rule: EnergyCurveRule | None = None,
        transition_rule: TransitionIntentRule | None = None,
        opening_rule: OpeningBlueprintRule | None = None,
        closing_rule: ClosingBlueprintRule | None = None,
        evidence_rule: EvidenceDisciplineRule | None = None,
        continuity_rule: ContinuityRule | None = None,
    ) -> None:
        self.theme_rule = theme_rule or EpisodeThemeRule()
        self.intent_rule = intent_rule or SegmentIntentRule()
        self.angle_rule = angle_rule or EditorialAngleRule()
        self.function_rule = function_rule or NarrativeFunctionRule()
        self.curve_rule = curve_rule or EnergyCurveRule()
        self.transition_rule = transition_rule or TransitionIntentRule()
        self.opening_rule = opening_rule or OpeningBlueprintRule()
        self.closing_rule = closing_rule or ClosingBlueprintRule()
        self.evidence_rule = evidence_rule or EvidenceDisciplineRule()
        self.continuity_rule = continuity_rule or ContinuityRule()

    def build(
        self,
        scout_input: ScoutEditorInputV1,
        profile: SelectionProfileV1,
        context: EpisodeContextV1,
        flow_result: FlowOptimizationResult,
    ) -> BlueprintBuildResult:
        """Build a controlled blueprint without changing the public output."""

        output = flow_result.output
        validate_editor_output_against_input(
            output,
            scout_input,
            selection_profile=profile,
            episode_context=context,
        )
        proposal = output.episode_proposal
        if proposal is None:
            raise BlueprintValidationError(
                "editorial blueprint requires a validated episode proposal"
            )
        event_map = {event.event_id: event for event in scout_input.ranked_events}
        flow_order = tuple(step.event_id for step in proposal.episode_flow)
        selected_ids = tuple(story.event_id for story in proposal.selected_stories)
        if flow_order != selected_ids:
            raise BlueprintValidationError(
                "public selected-story and flow orders must match"
            )
        events = tuple(event_map[event_id] for event_id in flow_order)
        levels = tuple(self.curve_rule.assign(event) for event in events)
        transitions = self._transitions(proposal.episode_flow)
        closing_transition = transitions[-1].intent if transitions else None
        closing_effect = (
            closing_effect_for(events[-1], levels[-1], closing_transition)
            if events
            else None
        )
        if closing_effect is None:
            raise BlueprintValidationError(
                "blueprint requires at least one selected event"
            )
        thesis = self.theme_rule.assign(events, levels, context, closing_effect)
        segments = tuple(
            SegmentBlueprint(
                position=position,
                event_id=event.event_id,
                intent=self.intent_rule.assign(
                    event,
                    position=position,
                    count=len(events),
                    public_transition=(
                        None
                        if position == 1
                        else proposal.episode_flow[
                            position - 1
                        ].expected_transition_type
                    ),
                    levels=levels[position - 1],
                ),
                angles=self.angle_rule.assign(event),
                narrative_function=self.function_rule.assign(
                    position=position,
                    count=len(events),
                    public_role=proposal.episode_flow[position - 1].role,
                ),
                levels=levels[position - 1],
                evidence=self.evidence_rule.assign(event),
                mandatory=event.event_id in context.mandatory_event_ids,
                recent_episode_reference=event.event_id
                in context.avoid_recent_event_ids,
            )
            for position, event in enumerate(events, start=1)
        )
        opening = self.opening_rule.assign(
            events[0],
            thesis.episode_tension,
            transitions[0].intent if transitions else None,
            context,
        )
        closing = self.closing_rule.assign(
            events[-1],
            levels[-1],
            closing_effect,
            closing_transition,
            events[-2].event_id if len(events) > 1 else None,
        )
        continuity = self.continuity_rule.assign(flow_order, context)
        blueprint = EditorialBlueprint(
            source_report_id=scout_input.report_id,
            flow_order=flow_order,
            thesis=thesis,
            segments=segments,
            transitions=transitions,
            opening=opening,
            closing=closing,
            continuity=continuity,
        )
        self._validate_blueprint(
            blueprint,
            scout_input,
            proposal.backup_stories,
            context,
        )
        trace = self._trace(blueprint, scout_input)
        return BlueprintBuildResult(output=output, blueprint=blueprint, trace=trace)

    def _transitions(self, flow_steps) -> tuple[TransitionBlueprint, ...]:
        values = []
        for previous, current in pairwise(flow_steps):
            public_type = current.expected_transition_type
            if public_type is None:
                raise BlueprintValidationError(
                    "every public adjacency requires a transition type"
                )
            intent = self.transition_rule.assign(
                public_type,
                enters_closer=current.position == len(flow_steps),
            )
            values.append(
                TransitionBlueprint(
                    from_event_id=previous.event_id,
                    to_event_id=current.event_id,
                    public_transition_type=public_type,
                    intent=intent,
                    reason_code=f"public_transition_{public_type}",
                )
            )
        return tuple(values)

    @staticmethod
    def _validate_blueprint(
        blueprint: EditorialBlueprint,
        scout_input: ScoutEditorInputV1,
        backups,
        context: EpisodeContextV1,
    ) -> None:
        source_events = {event.event_id: event for event in scout_input.ranked_events}
        backup_ids = {story.event_id for story in backups}
        excluded = set(context.excluded_event_ids)
        for segment in blueprint.segments:
            if segment.event_id in backup_ids:
                raise BlueprintValidationError(
                    "backup-only event cannot appear as a blueprint segment"
                )
            if segment.event_id in excluded:
                raise BlueprintValidationError(
                    "excluded event cannot appear as a blueprint segment"
                )
            source_event = source_events.get(segment.event_id)
            if source_event is None:
                raise BlueprintValidationError(
                    "blueprint segment is absent from Scout input"
                )
            public_evidence = {
                (item.source_id, item.url, item.title)
                for item in source_event.source_provenance
            }
            for reference in segment.evidence.provenance:
                if (
                    reference.source_id,
                    reference.url,
                    reference.title,
                ) not in public_evidence:
                    raise BlueprintValidationError(
                        "blueprint evidence is absent from public Scout provenance"
                    )
        if blueprint.continuity.excluded_event_ids_present:
            raise BlueprintValidationError(
                "continuity blueprint contains excluded selected events"
            )

    def _trace(
        self, blueprint: EditorialBlueprint, scout_input: ScoutEditorInputV1
    ) -> BlueprintDecisionTrace:
        theme = _decision(
            self.theme_rule.name,
            "episode_theme_assigned",
            assigned=(blueprint.thesis.dominant_theme.value,),
        )
        segment_intents = tuple(
            _decision(
                self.intent_rule.name,
                "segment_intent_assigned",
                event_ids=(segment.event_id,),
                assigned=(segment.intent.value,),
            )
            for segment in blueprint.segments
        )
        angles = tuple(
            _decision(
                self.angle_rule.name,
                "editorial_angles_assigned",
                event_ids=(segment.event_id,),
                assigned=tuple(value.value for value in segment.angles),
            )
            for segment in blueprint.segments
        )
        curves = tuple(
            _decision(
                self.curve_rule.name,
                "ordinal_levels_derived",
                event_ids=(segment.event_id,),
                assigned=(
                    f"tension:{segment.levels.tension_level}",
                    f"energy:{segment.levels.energy_level}",
                    f"satire:{segment.levels.satire_level}",
                    f"emotional:{segment.levels.emotional_weight}",
                ),
            )
            for segment in blueprint.segments
        )
        transition_decisions = tuple(
            _decision(
                self.transition_rule.name,
                transition.reason_code,
                event_ids=(transition.from_event_id, transition.to_event_id),
                assigned=(transition.intent.value,),
            )
            for transition in blueprint.transitions
        )
        evidence = tuple(
            _decision(
                self.evidence_rule.name,
                "public_evidence_referenced",
                event_ids=(segment.event_id,),
                assigned=tuple(
                    f"{item.source_id}|{item.url}"
                    for item in segment.evidence.provenance
                ),
            )
            for segment in blueprint.segments
        )
        fallbacks = tuple(
            _decision(
                self.curve_rule.name,
                "deterministic_score_fallback",
                event_ids=(event.event_id,),
                assigned=("final_score",),
                outcome=BlueprintDecisionOutcome.FALLBACK,
            )
            for event in scout_input.ranked_events
            if event.event_id in blueprint.flow_order
            and event.ai_editorial_score is None
        )
        opening = _decision(
            self.opening_rule.name,
            "opening_blueprint_assigned",
            event_ids=(blueprint.opening.event_id,),
            assigned=(blueprint.opening.opener_function.value,),
        )
        closing = _decision(
            self.closing_rule.name,
            "closing_blueprint_assigned",
            event_ids=(blueprint.closing.event_id,),
            assigned=(blueprint.closing.closing_mode.value,),
        )
        applied = (
            theme,
            *segment_intents,
            *angles,
            *curves,
            *transition_decisions,
            opening,
            closing,
            *evidence,
            _decision(
                self.continuity_rule.name,
                "continuity_references_copied",
                event_ids=blueprint.continuity.recent_event_ids_present,
            ),
        )
        return BlueprintDecisionTrace(
            input_flow_order=blueprint.flow_order,
            applied_rules=applied,
            assigned_episode_themes=(theme,),
            segment_intent_decisions=segment_intents,
            angle_decisions=angles,
            curve_decisions=curves,
            transition_intent_decisions=transition_decisions,
            opening_decision=opening,
            closing_decision=closing,
            evidence_decisions=evidence,
            conflicts=(),
            fallbacks=fallbacks,
        )


def _decision(
    rule: str,
    code: str,
    *,
    event_ids: tuple[int, ...] = (),
    assigned: tuple[str, ...] = (),
    outcome: BlueprintDecisionOutcome = BlueprintDecisionOutcome.APPLIED,
) -> BlueprintDecision:
    return BlueprintDecision(
        rule=rule,
        outcome=outcome,
        reason=BlueprintReason(
            code=code,
            message="A controlled deterministic blueprint value was assigned.",
        ),
        event_ids=event_ids,
        assigned_values=assigned,
    )
