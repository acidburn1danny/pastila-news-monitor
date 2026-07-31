"""Validation for immutable editorial learning contracts."""

import re

from pastila_scout.editor.language_learning.engine import derive_confidence
from pastila_scout.editor.language_learning.fingerprint import semantic_fingerprint
from pastila_scout.editor.language_learning.models import *
from pastila_scout.editor.language_learning.readiness import (
    determine_learning_readiness,
)

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


class LanguageLearningValidationError(ValueError):
    pass


def validate_learning_engine(engine: EditorialLanguageLearningEngine):
    errors = []
    if not _SEMVER.fullmatch(engine.version):
        errors.append("invalid semantic version")
    if len(engine.principles) != 30 or len(set(engine.principles)) != 30:
        errors.append("all 30 unique principles required")
    if engine.contains_generation or engine.runtime_persistence:
        errors.append("learning engine cannot generate or persist runtime state")
    if errors:
        raise LanguageLearningValidationError("; ".join(errors))
    return engine


def validate_contract_identity(artifact):
    if not getattr(artifact, "canonical_identifier", None):
        raise LanguageLearningValidationError("missing canonical identifier")
    if not _SEMVER.fullmatch(artifact.version):
        raise LanguageLearningValidationError("invalid contract semantic version")
    return artifact


def validate_artifact(artifact):
    """Apply universal validation shared by every learning-domain artifact."""
    validate_contract_identity(artifact)
    forbidden_truthy = {
        "contains_text",
        "contains_wording",
        "contains_generated_language",
        "contains_generated_prose",
        "contains_generated_text",
        "contains_language",
        "contains_generation",
        "runtime_persistence",
    }
    violations = [
        name
        for name in forbidden_truthy
        if hasattr(artifact, name) and bool(getattr(artifact, name))
    ]
    if violations:
        raise LanguageLearningValidationError(
            "forbidden generated or runtime content: " + ", ".join(sorted(violations))
        )
    return artifact


def validate_confidence(confidence: ConfidenceModel):
    """Reject manually assigned or internally inconsistent confidence."""
    expected = derive_confidence(
        confidence.observation_count,
        confidence.episode_diversity,
        confidence.story_diversity,
        confidence.context_diversity,
        confidence.consistency,
        confidence.counter_evidence_count,
        confidence.editor_confirmation,
        confidence.explicit_editor_rule,
        confidence.recency,
        confidence.scope_stability,
        confidence.conflict_count,
    )
    if not confidence.derived or (confidence.score, confidence.state) != (
        expected.score,
        expected.state,
    ):
        raise LanguageLearningValidationError(
            "confidence must be deterministically derived from its evidence factors"
        )
    return confidence


def validate_edit_graph(
    graph: LanguageEditGraph, intents: tuple[EditorialIntentModel, ...]
):
    ids = [x.operation_id for x in graph.ordered_operations]
    intent_ids = {x.intent_id for x in intents}
    errors = []
    if len(ids) != len(set(ids)):
        errors.append("duplicate operation identifiers")
    if any(x.intent_reference not in intent_ids for x in graph.ordered_operations):
        errors.append("operation without intent")
    if any(
        x.affected_dimension not in {item.value for item in LanguageDimension}
        for x in graph.ordered_operations
    ):
        errors.append("operation has unsupported language dimension")
    if any(x.contains_wording for x in graph.ordered_operations) or graph.contains_text:
        errors.append("edit graph cannot contain generated language")
    if graph.graph_fingerprint != semantic_fingerprint(
        graph.model_dump(exclude={"graph_fingerprint"})
    ):
        errors.append("graph fingerprint mismatch")
    edges = {
        (x.predecessor_operation_id, x.successor_operation_id)
        for x in graph.dependency_edges
    }
    if any(a not in ids or b not in ids for a, b in edges):
        errors.append("graph edge references unknown operation")
    order = {operation_id: index for index, operation_id in enumerate(ids)}
    if any(a in order and b in order and order[a] >= order[b] for a, b in edges):
        errors.append("graph dependency contradicts operation order")
    if set(graph.editor_intent_references) != {
        item.intent_reference for item in graph.ordered_operations
    }:
        errors.append("graph intent lineage mismatch")
    if errors:
        raise LanguageLearningValidationError("; ".join(errors))
    return graph


def validate_editorial_intent(intent: EditorialIntentModel):
    validate_artifact(intent)
    if intent.category not in {item.value for item in EditorialIntentCategory}:
        raise LanguageLearningValidationError("unsupported editorial intent category")
    return intent


