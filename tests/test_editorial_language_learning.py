"""Focused immutable editorial language learning tests."""

import pytest
from pydantic import ValidationError

from pastila_scout.editor.language_learning import *


def _intent():
    return EditorialIntentModel(
        intent_id="intent-1",
        category="increase_clarity",
        explanation_reference="reason-1",
    )


def _operation():
    return LanguageEditOperation(
        operation_id="op-1",
        operation_type=OperationType.REMOVE,
        affected_dimension="connector",
        intent_reference="intent-1",
        semantic_effect="formal_connector_removed",
    )


def _graph():
    values = {
        "graph_id": "graph-1",
        "source_reference": "original-1",
        "target_reference": "edited-1",
        "ordered_operations": (_operation(),),
        "editor_intent_references": ("intent-1",),
        "graph_fingerprint": "0" * 64,
    }
    probe = LanguageEditGraph(**values)
    values["graph_fingerprint"] = semantic_fingerprint(
        probe.model_dump(exclude={"graph_fingerprint"})
    )
    return LanguageEditGraph(**values)


def _observation():
    values = {
        "observation_id": "observation-1",
        "edit_graph_reference": "graph-1",
        "editor_intent_reference": "intent-1",
        "affected_policy_identifiers": ("connector-policy",),
        "affected_language_dimensions": ("connector",),
        "episode_reference": "episode-1",
        "story_reference": "story-1",
        "editor_reference": "editor",
        "provenance_reference": "correction-import-1",
        "scope": ObservationScope.LOCAL,
        "semantic_fingerprint": "0" * 64,
    }
    probe = EditorialObservation(**values)
    values["semantic_fingerprint"] = semantic_fingerprint(
        probe.model_dump(exclude={"semantic_fingerprint", "provenance_timestamp"})
    )
    return EditorialObservation(**values)


def _explanation():
    return LearningExplanation(
        explanation_id="explanation-1",
        why_learned=("observation-1",),
        why_rejected=(),
        why_promoted=("threshold-1",),
        why_deprecated=(),
        confidence_change_reasons=("derived-confidence-policy",),
        conflict_reasons=(),
        explicit_rule_reasons=(),
        scope_change_reasons=(),
    )


def _preference(status=PreferenceStatus.ESTABLISHED, preference_id="preference-1"):
    return EditorialPreference(
        preference_id=preference_id,
        language_dimension="connector",
        editorial_intent="increase_clarity",
        status=status,
        confidence=derive_confidence(4, 3, 3, 2, 0.9),
        evidence_chain=EvidenceChain(
            evidence_id=f"evidence-{preference_id}",
            observation_identifiers=("observation-1",),
            episode_identifiers=("episode-1",),
            story_identifiers=("story-1",),
            edit_graph_identifiers=("graph-1",),
            chronological_references=("observation-1",),
        ),
        counter_evidence=CounterEvidence(
            counter_evidence_id=f"counter-{preference_id}", contradiction_count=0
        ),
        scope=ObservationScope.STORY,
        activation_rules=("threshold-1",),
        deprecation_rules=("editor-action",),
        supersession_rules=("successor-required",),
        compatibility_references=("story-architecture",),
        requires_editor_review=False,
        explanation=_explanation(),
    )


def _profile(preference):
    values = {
        "profile_id": "profile-1",
        "editor_identity": "editor-in-chief",
        "learning_engine_id": "pastila-acida-editorial-language-learning-engine",
        "profile_version": "1.0.0",
        "active_preferences": (preference,),
        "emerging_preferences": (),
        "explicit_rules": (),
        "deprecated_preferences": (),
        "rejected_preferences": (),
        "archived_preferences": (),
        "conflicts": (),
        "profile_confidence": preference.confidence,
        "profile_maturity": ProfileMaturityModel(
            state="established",
            evidence_count=1,
            episode_diversity=1,
            story_diversity=1,
            confidence=preference.confidence.state,
        ),
        "observation_count": 1,
        "candidate_count": 0,
        "established_count": 1,
        "emerging_count": 0,
        "deprecated_count": 0,
        "explicit_rule_count": 0,
        "conflict_count": 0,
        "counter_evidence_count": 0,
        "profile_explanation": _explanation(),
        "profile_fingerprint": "0" * 64,
    }
    probe = EditorialLanguageProfile(**values)
    values["profile_fingerprint"] = artifact_fingerprint(probe)
    return EditorialLanguageProfile(**values)


