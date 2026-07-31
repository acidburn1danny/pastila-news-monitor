"""Canonical language-neutral Spoken Communication Engine configuration."""

from pastila_scout.editor.communication.models import (
    AttentionModel,
    CommunicationContinuityModel,
    CommunicationFlowModel,
    CommunicationPrinciple,
    CommunicationTransitionModel,
    EmotionTimingModel,
    OrientationModel,
    PauseModel,
    PayoffTimingModel,
    ReferenceContinuityModel,
    RhythmModel,
    SpokenCommunicationEngine,
    TeleprompterCognitionModel,
    WorkingMemoryModel,
)

CANONICAL_COMMUNICATION_PRINCIPLES = (
    ("communication-serves-comprehension", "Communication serves comprehension"),
    ("comprehension-precedes-elegance", "Comprehension precedes elegance"),
    ("speech-unfolds-sequentially", "Speech unfolds sequentially"),
    ("working-memory-is-limited", "Working memory is limited"),
    ("information-arrives-when-needed", "Information arrives only when needed"),
    ("each-step-prepares-next", "Each communication step prepares the next"),
    ("one-dominant-purpose", "Every spoken unit has one dominant purpose"),
    ("dependencies-remain-local", "Dependencies remain local"),
    ("complexity-grows-gradually", "Complexity increases gradually"),
    ("variation-sustains-attention", "Variation sustains attention"),
    ("pauses-communicate-structure", "Pauses communicate structure"),
    ("rhythm-supports-cognition", "Rhythm supports cognition"),
    ("emphasis-follows-importance", "Emphasis follows importance"),
    ("callbacks-require-recognition", "Callbacks require recognition"),
    ("payoffs-require-preparation", "Payoffs require preparation"),
    ("reflection-needs-breathing-room", "Reflection needs breathing room"),
    ("conversation-retains-orientation", "Conversation retains orientation"),
    ("listener-never-becomes-lost", "The listener never becomes lost"),
    ("quality-outweighs-speed", "Communication quality outweighs speed"),
    ("editor-in-chief-final-authority", "Editor-in-Chief remains final authority"),
)

SUPPORTED_PROFILE_DIMENSIONS = (
    "preferred_pacing",
    "preferred_rhythm",
    "preferred_pause_density",
    "preferred_callback_density",
    "preferred_communication_tempo",
    "preferred_attention_recovery",
    "preferred_explanation_density",
    "preferred_transition_density",
)


def _policy(label: str) -> str:
    return f"Use {label} only to preserve comprehension and dependency clarity."


