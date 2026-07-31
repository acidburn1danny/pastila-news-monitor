"""Canonical Pastila Acidă Story Architecture configuration."""

from pastila_scout.editor.story.models import (
    ConsequenceType,
    NarrativeFunction,
    NarrativeStage,
    OpeningStrategy,
    PayoffType,
    StoryArchitecture,
    StoryArchitecturePrinciple,
    StoryPattern,
    StoryUnitType,
    TransitionRelationshipType,
)

CANONICAL_PRINCIPLE_IDS = (
    "story-begins-with-relevance",
    "editorial-core-appears-early",
    "context-follows-need",
    "facts-precede-dependent-satire",
    "consequence-not-buried",
    "chronology-is-tool",
    "one-primary-spine",
    "every-segment-has-function",
    "information-arrives-once",
    "background-earns-position",
    "evidence-based-escalation",
    "strongest-beat-placed-intentionally",
    "satire-punctuates",
    "seriousness-protected-space",
    "logical-transitions",
    "payoff-resolves-setup",
    "closure-does-not-restart",
    "one-clear-recognition",
    "compression-preserves-causality",
    "editor-in-chief-final-choice",
)
CANONICAL_PATTERN_IDS = (
    "fact-consequence-contradiction-payoff",
    "consequence-fact-context-payoff",
    "official-claim-reality-contrast-payoff",
    "chronology-revelation-consequence-payoff",
    "absurd-detail-systemic-problem-payoff",
    "individual-case-public-pattern-payoff",
    "accusation-response-evidence-resolution",
    "serious-event-institutional-failure-reflection",
)


def default_story_architecture() -> StoryArchitecture:
    principles = tuple(
        StoryArchitecturePrinciple(
            principle_id=identifier,
            order=order,
            title=identifier.replace("-", " ").title(),
            statement=f"Apply {identifier.replace('-', ' ')} without changing evidence.",
        )
        for order, identifier in enumerate(CANONICAL_PRINCIPLE_IDS, start=1)
    )
    patterns = tuple(
        StoryPattern(
            pattern_id=identifier,
            order=order,
            title=identifier.replace("-", " ").title(),
            description="An evidence-linked sequencing template, not generated prose.",
            appropriate_conditions=("Upstream evidence supports the selected spine.",),
            prohibited_conditions=("Blocked or unsupported central evidence.",),
            required_unit_types=(StoryUnitType.PRIMARY_FACT, StoryUnitType.PAYOFF),
            optional_unit_types=(StoryUnitType.CONTEXT, StoryUnitType.SATIRE_BEAT),
            required_narrative_functions=(
                NarrativeFunction.ESTABLISH_EVENT,
                NarrativeFunction.DELIVER_PAYOFF,
            ),
            default_stage_sequence=(
                NarrativeStage.OPENING,
                NarrativeStage.FACTUAL_SETUP,
                NarrativeStage.PAYOFF,
                NarrativeStage.CLOSURE,
            ),
            tonal_constraints=("Respect upstream seriousness and protected space.",),
            audience_constraints=("Keep relevance and comprehension early.",),
            factual_prerequisites=("Validated Editorial Decision Plan evidence.",),
            satirical_constraints=("Use only validated Satirical Opportunities.",),
            closure_expectations=("Resolve setup without introducing a new story.",),
        )
        for order, identifier in enumerate(CANONICAL_PATTERN_IDS, start=1)
    )
    return StoryArchitecture(
        architecture_id="pastila-acida-spoken-satirical-story-architecture",
        version="1.0.0",
        title="Pastila Acidă Spoken Satirical Story Architecture",
        project="Pastila Acidă",
        jurisdiction="Romania",
        primary_medium="spoken audio-video satirical current-affairs content",
        purpose="Sequence evidence, context, consequence, restraint, and justified satire without writing prose.",
        principles=principles,
        patterns=patterns,
        stage_order=tuple(NarrativeStage),
        supported_unit_types=tuple(StoryUnitType),
        supported_functions=tuple(NarrativeFunction),
        opening_strategies=tuple(OpeningStrategy),
        transition_relationships=tuple(TransitionRelationshipType),
        consequence_types=tuple(ConsequenceType),
        payoff_types=tuple(PayoffType),
        fixed_boundaries=(
            "Never change factual status, chronology, causality, or upstream decisions.",
            "Never reintroduce held or removed material.",
            "Never generate hooks, transitions, jokes, punchlines, or script prose.",
            "Never override Persona, Voice, Audience, or victim safeguards.",
        ),
    )


DEFAULT_STORY_ARCHITECTURE = default_story_architecture()
