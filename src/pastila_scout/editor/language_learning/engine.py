"""Pure deterministic learning calculations and lifecycle decisions."""

from pastila_scout.editor.language_learning.defaults import (
    DEFAULT_EDITORIAL_LANGUAGE_LEARNING_ENGINE,
)
from pastila_scout.editor.language_learning.models import *


def derive_confidence(
    observations: int,
    episodes: int,
    stories: int,
    contexts: int,
    consistency: float,
    counter_evidence: int = 0,
    editor_confirmed: bool = False,
    explicit_rule: bool = False,
    recency: float = 1.0,
    scope_stability: float = 1.0,
    conflicts: int = 0,
) -> ConfidenceModel:
    if explicit_rule:
        score = 100
    else:
        score = round(
            min(observations, 4) * 6.25
            + min(episodes, 4) * 3.75
            + min(stories, 4) * 3.75
            + min(contexts, 4) * 2.5
            + consistency * 20
            + recency * 5
            + scope_stability * 5
            + (15 if editor_confirmed else 0)
            - counter_evidence * 10
            - conflicts * 10
        )
        score = max(0, min(100, score))
    state = (
        ConfidenceState.VERY_HIGH
        if score >= 85
        else (
            ConfidenceState.HIGH
            if score >= 70
            else (
                ConfidenceState.MODERATE
                if score >= 50
                else ConfidenceState.LOW if score >= 25 else ConfidenceState.VERY_LOW
            )
        )
    )
    return ConfidenceModel(
        score=score,
        state=state,
        observation_count=observations,
        episode_diversity=episodes,
        story_diversity=stories,
        context_diversity=contexts,
        editor_confirmation=editor_confirmed,
        explicit_editor_rule=explicit_rule,
        counter_evidence_count=counter_evidence,
        consistency=consistency,
        recency=recency,
        scope_stability=scope_stability,
        conflict_count=conflicts,
        explanation_references=("derived-confidence-policy",),
    )


def candidate_eligible(
    aggregation: ObservationAggregation,
    confidence: ConfidenceModel,
    counter_ratio: float,
) -> bool:
    p = DEFAULT_EDITORIAL_LANGUAGE_LEARNING_ENGINE.aggregation_policy
    return (
        aggregation.support_count >= p.minimum_observations
        and aggregation.episode_count >= p.minimum_episodes
        and aggregation.story_count >= p.minimum_diversity
        and aggregation.consistency >= p.minimum_consistency
        and counter_ratio <= p.maximum_counter_evidence_ratio
        and confidence.score >= p.minimum_confidence
    )


def next_preference_status(
    current: PreferenceStatus,
    target: PreferenceStatus,
    *,
    editor_authorized: bool = False,
) -> PreferenceStatus:
    transition = f"{current.value}->{target.value}"
    if transition == "deprecated->established" and editor_authorized:
        return target
    if (
        transition
        not in DEFAULT_EDITORIAL_LANGUAGE_LEARNING_ENGINE.lifecycle_policy.allowed_transitions
    ):
        raise ValueError(f"invalid preference lifecycle transition: {transition}")
    return target


def derive_decay(
    *,
    first_observation: str,
    last_observation: str,
    last_confirmation: str | None,
    observation_count: int,
    episode_count: int,
    story_count: int,
    periods_since_confirmation: int,
    consistency: float,
    counter_evidence_ratio: float,
    editor_confirmation: bool = False,
    explicit_rule: bool = False,
    deprecation_reason: str | None = None,
) -> PreferenceDecayPolicy:
    """Derive decay without deleting lineage or automatically decaying explicit rules."""
    if explicit_rule:
        state, adjustment = DecayState.STABLE, 0
    elif deprecation_reason:
        state, adjustment = DecayState.DEPRECATED, -35
    elif periods_since_confirmation >= 12 or counter_evidence_ratio >= 0.6:
        state, adjustment = DecayState.WEAKENING, -25
    elif periods_since_confirmation >= 6 or counter_evidence_ratio >= 0.35:
        state, adjustment = DecayState.AGING, -15
    elif editor_confirmation or periods_since_confirmation <= 2:
        state, adjustment = DecayState.STABLE, 0
    else:
        state, adjustment = DecayState.ACTIVE, -5
    influence = max(0, 100 + adjustment)
    return PreferenceDecayPolicy(
        first_observation=first_observation,
        last_observation=last_observation,
        last_confirmation=last_confirmation,
        observation_count=observation_count,
        episode_count=episode_count,
        story_count=story_count,
        time_since_confirmation=periods_since_confirmation,
        consistency=consistency,
        counter_evidence_ratio=counter_evidence_ratio,
        editor_confirmation=editor_confirmation,
        explicit_rule=explicit_rule,
        deprecation_reason=deprecation_reason,
        activity_status=state,
        confidence_adjustment=adjustment,
        influence_score=influence,
        recommendation_priority=influence,
    )