def default_spoken_communication_engine() -> SpokenCommunicationEngine:
    """Build the canonical language-neutral spoken communication policy."""

    principles = tuple(
        CommunicationPrinciple(
            principle_id=identifier,
            order=order,
            title=title,
            statement=f"{title} as a stable communication constraint.",
        )
        for order, (identifier, title) in enumerate(
            CANONICAL_COMMUNICATION_PRINCIPLES, start=1
        )
    )
    return SpokenCommunicationEngine(
        communication_engine_id="pastila-acida-spoken-communication-engine",
        version="1.0.0",
        title="Universal Spoken Communication Engine",
        project="Pastila Acidă",
        language="language-neutral",
        medium="spoken audio-video",
        purpose="Govern how approved meaning travels through spoken communication without generating language.",
        core_assumptions=(
            "The listener hears information only once.",
            "Speech is irreversible and unfolds over time.",
            "Attention fluctuates and working memory is limited.",
            "Comprehension is cumulative and timing affects understanding.",
            "Rhythm and silence carry structural information.",
            "Communication exists to transfer approved meaning.",
        ),
        principles=principles,
        working_memory=WorkingMemoryModel(
            concept_capacity=3,
            entity_capacity=4,
            reference_capacity=3,
            context_capacity=3,
            number_capacity=3,
            carry_over_capacity=3,
            overload_thresholds=(
                "A communication unit exceeds a configured capacity.",
                "Several unresolved dependencies remain active together.",
            ),
            recovery_strategy=(
                "Restore orientation before adding information.",
                "Resolve or retire active references before progression.",
            ),
        ),
        communication_flow=CommunicationFlowModel(
            orientation_flow=(_policy("orientation"),),
            fact_flow=(_policy("fact progression"),),
            context_flow=(_policy("context progression"),),
            consequence_flow=(_policy("consequence progression"),),
            emotion_flow=(_policy("emotion progression"),),
            reflection_flow=(_policy("reflection progression"),),
            satire_flow=(_policy("satire progression after factual setup"),),
            payoff_flow=(_policy("payoff progression after recognition"),),
            closure_flow=(_policy("closure without a new dependency"),),
        ),
        rhythm=RhythmModel(
            information_rhythm=_policy("information variation"),
            attention_rhythm=_policy("attention recovery"),
            sentence_rhythm=_policy("unit-length variation"),
            breathing_rhythm=_policy("breathing space"),
            contrast_rhythm=_policy("contrast spacing"),
            reflection_rhythm=_policy("reflection spacing"),
            callback_rhythm=_policy("callback spacing"),
            payoff_rhythm=_policy("setup-to-payoff spacing"),
            closing_rhythm=_policy("closure deceleration"),
        ),
        pauses=PauseModel(
            micro_pause=_policy("micro timing"),
            thinking_pause=_policy("thinking timing"),
            contrast_pause=_policy("contrast timing"),
            emotion_pause=_policy("emotion timing"),
            callback_pause=_policy("callback recognition timing"),
            gravity_pause=_policy("gravity timing"),
            closure_pause=_policy("closure timing"),
        ),
        attention=AttentionModel(
            attention_gain=_policy("early relevance"),
            attention_preservation=_policy("purposeful variation"),
            attention_recovery=_policy("orientation recovery"),
            attention_fatigue=_policy("cumulative-load monitoring"),
            attention_reset=_policy("a supported reset"),
            attention_overload=_policy("load reduction"),
        ),
        orientation=OrientationModel(
            topic_orientation=_policy("topic identity"),
            speaker_orientation=_policy("speaker position"),
            timeline_orientation=_policy("timeline position"),
            entity_orientation=_policy("entity identity"),
            context_orientation=_policy("context relevance"),
            reasoning_orientation=_policy("reasoning direction"),
        ),
        references=ReferenceContinuityModel(
            reference_introduction=_policy("reference introduction"),
            reference_continuation=_policy("unambiguous continuation"),
            reference_retirement=_policy("reference retirement"),
            reference_refresh=_policy("reference refresh after distance"),
            ambiguity_prevention=_policy("unique active reference"),
            listener_recall=_policy("proportionate recall support"),
        ),
        continuity=CommunicationContinuityModel(
            topic_continuity=_policy("topic continuity"),
            reasoning_continuity=_policy("reasoning continuity"),
            context_continuity=_policy("context continuity"),
            emotion_continuity=_policy("proportionate emotional movement"),
            satirical_continuity=_policy("satire attached to its factual target"),
            closing_continuity=_policy("closure continuity"),
        ),
        transitions=CommunicationTransitionModel(
            fact=_policy("fact movement"),
            context=_policy("context movement"),
            contrast=_policy("contrast movement"),
            cause=_policy("evidence-supported cause movement"),
            effect=_policy("evidence-supported effect movement"),
            chronology=_policy("chronology movement"),
            reflection=_policy("reflection movement"),
            satire=_policy("movement into or out of satire"),
            callback=_policy("callback movement"),
            payoff=_policy("payoff movement"),
        ),
        payoff_timing=PayoffTimingModel(
            minimum_setup_units=1,
            maximum_setup_units=8,
            recognition_dependency=_policy("setup recognition"),
            reflection_spacing=_policy("reflection before payoff"),
            callback_spacing=_policy("recognizable callback distance"),
            premature_payoff_prevention=_policy("complete setup before payoff"),
        ),
        emotion_timing=EmotionTimingModel(
            curiosity=_policy("curiosity"),
            surprise=_policy("surprise"),
            concern=_policy("concern"),
            frustration=_policy("frustration"),
            humor=_policy("humor after comprehension"),
            gravity=_policy("gravity and protected space"),
            reflection=_policy("reflection"),
            relief=_policy("relief"),
        ),
        teleprompter_cognition=TeleprompterCognitionModel(
            reading_continuity=_policy("reading continuity"),
            visual_continuity=_policy("visual scan continuity"),
            breathing_continuity=_policy("breathing continuity"),
            working_memory_continuity=_policy("working-memory continuity"),
            scan_continuity=_policy("scan continuity"),
        ),
        supported_profile_dimensions=SUPPORTED_PROFILE_DIMENSIONS,
        editor_in_chief_authority="The Editor-in-Chief controls final communication choices within fixed boundaries.",
        fixed_boundaries=(
            "Never generate language, wording, dialogue, scripts, humor, or transitions.",
            "Never alter facts, Story Architecture, or upstream editorial contracts.",
            "Never introduce language-specific grammar, syntax, or vocabulary rules.",
            "Never override Persona, Philosophy, Voice, Audience, or Decision safeguards.",
            "Never implement profile learning or mutate prompts and benchmarks.",
        ),
    )


DEFAULT_SPOKEN_COMMUNICATION_ENGINE = default_spoken_communication_engine()
