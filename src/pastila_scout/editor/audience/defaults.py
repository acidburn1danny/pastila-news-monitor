"""Canonical Pastila Acidă Audience Model configuration."""

from __future__ import annotations

from pastila_scout.editor.audience.models import (
    AudienceCognitiveProfile,
    AudienceKnowledgeProfile,
    AudienceModel,
    AudiencePrinciple,
    AudienceTrustProfile,
    ChronologyComplexity,
    ConceptComplexity,
    ContextLoad,
    EntityLoad,
    InformationDensity,
    NumericLoad,
    PriorKnowledgeLevel,
    Tolerance,
)

_PRINCIPLES = (
    ("audience-is-intelligent", "The audience is intelligent"),
    ("intelligence-not-prior-knowledge", "Intelligence does not imply prior knowledge"),
    ("proportionate-context", "Context must be proportionate"),
    ("audience-listens", "The audience listens, not studies"),
    ("attention-is-finite", "Attention is finite"),
    ("reason-to-care", "The audience needs a reason to care"),
    ("respect-through-clarity", "Respect is demonstrated through clarity"),
    ("do-not-lecture", "Do not lecture"),
    ("do-not-manipulate-emotion", "Do not manipulate emotion"),
    ("trust-over-impact", "Trust is more valuable than momentary impact"),
    ("accepts-strong-voice", "The audience accepts strong editorial voice"),
    ("rejects-artificial-neutrality", "The audience rejects artificial neutrality"),
    ("prefers-concrete-information", "The audience prefers concrete information"),
    ("purposeful-repetition", "Repetition must have a purpose"),
    ("humor-supports-comprehension", "Humor should not compete with comprehension"),
    ("audience-agency", "The audience must retain agency"),
    ("story-specific-calibration", "Different stories require different calibration"),
    (
        "editor-in-chief-audience-authority",
        "The Editor-in-Chief is final audience authority",
    ),
)
_PROHIBITED_ASSUMPTIONS = (
    "knowing all acronyms",
    "knowing all named officials",
    "knowing previous episodes",
    "knowing institutional procedures",
    "knowing the chronology of a developing story",
    "knowing why an administrative detail matters",
    "sharing the project's political conclusions in advance",
)
_TRUST_FOUNDATIONS = (
    "factual fidelity",
    "clear attribution",
    "transparent uncertainty",
    "proportional framing",
    "correction readiness",
    "consistency",
    "respect for victims",
    "distinction between fact and commentary",
    "avoidance of manipulation",
)


def _cognitive_profile() -> AudienceCognitiveProfile:
    return AudienceCognitiveProfile(
        preferred_information_density=InformationDensity.MODERATE,
        maximum_recommended_context_load=ContextLoad.MODERATE,
        maximum_recommended_entity_load=EntityLoad.MODERATE,
        maximum_recommended_numeric_load=NumericLoad.MODERATE,
        chronology_tolerance=ChronologyComplexity.LAYERED,
        concept_complexity_tolerance=ConceptComplexity.EXPLAINABLE,
        repetition_tolerance=Tolerance.LOW,
        acronym_tolerance=Tolerance.LOW,
        unresolved_reference_tolerance=Tolerance.LOW,
        recommended_mitigation_strategies=(
            "Introduce relevance early.",
            "Expand necessary acronyms.",
            "Reduce names, numbers, and repeated context.",
            "Keep chronology and referents explicit.",
        ),
    )


def default_audience_model() -> AudienceModel:
    principles = tuple(
        AudiencePrinciple(
            principle_id=identifier,
            order=order,
            title=title,
            statement=f"{title} as a stable Pastila Acidă audience assumption.",
            required_behaviors=(
                "Apply the assumption proportionately to supplied evidence.",
            ),
            prohibited_behaviors=(
                "Use the assumption to manipulate or stereotype viewers.",
            ),
        )
        for order, (identifier, title) in enumerate(_PRINCIPLES, start=1)
    )
    return AudienceModel(
        audience_id="pastila-acida-core-audience",
        version="1.0.0",
        title="Pastila Acidă Core Audience",
        project="Pastila Acidă",
        jurisdiction="Romania",
        primary_medium="spoken audio-video satirical current-affairs content",
        audience_assumptions=(
            "intelligent",
            "capable of implication and nuance",
            "culturally aware",
            "familiar with everyday Romanian realities",
            "skeptical of institutional language",
            "sensitive to hypocrisy and contradiction",
            "interested in meaningful satire",
            "impatient with unnecessary exposition",
            "capable of empathy",
            "unwilling to tolerate manipulation or condescension",
        ),
        excluded_assumptions=(
            "universally politically aligned",
            "uniformly educated or informed",
            "captive, passive, or gullible",
            "incapable of nuance",
            "interested only in jokes or outrage",
            "demographic stereotype",
        ),
        principles=principles,
        knowledge_profile=AudienceKnowledgeProfile(
            default_prior_knowledge=PriorKnowledgeLevel.GENERAL,
            assumed_knowledge_categories=("everyday Romanian social realities",),
            required_context_categories=(
                "story-specific actors and relevance",
                "necessary chronology",
                "unfamiliar institutions and acronyms",
            ),
            specialist_knowledge_categories=(
                "legal procedure",
                "institutional procedure",
                "specialist policy detail",
            ),
            recurring_project_knowledge=(),
            prohibited_assumptions=_PROHIBITED_ASSUMPTIONS,
        ),
        cognitive_profile=_cognitive_profile(),
        trust_profile=AudienceTrustProfile(foundations=_TRUST_FOUNDATIONS),
        default_emotional_policy=(
            "Ground emotion in supplied facts and consequences.",
            "Never guarantee, manufacture, or prescribe audience emotion.",
        ),
        fatigue_policy=(
            "Track cumulative entity, acronym, numeric, context, repetition, and tonal fatigue.",
        ),
        attention_policy=(
            "Treat attention loss as an editorial risk, not a scientific prediction.",
            "Place comprehension before satirical payoff.",
        ),
        fixed_boundaries=(
            "Never distort facts or hide uncertainty.",
            "Never manipulate, condescend, stereotype, or exploit victims.",
            "Never infer demographic traits from verdicts.",
            "Never override Persona or Satirical Voice boundaries.",
        ),
    )


DEFAULT_AUDIENCE_MODEL = default_audience_model()