def validate_observations(
    observations: tuple[EditorialObservation, ...],
    graphs: tuple[LanguageEditGraph, ...],
    intents: tuple[EditorialIntentModel, ...],
):
    graph_ids = {x.graph_id for x in graphs}
    intent_ids = {x.intent_id for x in intents}
    ids = [x.observation_id for x in observations]
    errors = []
    if len(ids) != len(set(ids)):
        errors.append("duplicate observations")
    for x in observations:
        if (
            x.edit_graph_reference not in graph_ids
            or x.editor_intent_reference not in intent_ids
        ):
            errors.append("orphan observation")
        if not x.validated_editor_correction:
            errors.append("only validated corrections become observations")
        if any(
            dimension not in {item.value for item in LanguageDimension}
            for dimension in x.affected_language_dimensions
        ):
            errors.append("observation has unsupported language dimension")
        if x.semantic_fingerprint != semantic_fingerprint(
            x.model_dump(exclude={"semantic_fingerprint", "provenance_timestamp"})
        ):
            errors.append("observation fingerprint mismatch")
    if errors:
        raise LanguageLearningValidationError("; ".join(errors))
    return observations


def validate_preference(preference: EditorialPreference, observation_ids: set[str]):
    errors = []
    if not set(preference.evidence_chain.observation_identifiers).issubset(
        observation_ids
    ):
        errors.append("preference missing observation evidence")
    if (
        preference.status
        in {PreferenceStatus.ESTABLISHED, PreferenceStatus.EXPLICIT_EDITOR_RULE}
        and not preference.evidence_chain.observation_identifiers
    ):
        errors.append("active preference requires evidence")
    try:
        validate_confidence(preference.confidence)
    except LanguageLearningValidationError as exc:
        errors.append(str(exc))
    if preference.counter_evidence.contradiction_count > 0 and not (
        preference.counter_evidence.conflicting_observation_identifiers
        or preference.counter_evidence.editor_rejection_references
        or preference.counter_evidence.explicit_override_references
    ):
        errors.append("counter evidence count requires permanent lineage")
    if set(preference.predecessor_preference_ids) & set(
        preference.successor_preference_ids
    ):
        errors.append("predecessor and successor lineage cannot overlap")
    if preference.explanation.contains_generated_prose:
        errors.append("explanations must be reference-only")
    if errors:
        raise LanguageLearningValidationError("; ".join(errors))
    return preference


def validate_evidence_chain(evidence: EvidenceChain, observation_ids: set[str]):
    if not set(evidence.observation_identifiers).issubset(observation_ids):
        raise LanguageLearningValidationError("orphan evidence observation reference")
    if len(evidence.chronological_references) != len(
        set(evidence.chronological_references)
    ):
        raise LanguageLearningValidationError("evidence chronology contains duplicates")
    lineage_lengths = {
        len(evidence.observation_identifiers),
        len(evidence.episode_identifiers),
        len(evidence.story_identifiers),
        len(evidence.edit_graph_identifiers),
        len(evidence.chronological_references),
    }
    if len(lineage_lengths) != 1:
        raise LanguageLearningValidationError("evidence lineage is incomplete")
    return evidence


def validate_learning_evidence(
    evidence: LearningEvidence,
    observation_ids: set[str],
):
    if not set(evidence.observation_references).issubset(observation_ids):
        raise LanguageLearningValidationError("orphan learning evidence observation")
    if evidence.support_count != len(evidence.observation_references):
        raise LanguageLearningValidationError(
            "learning evidence support count mismatch"
        )
    if evidence.contradiction_count != len(evidence.counter_evidence_references):
        raise LanguageLearningValidationError(
            "learning evidence contradiction count mismatch"
        )
    return evidence


def validate_candidate(candidate: LearningCandidate, observation_ids: set[str]):
    if not set(candidate.origin_observations).issubset(observation_ids):
        raise LanguageLearningValidationError("candidate without observations")
    validate_confidence(candidate.confidence)
    if not candidate.inactive:
        raise LanguageLearningValidationError(
            "learning candidates must remain inactive"
        )
    if candidate.eligible and not candidate.supporting_evidence_references:
        raise LanguageLearningValidationError("eligible candidate requires evidence")
    return candidate


def validate_conflict(conflict: PreferenceConflict, preference_ids: set[str]):
    if not set(conflict.preference_identifiers).issubset(preference_ids):
        raise LanguageLearningValidationError("conflict references orphan preference")
    if conflict.resolved != (conflict.resolution_status != "unresolved"):
        raise LanguageLearningValidationError("conflict resolution state mismatch")
    if not conflict.evidence_references or not conflict.explanation_references:
        raise LanguageLearningValidationError(
            "conflict requires evidence and explanation"
        )
    return conflict