def test_identity_and_immutability():
    engine = DEFAULT_EDITORIAL_LANGUAGE_LEARNING_ENGINE
    assert validate_learning_engine(engine) is engine
    assert (
        engine.learning_engine_id == "pastila-acida-editorial-language-learning-engine"
    )
    with pytest.raises(ValidationError):
        engine.title = "changed"


def test_graph_validation_order_render_and_fingerprint():
    graph = _graph()
    assert validate_edit_graph(graph, (_intent(),)) is graph
    assert "op-1" in render_edit_graph(graph)
    assert graph_fingerprint(graph) == graph_fingerprint(graph.model_copy(deep=True))


def test_graph_rejects_unknown_intent_and_text():
    with pytest.raises(LanguageLearningValidationError):
        validate_edit_graph(_graph(), ())
    with pytest.raises(LanguageLearningValidationError):
        validate_edit_graph(
            _graph().model_copy(update={"contains_text": True}), (_intent(),)
        )


def test_observation_creation_immutability_lineage_and_fingerprint():
    item = _observation()
    assert validate_observations((item,), (_graph(),), (_intent(),)) == (item,)
    with pytest.raises(ValidationError):
        item.scope = ObservationScope.PROJECT
    assert observation_fingerprint(item) == observation_fingerprint(
        item.model_copy(deep=True)
    )


def test_orphan_or_unvalidated_observation_rejected():
    with pytest.raises(LanguageLearningValidationError):
        validate_observations((_observation(),), (), (_intent(),))
    with pytest.raises(LanguageLearningValidationError):
        validate_observations(
            (_observation().model_copy(update={"validated_editor_correction": False}),),
            (_graph(),),
            (_intent(),),
        )


@pytest.mark.parametrize("counter", (0, 1, 3))
def test_confidence_is_deterministic_and_counter_evidence_reduces(counter):
    result = derive_confidence(4, 3, 3, 2, 0.9, counter)
    assert result == derive_confidence(4, 3, 3, 2, 0.9, counter)
    if counter:
        assert result.score < derive_confidence(4, 3, 3, 2, 0.9, 0).score


def test_confirmation_and_explicit_rule_strengthen_confidence():
    base = derive_confidence(1, 1, 1, 1, 0.5)
    assert derive_confidence(1, 1, 1, 1, 0.5, editor_confirmed=True).score > base.score
    assert derive_confidence(0, 0, 0, 0, 0, explicit_rule=True).score == 100


def test_candidate_eligibility_thresholds():
    aggregation = ObservationAggregation(
        aggregation_id="a",
        observation_identifiers=("o1", "o2", "o3"),
        grouping_dimensions=("connector",),
        support_count=3,
        episode_count=2,
        story_count=2,
        consistency=0.9,
    )
    assert candidate_eligible(aggregation, derive_confidence(4, 3, 3, 2, 1), 0.1)
    assert not candidate_eligible(
        aggregation.model_copy(update={"support_count": 1}),
        derive_confidence(4, 3, 3, 2, 1),
        0.1,
    )


def test_lifecycle_valid_and_invalid_transitions():
    assert (
        next_preference_status(PreferenceStatus.CANDIDATE, PreferenceStatus.EMERGING)
        == PreferenceStatus.EMERGING
    )
    with pytest.raises(ValueError):
        next_preference_status(PreferenceStatus.CANDIDATE, PreferenceStatus.ARCHIVED)