def project_guidance(
    profile: EditorialLanguageProfile,
    projection_id: str,
) -> GuidanceProjection:
    """Project active reference-only preferences; never emit or rewrite language."""
    eligible = profile.active_preferences + profile.explicit_rules
    guidance = tuple(
        LearnedGuidance(
            guidance_id=f"guidance-{item.preference_id}",
            source_preference_id=item.preference_id,
            status=item.status,
            confidence=item.confidence,
            scope=item.scope,
            supported_dimensions=(item.language_dimension,),
            requires_editor_review=item.requires_editor_review,
            compatibility_references=item.compatibility_references,
        )
        for item in sorted(eligible, key=lambda value: value.preference_id)
    )
    return GuidanceProjection(
        projection_id=projection_id,
        profile_id=profile.profile_id,
        guidance=guidance,
        preference_identifiers=tuple(item.source_preference_id for item in guidance),
        compatibility_references=tuple(
            sorted({ref for item in guidance for ref in item.compatibility_references})
        ),
    )


def append_evidence(
    evidence: EvidenceChain,
    *,
    observation_id: str,
    episode_id: str,
    story_id: str,
    edit_graph_id: str,
) -> EvidenceChain:
    """Return a new evidence chain while preserving the complete old prefix."""
    if observation_id in evidence.observation_identifiers:
        raise ValueError("evidence observation already exists")
    return evidence.model_copy(
        update={
            "observation_identifiers": evidence.observation_identifiers
            + (observation_id,),
            "episode_identifiers": evidence.episode_identifiers + (episode_id,),
            "story_identifiers": evidence.story_identifiers + (story_id,),
            "edit_graph_identifiers": evidence.edit_graph_identifiers
            + (edit_graph_id,),
            "chronological_references": evidence.chronological_references
            + (observation_id,),
        }
    )


def build_profile(
    *,
    profile_id: str,
    profile_version: str,
    editor_identity: str,
    observations: tuple[EditorialObservation, ...],
    preferences: tuple[EditorialPreference, ...],
    conflicts: tuple[PreferenceConflict, ...],
    explanation: LearningExplanation,
    candidate_count: int = 0,
) -> EditorialLanguageProfile:
    """Build a deterministic, reference-only profile from accepted artifacts."""
    ordered = tuple(sorted(preferences, key=lambda item: item.preference_id))
    bucket = lambda status: tuple(item for item in ordered if item.status == status)
    active = bucket(PreferenceStatus.ESTABLISHED)
    emerging = bucket(PreferenceStatus.EMERGING)
    explicit = bucket(PreferenceStatus.EXPLICIT_EDITOR_RULE)
    deprecated = bucket(PreferenceStatus.DEPRECATED)
    rejected = bucket(PreferenceStatus.REJECTED)
    archived = bucket(PreferenceStatus.ARCHIVED)
    confidence = (
        derive_confidence(
            sum(item.confidence.observation_count for item in ordered),
            sum(item.confidence.episode_diversity for item in ordered),
            sum(item.confidence.story_diversity for item in ordered),
            sum(item.confidence.context_diversity for item in ordered),
            (
                sum(item.confidence.consistency for item in ordered) / len(ordered)
                if ordered
                else 0
            ),
            sum(item.counter_evidence.contradiction_count for item in ordered),
            any(item.confidence.editor_confirmation for item in ordered),
            any(item.confidence.explicit_editor_rule for item in ordered),
        )
        if ordered
        else derive_confidence(0, 0, 0, 0, 0)
    )
    maturity = ProfileMaturityModel(
        state=(
            "established" if active or explicit else "emerging" if emerging else "empty"
        ),
        evidence_count=sum(
            len(item.evidence_chain.observation_identifiers) for item in ordered
        ),
        episode_diversity=len(
            {
                episode
                for item in ordered
                for episode in item.evidence_chain.episode_identifiers
            }
        ),
        story_diversity=len(
            {
                story
                for item in ordered
                for story in item.evidence_chain.story_identifiers
            }
        ),
        confidence=confidence.state,
    )
    values = {
        "profile_id": profile_id,
        "editor_identity": editor_identity,
        "learning_engine_id": DEFAULT_EDITORIAL_LANGUAGE_LEARNING_ENGINE.learning_engine_id,
        "profile_version": profile_version,
        "active_preferences": active,
        "emerging_preferences": emerging,
        "explicit_rules": explicit,
        "deprecated_preferences": deprecated,
        "rejected_preferences": rejected,
        "archived_preferences": archived,
        "conflicts": tuple(sorted(conflicts, key=lambda item: item.conflict_id)),
        "profile_confidence": confidence,
        "profile_maturity": maturity,
        "observation_count": len(observations),
        "candidate_count": candidate_count,
        "established_count": len(active),
        "emerging_count": len(emerging),
        "deprecated_count": len(deprecated),
        "explicit_rule_count": len(explicit),
        "conflict_count": len(conflicts),
        "counter_evidence_count": sum(
            item.counter_evidence.contradiction_count for item in ordered
        ),
        "profile_explanation": explanation,
        "profile_fingerprint": "0" * 64,
    }
    from pastila_scout.editor.language_learning.fingerprint import artifact_fingerprint

    probe = EditorialLanguageProfile(**values)
    values["profile_fingerprint"] = artifact_fingerprint(probe)
    return EditorialLanguageProfile(**values)