def validate_supersession(
    supersession: PreferenceSupersession, preference_ids: set[str]
):
    if supersession.old_preference_id == supersession.new_preference_id:
        raise LanguageLearningValidationError("preference cannot supersede itself")
    if not {
        supersession.old_preference_id,
        supersession.new_preference_id,
    }.issubset(preference_ids):
        raise LanguageLearningValidationError(
            "supersession references orphan preference"
        )
    return supersession


def validate_decay(decay: PreferenceDecayPolicy):
    if decay.explicit_rule and (
        decay.confidence_adjustment < 0
        or decay.influence_score < 100
        or decay.activity_status
        in {DecayState.AGING, DecayState.WEAKENING, DecayState.DEPRECATED}
    ):
        raise LanguageLearningValidationError(
            "explicit editor rules cannot decay automatically"
        )
    if decay.counter_evidence_ratio < 0 or decay.counter_evidence_ratio > 1:
        raise LanguageLearningValidationError("invalid counter evidence ratio")
    return decay


def validate_compatibility(snapshot: LearningCompatibilitySnapshot):
    ids = [item.module_id for item in snapshot.dependencies]
    if len(ids) != len(set(ids)):
        raise LanguageLearningValidationError(
            "duplicate upstream compatibility identity"
        )
    if snapshot.canonical_mutation:
        raise LanguageLearningValidationError("canonical mutation is forbidden")
    return snapshot


def validate_guidance_projection(
    projection: GuidanceProjection, preference_ids: set[str]
):
    if not projection.advisory_only:
        raise LanguageLearningValidationError("guidance must remain advisory")
    if not set(projection.preference_identifiers).issubset(preference_ids):
        raise LanguageLearningValidationError("guidance references orphan preferences")
    if any(
        item.contains_language or not item.advisory_only for item in projection.guidance
    ):
        raise LanguageLearningValidationError(
            "guidance cannot contain or edit language"
        )
    return projection


def validate_profile(profile: EditorialLanguageProfile, observation_ids: set[str]):
    preferences = (
        profile.active_preferences
        + profile.emerging_preferences
        + profile.explicit_rules
        + profile.deprecated_preferences
        + profile.rejected_preferences
        + profile.archived_preferences
    )
    ids = [x.preference_id for x in preferences]
    if len(ids) != len(set(ids)):
        raise LanguageLearningValidationError(
            "duplicate profile preference identifiers"
        )
    for item in preferences:
        validate_preference(item, observation_ids)
    buckets = {
        PreferenceStatus.ESTABLISHED: profile.active_preferences,
        PreferenceStatus.EMERGING: profile.emerging_preferences,
        PreferenceStatus.EXPLICIT_EDITOR_RULE: profile.explicit_rules,
        PreferenceStatus.DEPRECATED: profile.deprecated_preferences,
        PreferenceStatus.REJECTED: profile.rejected_preferences,
        PreferenceStatus.ARCHIVED: profile.archived_preferences,
    }
    if any(
        item.status != status for status, items in buckets.items() for item in items
    ):
        raise LanguageLearningValidationError("profile status bucket mismatch")
    if profile.observation_count != len(observation_ids):
        raise LanguageLearningValidationError("profile observation count mismatch")
    if profile.established_count != len(profile.active_preferences):
        raise LanguageLearningValidationError("profile established count mismatch")
    if profile.emerging_count != len(profile.emerging_preferences):
        raise LanguageLearningValidationError("profile emerging count mismatch")
    if profile.deprecated_count != len(profile.deprecated_preferences):
        raise LanguageLearningValidationError("profile deprecated count mismatch")
    if profile.explicit_rule_count != len(profile.explicit_rules):
        raise LanguageLearningValidationError("profile explicit rule count mismatch")
    if profile.conflict_count != len(profile.conflicts):
        raise LanguageLearningValidationError("profile conflict count mismatch")
    if profile.contains_generated_text:
        raise LanguageLearningValidationError("profile cannot store generated language")
    if profile.profile_fingerprint != semantic_fingerprint(
        profile.model_dump(exclude={"profile_fingerprint"})
    ):
        raise LanguageLearningValidationError("profile fingerprint mismatch")
    return profile


def validate_learning_session(session: LearningSession):
    if session.compatibility is not None:
        validate_compatibility(session.compatibility)
    expected = determine_learning_readiness(session)
    if session.readiness != expected:
        raise LanguageLearningValidationError(
            f"learning readiness must be {expected.value}"
        )
    if session.fingerprint != semantic_fingerprint(
        session.model_dump(exclude={"fingerprint"})
    ):
        raise LanguageLearningValidationError("session fingerprint mismatch")
    return session