def test_readiness_precedence_and_manual_validation():
    values = {
        "session_id": "s",
        "engine_version": "1.0.0",
        "profile_version": "1.0.0",
        "observations_imported": (),
        "candidates_created": (),
        "preferences_promoted": (),
        "preferences_deprecated": (),
        "conflicts_detected": (),
        "profile_changes": (),
        "fingerprint": "0" * 64,
        "readiness": LearningReadiness.BLOCKED,
        "blocking_issues": ("broken lineage",),
    }
    probe = LearningSession(**values)
    values["fingerprint"] = semantic_fingerprint(
        probe.model_dump(exclude={"fingerprint"})
    )
    session = LearningSession(**values)
    assert validate_learning_session(session) is session
    with pytest.raises(LanguageLearningValidationError):
        validate_learning_session(
            session.model_copy(update={"readiness": LearningReadiness.READY})
        )


def test_no_forbidden_dependencies():
    import pastila_scout.editor.language_learning as package

    modules = " ".join(
        getattr(getattr(package, n), "__module__", "") for n in dir(package)
    )
    for item in ("openai", "httpx", "sqlite", "requests", "cli"):
        assert item not in modules


def test_every_artifact_has_identity_version_rendering_and_fingerprint():
    artifact = _intent()
    assert artifact.canonical_identifier == "intent-1"
    assert artifact.version == "1.0.0"
    assert artifact.render() == artifact.render()
    assert len(artifact.semantic_sha256) == 64
    assert artifact.validate_contract() is artifact


def test_rendering_excludes_timestamps_and_preserves_unicode():
    item = _observation().model_copy(
        update={"provenance_timestamp": "2026-07-28T12:00:00Z"}
    )
    rendered = item.render()
    assert "provenance_timestamp" not in rendered
    assert "correction-import-1" in rendered


def test_canonical_rendering_normalizes_unordered_references():
    first = CounterEvidence(
        counter_evidence_id="counter-1",
        conflicting_observation_identifiers=("observation-2", "observation-1"),
        contradiction_count=2,
    )
    second = first.model_copy(
        update={
            "conflicting_observation_identifiers": (
                "observation-1",
                "observation-2",
            )
        }
    )
    assert first.render() == second.render()
    assert first.semantic_sha256 == second.semantic_sha256


def test_graph_dependency_must_follow_declared_order():
    second = _operation().model_copy(update={"operation_id": "op-2"})
    values = _graph().model_dump()
    values.update(
        ordered_operations=(second, _operation()),
        dependency_edges=(
            LanguageEditEdge(
                predecessor_operation_id="op-1", successor_operation_id="op-2"
            ),
        ),
        graph_fingerprint="0" * 64,
    )
    graph = LanguageEditGraph(**values)
    graph = graph.model_copy(update={"graph_fingerprint": artifact_fingerprint(graph)})
    with pytest.raises(LanguageLearningValidationError, match="dependency"):
        validate_edit_graph(graph, (_intent(),))


def test_confidence_rejects_manual_score_and_accounts_for_conflict():
    base = derive_confidence(4, 3, 3, 2, 0.9)
    assert derive_confidence(4, 3, 3, 2, 0.9, conflicts=1).score < base.score
    with pytest.raises(LanguageLearningValidationError, match="deterministically"):
        validate_confidence(base.model_copy(update={"score": base.score - 1}))


def test_candidate_is_inactive_and_requires_evidence_when_eligible():
    values = {
        "candidate_id": "candidate-1",
        "origin_observations": ("observation-1",),
        "confidence": derive_confidence(4, 3, 3, 2, 0.9),
        "support": 4,
        "counter_support": 0,
        "affected_language_dimensions": ("connector",),
        "suggested_scope": ObservationScope.STORY,
        "review_required": False,
        "eligible": True,
    }
    with pytest.raises(LanguageLearningValidationError, match="requires evidence"):
        validate_candidate(LearningCandidate(**values), {"observation-1"})
    candidate = LearningCandidate(
        **values, supporting_evidence_references=("evidence-1",)
    )
    assert validate_candidate(candidate, {"observation-1"}) is candidate
    with pytest.raises(LanguageLearningValidationError, match="inactive"):
        validate_candidate(
            candidate.model_copy(update={"inactive": False}), {"observation-1"}
        )


