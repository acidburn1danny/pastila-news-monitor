"""Canonical editorial language learning policy."""

from pastila_scout.editor.language_learning.models import *

_PRINCIPLES = (
    "generated-language-never-knowledge",
    "validated-corrections-only",
    "observations-immutable",
    "observations-not-preferences",
    "preferences-derived",
    "evidence-required",
    "counter-evidence-considered",
    "confidence-derived",
    "history-immutable",
    "local-remains-local",
    "episode-not-project",
    "repetition-increases-confidence",
    "counter-evidence-reduces-confidence",
    "confirmation-strengthens",
    "explicit-rules-override",
    "deprecated-visible",
    "superseded-traceable",
    "conflicts-reviewed",
    "canonical-contracts-immutable",
    "factual-meaning-immutable",
    "legal-status-immutable",
    "attribution-immutable",
    "evidence-immutable",
    "story-architecture-immutable",
    "spoken-communication-immutable",
    "romanian-policy-immutable",
    "deterministic",
    "explainable",
    "active-lineage-complete",
    "editor-final-authority",
)


def default_editorial_language_learning_engine():
    return EditorialLanguageLearningEngine(
        learning_engine_id="pastila-acida-editorial-language-learning-engine",
        version="1.0.0",
        title="Editorial Language Learning Engine",
        project="Pastila Acidă",
        language="Romanian",
        learning_scope="editorial language preferences",
        editor="Editor-in-Chief",
        principles=_PRINCIPLES,
        confidence_policy=ConfidencePolicy(),
        aggregation_policy=PreferenceAggregationPolicy(),
        candidate_policy=LearningCandidatePolicy(
            candidate_eligibility=("sufficient evidence",),
            candidate_expiration=("editor review",),
            candidate_review=("conflict",),
            candidate_rejection=("insufficient evidence",),
            candidate_promotion=("threshold met",),
            candidate_conflict_detection=("scope and intent",),
        ),
        promotion_policy=PreferencePromotionPolicy(),
        deprecation_policy=PreferenceDeprecationPolicy(),
        conflict_engine=ConflictEngine(supported_conflicts=tuple(ConflictType)),
        counter_evidence_policy=CounterEvidencePolicy(
            sources=(
                "editor rejection",
                "opposite correction",
                "unchanged usage",
                "deprecated rule",
                "conflicting explicit rule",
            )
        ),
        lifecycle_policy=PreferenceLifecyclePolicy(
            allowed_transitions=(
                "candidate->emerging",
                "emerging->established",
                "established->deprecated",
                "deprecated->archived",
                "candidate->rejected",
                "explicit_editor_rule->established",
                "established->superseded",
            )
        ),
        fixed_boundaries=(
            "Never store generated language, scripts, articles, jokes, paragraphs, or replacement wording.",
            "Never change facts, evidence, chronology, legal meaning, attribution, or canonical editorial contracts.",
            "Never learn from AI output, unreviewed text, or speculation.",
            "Never widen scope automatically or mutate Editorial Memory.",
        ),
    )


DEFAULT_EDITORIAL_LANGUAGE_LEARNING_ENGINE = (
    default_editorial_language_learning_engine()
)
