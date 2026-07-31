"""Build deterministic private Pastila Acida voice execution plans."""

from collections import Counter

from pastila_scout.contracts.editor_output import validate_editor_output_against_input
from pastila_scout.editor.voice_models import (
    AntiRepetitionPlan,
    CallbackPlan,
    EpisodeExpressionBudget,
    EpisodeVoicePlan,
    HumorIntensity,
    MarkerPlan,
    MechanismBudget,
    MechanismType,
    OralityLevel,
    OralityProfile,
    RhetoricalQuestionPlan,
    RomanianExpressionPlan,
    SentenceRhythmPlan,
    StoryVoicePlan,
    VocativeMarkerFamily,
    VocativeMarkerPolicy,
    VoiceBuildResult,
    VoiceDecision,
    VoiceDecisionTrace,
)
from pastila_scout.editor.voice_rules import (
    CallbackRule,
    ConversationRegisterRule,
    EmotionalTemperatureRule,
    EmpathyVoiceRule,
    ExpressionRule,
    HumorRule,
    ProtectedDimensionRule,
    RoastEligibilityRule,
    VoiceMechanicsRule,
)
from pastila_scout.editor.voice_validation import validate_voice_plan


class VoiceModelBuilder:
    """Convert deterministic commentary plans into controlled voice plans."""

    def __init__(self) -> None:
        self.register_rule = ConversationRegisterRule()
        self.humor_rule = HumorRule()
        self.protected_rule = ProtectedDimensionRule()
        self.roast_rule = RoastEligibilityRule()
        self.empathy_rule = EmpathyVoiceRule()
        self.temperature_rule = EmotionalTemperatureRule()
        self.expression_rule = ExpressionRule()
        self.callback_rule = CallbackRule()
        self.mechanics_rule = VoiceMechanicsRule()

    def build(
        self,
        scout_input,
        profile,
        context,
        flow_result,
        editorial_blueprint,
        commentary_blueprint,
    ) -> VoiceBuildResult:
        """Return unchanged public output with a private voice plan and trace."""
        output = flow_result.output
        validate_editor_output_against_input(
            output,
            scout_input,
            selection_profile=profile,
            episode_context=context,
        )
        order = commentary_blueprint.flow_order
        if order != editorial_blueprint.flow_order:
            raise ValueError("voice inputs disagree on optimized flow order")
        event_map = {event.event_id: event for event in scout_input.ranked_events}
        stories = []
        decisions = []
        for index, source in enumerate(commentary_blueprint.stories):
            event = event_map[source.event_id]
            register = self.register_rule.assign(source)
            humor, escalation = self.humor_rule.assign(source)
            protected = self.protected_rule.assign(source)
            roast = self.roast_rule.assign(event, source, protected)
            empathy, sarcasm = self.empathy_rule.assign(source)
            temperature = self.temperature_rule.assign(source)
            expression_type, expression_function, expression_tone = (
                self.expression_rule.assign(source)
            )
            callback_type, callback_target, callback_count = self.callback_rule.assign(
                source
            )
            sensitive = bool(protected)
            vocative_count = 0 if sensitive else 1
            story = StoryVoicePlan(
                position=index + 1,
                event_id=source.event_id,
                conversation_register=register,
                orality=OralityProfile(
                    level=OralityLevel.HIGH,
                    fragmentation=(
                        OralityLevel.MEDIUM if sensitive else OralityLevel.HIGH
                    ),
                    interruptions=(
                        OralityLevel.LOW if sensitive else OralityLevel.MEDIUM
                    ),
                    connector_suppression=OralityLevel.MEDIUM,
                    conversational_density=OralityLevel.HIGH,
                ),
                sentence_rhythm=SentenceRhythmPlan(
                    rhythm="fact_then_controlled_variation",
                    fragment_ratio="reduced" if sensitive else "moderate",
                    pause_density=(
                        OralityLevel.HIGH if sensitive else OralityLevel.MEDIUM
                    ),
                    escalation_rhythm="restrained" if sensitive else "progressive",
                    reset_rhythm="after_humor_before_consequence",
                ),
                markers=MarkerPlan(
                    families=self.mechanics_rule.markers(source),
                    maximum_markers=2 if sensitive else 4,
                ),
                vocatives=VocativeMarkerPolicy(
                    allowed_families=() if sensitive else tuple(VocativeMarkerFamily),
                    prohibited_in_factual_summary=True,
                    maximum_per_story=vocative_count,
                    minimum_beats_between_uses=3,
                    prohibit_consecutive_usage=True,
                ),
                rhetorical_questions=RhetoricalQuestionPlan(
                    functions=(self.mechanics_rule.question(source),),
                    maximum_count=1,
                ),
                curiosity={
                    "trigger": self.mechanics_rule.curiosity(source),
                    "reveal_required": not sensitive,
                },
                humor_intensity=humor,
                humor_escalation=escalation,
                sarcasm_ceiling=sarcasm,
                roast_eligibility=roast,
                protected_dimensions=protected,
                empathy_mode=empathy,
                seriousness_reset=self.mechanics_rule.reset(source),
                direct_language_ceiling=self.mechanics_rule.language(source),
                profanity_ceiling=self.mechanics_rule.language(source),
                romanian_expression=RomanianExpressionPlan(
                    expression_type=expression_type,
                    function=expression_function,
                    tone=expression_tone,
                    maximum_count=0 if expression_type is None else 1,
                ),
                romanian_reference=self.mechanics_rule.reference(source),
                callback=CallbackPlan(
                    callback_type=callback_type,
                    target_event_id=callback_target,
                    maximum_count=callback_count,
                ),
                perspective_shift={
                    "primary": self.mechanics_rule.perspective(source),
                    "secondary": None,
                },
                emotional_temperature=temperature,
                absurd_reveal={
                    "level": self.mechanics_rule.absurd_reveal(source),
                    "after_factual_anchor": True,
                },
                ending_voice=self.mechanics_rule.ending(
                    source, index == len(commentary_blueprint.stories) - 1
                ),
                audience_knowledge=self.mechanics_rule.knowledge(event),
                audience_relationship="intelligent_peer",
                prohibited_voice_modes=(
                    "news_presenter",
                    "formal_editorialist",
                    "lecturer",
                    "political_commentator",
                    "moral_authority",
                ),
                safety_invariants=(
                    "facts_before_humor_escalation",
                    "protected_dimensions_never_punchlines",
                    "profanity_cannot_replace_content",
                    "imaginary_dialogue_never_invents_facts",
                    "no_ai_cliches",
                    "no_emotional_manipulation",
                    "audience_is_peer",
                ),
            )
            stories.append(story)
            for rule, values in (
                (self.register_rule.name, (register.value,)),
                (self.humor_rule.name, (humor.value, escalation.value)),
                (self.roast_rule.name, (roast.value,)),
                (self.empathy_rule.name, (empathy.value, sarcasm.value)),
            ):
                decisions.append(
                    VoiceDecision(
                        rule=rule,
                        event_id=source.event_id,
                        code="controlled_voice_value_assigned",
                        values=values,
                    )
                )
        callbacks = sum(story.callback.maximum_count for story in stories)
        expressions = sum(story.romanian_expression.maximum_count for story in stories)
        vocatives = sum(story.vocatives.maximum_per_story for story in stories)
        registers = Counter(story.conversation_register for story in stories)
        dominant_register = min(
            registers, key=lambda value: (-registers[value], value.value)
        )
        humor_order = tuple(HumorIntensity)
        global_humor = max(
            (story.humor_intensity for story in stories),
            key=humor_order.index,
        )
        plan = EpisodeVoicePlan(
            source_report_id=scout_input.report_id,
            flow_order=order,
            stories=tuple(stories),
            dominant_register=dominant_register,
            global_humor_ceiling=global_humor,
            profanity_ceiling=max(
                (story.profanity_ceiling for story in stories),
                key=lambda value: list(type(value)).index(value),
            ),
            emotional_arc=tuple(story.emotional_temperature for story in stories),
            callback_budget=callbacks,
            vocative_budget=vocatives,
            expression_budget=EpisodeExpressionBudget(
                maximum_total=expressions,
                maximum_twisted_proverbs=0,
            ),
            anti_repetition=AntiRepetitionPlan(
                budgets=tuple(
                    MechanismBudget(
                        mechanism=mechanism,
                        maximum_per_story=1,
                        maximum_per_episode=max(1, len(stories)),
                    )
                    for mechanism in MechanismType
                ),
                intentional_callback_exception=True,
            ),
            ending_register=stories[-1].conversation_register,
            consistency_plan=(
                "facts_precede_escalation",
                "shared_episode_budgets",
                "sensitive_stories_reduce_humor",
                "callbacks_are_explicit",
            ),
            audience_respect_invariants=(
                "no_excessive_explanation",
                "no_moralizing",
                "no_superiority",
                "no_emotional_manipulation",
                "no_teaching_voice",
                "no_generic_editorial_tone",
            ),
        )
        validate_voice_plan(plan, commentary_blueprint, output)
        trace = VoiceDecisionTrace(
            input_flow_order=order,
            decisions=tuple(decisions),
            fallbacks=(),
            validation_checks=(
                "optimized_order",
                "one_plan_per_story",
                "shared_budgets",
                "protected_dimensions",
                "roast_eligibility",
                "sensitivity_safeguards",
                "audience_respect",
                "upstream_output_unchanged",
            ),
        )
        return VoiceBuildResult(output=output, plan=plan, trace=trace)