def test_editor_authority_controls_deprecated_preference_restoration():
    with pytest.raises(ValueError):
        next_preference_status(
            PreferenceStatus.DEPRECATED, PreferenceStatus.ESTABLISHED
        )
    assert (
        next_preference_status(
            PreferenceStatus.DEPRECATED,
            PreferenceStatus.ESTABLISHED,
            editor_authorized=True,
        )
        == PreferenceStatus.ESTABLISHED
    )


def test_decay_is_deterministic_and_explicit_rules_do_not_decay():
    values = {
        "first_observation": "o1",
        "last_observation": "o2",
        "last_confirmation": None,
        "observation_count": 2,
        "episode_count": 2,
        "story_count": 2,
        "periods_since_confirmation": 12,
        "consistency": 0.7,
        "counter_evidence_ratio": 0.2,
    }
    decay = derive_decay(**values)
    assert decay == derive_decay(**values)
    assert decay.activity_status == DecayState.WEAKENING
    assert decay.confidence_adjustment < 0
    explicit = derive_decay(**values, explicit_rule=True)
    assert explicit.activity_status == DecayState.STABLE
    assert explicit.confidence_adjustment == 0
    assert validate_decay(explicit) is explicit


def test_conflict_and_supersession_preserve_complete_lineage():
    ids = {"old", "new"}
    conflict = PreferenceConflict(
        conflict_id="conflict-1",
        conflict_type=ConflictType.SUPERSEDED,
        preference_identifiers=("old", "new"),
        evidence_references=("evidence-1",),
        explanation_references=("explanation-1",),
        requires_editor_review=False,
        resolved=True,
        predecessor_preference_id="old",
        successor_preference_id="new",
        confidence_impact=-10,
        resolution_status="superseded",
    )
    assert validate_conflict(conflict, ids) is conflict
    supersession = PreferenceSupersession(
        supersession_id="supersession-1",
        old_preference_id="old",
        new_preference_id="new",
        reason_reference="conflict-1",
        editor_confirmation=True,
        support_evidence=("evidence-1",),
    )
    assert validate_supersession(supersession, ids) is supersession


def test_profile_visibility_validation_and_guidance_boundary():
    preference = _preference()
    profile = _profile(preference)
    assert validate_profile(profile, {"observation-1"}) is profile
    projection = project_guidance(profile, "projection-1")
    assert validate_guidance_projection(projection, {"preference-1"}) is projection
    assert projection.guidance[0].contains_language is False
    archived = _preference(PreferenceStatus.ARCHIVED, "archived-1")
    values = profile.model_dump()
    values.update(
        active_preferences=(),
        archived_preferences=(archived,),
        established_count=0,
        profile_fingerprint="0" * 64,
    )
    evolved = EditorialLanguageProfile(**values)
    evolved = evolved.model_copy(
        update={"profile_fingerprint": artifact_fingerprint(evolved)}
    )
    assert validate_profile(evolved, {"observation-1"}).archived_preferences == (
        archived,
    )


def test_upstream_compatibility_and_readiness_propagation():
    dependency = UpstreamCompatibilityReference(
        module_id="romanian-conversational-engine",
        module_version="1.0.0",
        semantic_fingerprint="a" * 64,
        readiness=LearningReadiness.BLOCKED,
    )
    compatibility = LearningCompatibilitySnapshot(
        snapshot_id="compatibility-1", dependencies=(dependency,)
    )
    assert validate_compatibility(compatibility) is compatibility
    values = {
        "session_id": "session-compatibility",
        "engine_version": "1.0.0",
        "profile_version": "1.0.0",
        "observations_imported": (),
        "candidates_created": (),
        "preferences_promoted": (),
        "preferences_deprecated": (),
        "conflicts_detected": (),
        "profile_changes": (),
        "fingerprint": "0" * 64,
        "readiness": LearningReadiness.BLOCKED,
        "compatibility": compatibility,
    }
    probe = LearningSession(**values)
    values["fingerprint"] = artifact_fingerprint(probe)
    session = LearningSession(**values)
    assert validate_learning_session(session) is session
    with pytest.raises(LanguageLearningValidationError, match="canonical mutation"):
        validate_compatibility(
            compatibility.model_copy(update={"canonical_mutation": True})
        )


@pytest.mark.parametrize(
    ("dependency_state", "expected"),
    (
        (
            LearningReadiness.REQUIRES_EDITOR_REVIEW,
            LearningReadiness.REQUIRES_EDITOR_REVIEW,
        ),
        (
            LearningReadiness.READY_WITH_ADVISORIES,
            LearningReadiness.READY_WITH_ADVISORIES,
        ),
    ),
)
def test_upstream_nonblocking_readiness_propagates(dependency_state, expected):
    compatibility = LearningCompatibilitySnapshot(
        snapshot_id="compatibility-readiness",
        dependencies=(
            UpstreamCompatibilityReference(
                module_id="story-architecture",
                module_version="1.0.0",
                semantic_fingerprint="b" * 64,
                readiness=dependency_state,
            ),
        ),
    )
    values = {
        "session_id": "session-readiness",
        "engine_version": "1.0.0",
        "profile_version": "1.0.0",
        "observations_imported": (),
        "candidates_created": (),
        "preferences_promoted": (),
        "preferences_deprecated": (),
        "conflicts_detected": (),
        "profile_changes": (),
        "fingerprint": "0" * 64,
        "readiness": expected,
        "compatibility": compatibility,
    }
    probe = LearningSession(**values)
    values["fingerprint"] = artifact_fingerprint(probe)
    session = LearningSession(**values)
    assert determine_learning_readiness(session) == expected
    assert validate_learning_session(session) is session


def test_evidence_append_is_non_mutating_and_preserves_history():
    old = _preference().evidence_chain
    old_fingerprint = evidence_fingerprint(old)
    new = append_evidence(
        old,
        observation_id="observation-2",
        episode_id="episode-2",
        story_id="story-2",
        edit_graph_id="graph-2",
    )
    assert old.observation_identifiers == ("observation-1",)
    assert evidence_fingerprint(old) == old_fingerprint
    assert new.observation_identifiers[:1] == old.observation_identifiers
    assert new.chronological_references[-1] == "observation-2"
    assert validate_evidence_chain(new, {"observation-1", "observation-2"}) is new


def test_incomplete_evidence_lineage_and_count_mismatches_are_rejected():
    chain = _preference().evidence_chain.model_copy(
        update={"episode_identifiers": ("episode-1", "episode-orphan")}
    )
    with pytest.raises(LanguageLearningValidationError, match="incomplete"):
        validate_evidence_chain(chain, {"observation-1"})
    evidence = LearningEvidence(
        evidence_id="learning-evidence-1",
        observation_references=("observation-1",),
        episode_references=("episode-1",),
        story_references=("story-1",),
        edit_graph_references=("graph-1",),
        editor_confirmations=(),
        explicit_rules=(),
        counter_evidence_references=(),
        support_count=2,
        contradiction_count=0,
        confidence_contribution=10,
    )
    with pytest.raises(LanguageLearningValidationError, match="support count"):
        validate_learning_evidence(evidence, {"observation-1"})


def test_equivalent_history_builds_identical_profile_and_fingerprint():
    preference = _preference()
    kwargs = {
        "profile_id": "profile-built",
        "profile_version": "1.0.0",
        "editor_identity": "editor-in-chief",
        "observations": (_observation(),),
        "conflicts": (),
        "explanation": _explanation(),
    }
    first = build_profile(preferences=(preference,), **kwargs)
    second = build_profile(preferences=(preference.model_copy(deep=True),), **kwargs)
    assert first == second
    assert first.profile_fingerprint == second.profile_fingerprint
    assert validate_profile(first, {"observation-1"}) is first
