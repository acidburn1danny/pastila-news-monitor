"""Focused Story Architecture contracts, validation, and determinism tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pastila_scout.editor.audience import (
    DEFAULT_AUDIENCE_MODEL,
    AudienceAssessment,
    AudienceCalibration,
    AudienceEmotion,
    AudienceEmotionalCalibration,
    AudienceReadiness,
    ComprehensionAssessment,
    ContextBudget,
    ContextBudgetLevel,
    PriorKnowledgeLevel,
    assessment_fingerprint,
)
from pastila_scout.editor.decision import (
    CoreElement,
    DecisionConfidence,
    DecisionStage,
    EditorialAction,
    EditorialCore,
    EditorialDecision,
    EditorialDecisionPlan,
    EditorialMaterial,
    FactImportance,
    FactualStatus,
    MaterialType,
    ProductionReadiness,
    decision_plan_fingerprint,
    source_material_fingerprint,
)
from pastila_scout.editor.persona import DEFAULT_EDITORIAL_PERSONA
from pastila_scout.editor.story import (
    DEFAULT_STORY_ARCHITECTURE,
    STAGE_RANK,
    AudienceTakeaway,
    NarrativeFunction,
    NarrativeSpine,
    NarrativeStage,
    OpeningStrategy,
    PayoffType,
    StoryArchitecturePlan,
    StoryArchitectureReadiness,
    StoryArchitectureValidationError,
    StoryOpeningPlan,
    StoryPatternSelection,
    StoryPayoffPlan,
    StoryTransition,
    StoryUnit,
    StoryUnitType,
    TransitionRelationshipType,
    architecture_fingerprint,
    pattern_collection_fingerprint,
    render_story_architecture,
    render_story_plan,
    story_plan_fingerprint,
    unit_collection_fingerprint,
    validate_story_architecture,
    validate_story_plan,
)
from pastila_scout.editor.voice import DEFAULT_SATIRICAL_VOICE, TonalSeriousness


def _decision_plan(**changes: object) -> EditorialDecisionPlan:
    material = EditorialMaterial(
        material_id="m1",
        source_reference="source-a",
        material_type=MaterialType.FACT,
        content="Instituția a anunțat măsura miercuri.",
        factual_status=FactualStatus.VERIFIED_FACT,
        chronology_position=1,
    )
    decision = EditorialDecision(
        decision_id="d1",
        stage=DecisionStage.EDITORIAL_CORE,
        rank=1,
        material_ids=("m1",),
        classification=FactImportance.INDISPENSABLE,
        action=EditorialAction.PRESERVE,
        rationale="Preserve the factual core.",
        evidence=("m1",),
        principle_ids=("truth-before-performance",),
        confidence=DecisionConfidence.HIGH,
        consequence_if_ignored="The story would lose its factual core.",
    )
    core_element = CoreElement(
        statement="Măsura a fost anunțată.", material_ids=("m1",)
    )
    core = EditorialCore(
        what_happened=core_element,
        involved_parties=core_element,
        why_it_matters=core_element,
        consequence=core_element,
        central_tension=core_element,
        factual_boundaries=(core_element,),
    )
    values = {
        "plan_id": "decision-plan-1",
        "version": "1.0.0",
        "persona_id": DEFAULT_EDITORIAL_PERSONA.persona_id,
        "persona_version": DEFAULT_EDITORIAL_PERSONA.version,
        "philosophy_id": DEFAULT_EDITORIAL_PERSONA.philosophy.philosophy_id,
        "philosophy_version": DEFAULT_EDITORIAL_PERSONA.philosophy.version,
        "source_material_fingerprint": source_material_fingerprint((material,)),
        "source_material": (material,),
        "editorial_core": core,
        "decisions": (decision,),
        "requires_editor_in_chief_review": False,
        "production_readiness": ProductionReadiness.READY,
        "summary": "Evidence-linked decision plan.",
    }
    values.update(changes)
    return EditorialDecisionPlan(**values)


def _audience(plan: EditorialDecisionPlan, **changes: object) -> AudienceAssessment:
    context = ContextBudget(
        budget_level=ContextBudgetLevel.MODERATE,
        justification="Enough context for the current event.",
        required_background=("Institution role.",),
        optional_background=(),
        prohibited_detours=("Unrelated history.",),
        compression_candidates=(),
        indispensable_explanations=("Why the measure matters.",),
        review_conditions=(),
        required_context_material_ids=("m1",),
    )
    emotion = AudienceEmotionalCalibration(
        primary_intended_response=AudienceEmotion.INFORMED,
        secondary_intended_responses=(AudienceEmotion.CURIOUS,),
        responses_to_avoid=(),
        factual_basis_material_ids=("m1",),
        emotional_ceiling=AudienceEmotion.CONCERNED,
        tonal_seriousness=TonalSeriousness.MIXED,
        tonal_constraints=("Remain evidence-grounded.",),
        sensitivity_conditions=(),
        editor_review_conditions=(),
    )
    calibration = AudienceCalibration(
        audience_id=DEFAULT_AUDIENCE_MODEL.audience_id,
        audience_version=DEFAULT_AUDIENCE_MODEL.version,
        prior_knowledge=PriorKnowledgeLevel.GENERAL,
        context_budget=context,
        cognitive_profile=DEFAULT_AUDIENCE_MODEL.cognitive_profile,
        intended_emotional_response=emotion,
        voice_dimensions=DEFAULT_SATIRICAL_VOICE.calibration.dimensions,
        attention_priorities=("early relevance",),
        trust_safeguards=("visible attribution",),
        fatigue_constraints=("avoid repetition",),
    )
    values = {
        "assessment_id": "audience-assessment-1",
        "version": "1.0.0",
        "audience_id": DEFAULT_AUDIENCE_MODEL.audience_id,
        "audience_version": DEFAULT_AUDIENCE_MODEL.version,
        "decision_plan_id": plan.plan_id,
        "source_material_fingerprint": plan.source_material_fingerprint,
        "calibration": calibration,
        "comprehension_assessment": ComprehensionAssessment(
            summary="The core is clear."
        ),
        "context_assessment": context,
        "emotional_calibration": emotion,
        "requires_editor_in_chief_review": False,
        "audience_readiness": AudienceReadiness.READY,
        "summary": "Audience assessment.",
    }
    values.update(changes)
    return AudienceAssessment(**values)


def _unit(
    unit_id: str, stage: NarrativeStage, rank: int, **changes: object
) -> StoryUnit:
    values = {
        "unit_id": unit_id,
        "stage": stage,
        "rank": rank,
        "source_material_ids": ("m1",),
        "editorial_decision_ids": ("d1",),
        "editorial_core_element_ids": ("what_happened",),
        "unit_type": StoryUnitType.OPENING_FACT if rank == 1 else StoryUnitType.PAYOFF,
        "primary_function": (
            NarrativeFunction.ESTABLISH_RELEVANCE
            if rank == 1
            else NarrativeFunction.DELIVER_PAYOFF
        ),
        "factual_status_summary": "verified_fact",
        "importance": FactImportance.INDISPENSABLE,
        "prerequisite_unit_ids": () if rank == 1 else ("u1",),
        "can_be_compressed": False,
        "can_be_combined": False,
        "can_be_removed": False,
        "requires_verbatim_evidence": False,
        "requires_attribution": False,
        "requires_tonal_restraint": False,
        "requires_editor_in_chief_review": False,
    }
    values.update(changes)
    return StoryUnit(**values)


def _plan(
    decision: EditorialDecisionPlan, audience: AudienceAssessment, **changes: object
) -> StoryArchitecturePlan:
    u1 = _unit("u1", NarrativeStage.OPENING, 1)
    u2 = _unit("u2", NarrativeStage.PAYOFF, 2)
    selection = StoryPatternSelection(
        selection_id="selection-1",
        selected_pattern_id="fact-consequence-contradiction-payoff",
        decision_plan_id=decision.plan_id,
        audience_assessment_id=audience.assessment_id,
        selection_rationale="The event itself establishes relevance.",
        supporting_core_element_ids=("what_happened",),
        supporting_decision_ids=("d1",),
        audience_reasons=("Early relevance.",),
        tonal_reasons=("Mixed seriousness.",),
        rejected_pattern_ids=(),
        rejection_reasons=(),
        confidence=DecisionConfidence.HIGH,
    )
    values = {
        "architecture_id": DEFAULT_STORY_ARCHITECTURE.architecture_id,
        "version": DEFAULT_STORY_ARCHITECTURE.version,
        "persona_id": DEFAULT_EDITORIAL_PERSONA.persona_id,
        "persona_version": DEFAULT_EDITORIAL_PERSONA.version,
        "philosophy_id": DEFAULT_EDITORIAL_PERSONA.philosophy.philosophy_id,
        "philosophy_version": DEFAULT_EDITORIAL_PERSONA.philosophy.version,
        "voice_id": DEFAULT_SATIRICAL_VOICE.voice_id,
        "voice_version": DEFAULT_SATIRICAL_VOICE.version,
        "audience_id": DEFAULT_AUDIENCE_MODEL.audience_id,
        "audience_version": DEFAULT_AUDIENCE_MODEL.version,
        "decision_plan_id": decision.plan_id,
        "audience_assessment_id": audience.assessment_id,
        "source_material_fingerprint": decision.source_material_fingerprint,
        "decision_plan_fingerprint": decision_plan_fingerprint(decision),
        "audience_assessment_fingerprint": assessment_fingerprint(audience),
        "selected_pattern": selection,
        "primary_narrative_spine": NarrativeSpine(
            spine_id="spine-1",
            editorial_core_element_ids=("what_happened",),
            ordered_unit_ids=("u1", "u2"),
            central_event="m1",
            central_relevance="why_it_matters",
            central_contradiction_or_tension="central_tension",
            consequence_focus="consequence",
            intended_progression=(
                NarrativeFunction.ESTABLISH_RELEVANCE,
                NarrativeFunction.DELIVER_PAYOFF,
            ),
            excluded_competing_angles=(),
            factual_boundaries=("factual_boundaries",),
            confidence=DecisionConfidence.HIGH,
        ),
        "secondary_angles": (),
        "opening_plan": StoryOpeningPlan(
            strategy=OpeningStrategy.EVENT_FIRST,
            supported_unit_ids=("u1",),
            reason_for_selection="The verified event is immediately relevant.",
            immediate_audience_need="Know what happened.",
            required_context_after_opening=(),
            risks=(),
            tonal_limit=TonalSeriousness.MIXED,
            prohibited_opening_interpretations=("No unsupported motive.",),
            requires_editor_in_chief_review=False,
        ),
        "story_units": (u1, u2),
        "transitions": (
            StoryTransition(
                transition_id="t1",
                from_unit_id="u1",
                to_unit_id="u2",
                relationship_type=TransitionRelationshipType.SETUP_TO_PAYOFF,
                transition_function="Resolve established setup.",
                required_information_state=("u1",),
                tonal_shift="none",
                risk_if_missing="Payoff becomes detached.",
                requires_editor_in_chief_review=False,
            ),
        ),
        "context_placements": (),
        "consequence_plans": (),
        "satire_placements": (),
        "payoff_plan": StoryPayoffPlan(
            payoff_id="payoff-1",
            payoff_type=PayoffType.FACTUAL_REVELATION,
            supporting_unit_ids=("u2",),
            setup_unit_ids=("u1",),
            editorial_function="Resolve setup.",
            audience_takeaway="Recognize the verified consequence.",
            factual_boundary="No unsupported motive.",
            tonal_limit=TonalSeriousness.MIXED,
            unresolved_elements=(),
            closure_dependency="u1",
            requires_editor_in_chief_review=False,
        ),
        "audience_takeaway": AudienceTakeaway(
            takeaway_id="takeaway-1",
            primary_recognition="The measure has a verified public consequence.",
            supporting_core_element_ids=("what_happened",),
            supporting_unit_ids=("u1", "u2"),
            factual_basis=("m1",),
            emotional_register="informed",
            interpretive_limit="No motive inferred.",
            prohibited_overstatement="Do not universalize.",
            confidence=DecisionConfidence.HIGH,
        ),
        "architecture_risks": (),
        "unresolved_dependencies": (),
        "blocking_issues": (),
        "advisory_issues": (),
        "requires_editor_in_chief_review": False,
        "readiness": StoryArchitectureReadiness.READY,
        "summary": "Reference-only narrative plan.",
    }
    values.update(changes)
    return StoryArchitecturePlan(**values)


def _validated() -> (
    tuple[StoryArchitecturePlan, EditorialDecisionPlan, AudienceAssessment]
):
    decision = _decision_plan()
    audience = _audience(decision)
    plan = _plan(decision, audience)
    validate_story_plan(
        plan,
        DEFAULT_STORY_ARCHITECTURE,
        decision,
        audience,
        DEFAULT_AUDIENCE_MODEL,
        DEFAULT_SATIRICAL_VOICE,
    )
    return plan, decision, audience


def test_canonical_architecture_and_contracts_validate_and_are_immutable():
    assert (
        validate_story_architecture(DEFAULT_STORY_ARCHITECTURE)
        is DEFAULT_STORY_ARCHITECTURE
    )
    assert len(DEFAULT_STORY_ARCHITECTURE.principles) == 20
    assert len(DEFAULT_STORY_ARCHITECTURE.patterns) == 8
    with pytest.raises(ValidationError):
        DEFAULT_STORY_ARCHITECTURE.title = "changed"  # type: ignore[misc]


def test_canonical_identifiers_and_order_are_unique_and_complete():
    principles = DEFAULT_STORY_ARCHITECTURE.principles
    patterns = DEFAULT_STORY_ARCHITECTURE.patterns
    assert len({item.principle_id for item in principles}) == len(principles)
    assert [item.order for item in principles] == list(range(1, 21))
    assert len({item.pattern_id for item in patterns}) == len(patterns)
    assert tuple(DEFAULT_STORY_ARCHITECTURE.stage_order) == tuple(NarrativeStage)
    assert list(STAGE_RANK.values()) == list(range(1, 12))


def test_invalid_semver_and_stage_order_are_rejected():
    for architecture in (
        DEFAULT_STORY_ARCHITECTURE.model_copy(update={"version": "v1"}),
        DEFAULT_STORY_ARCHITECTURE.model_copy(
            update={"stage_order": tuple(reversed(tuple(NarrativeStage)))}
        ),
    ):
        with pytest.raises(StoryArchitectureValidationError):
            validate_story_architecture(architecture)


def test_clean_story_plan_validates_and_is_ready():
    plan, _, _ = _validated()
    assert plan.readiness == StoryArchitectureReadiness.READY


@pytest.mark.parametrize(
    ("unit_change", "match"),
    [
        ({"source_material_ids": ("missing",)}, "unknown material"),
        ({"editorial_decision_ids": ("missing",)}, "unknown decision"),
        ({"editorial_core_element_ids": ("missing",)}, "unknown core element"),
        ({"satirical_opportunity_ids": ("missing",)}, "unknown Satirical Opportunity"),
        ({"prerequisite_unit_ids": ("missing",)}, "unknown prerequisite"),
    ],
)
def test_unknown_story_unit_references_are_rejected(
    unit_change: dict[str, object], match: str
):
    plan, decision, audience = _validated()
    bad = plan.model_copy(
        update={
            "story_units": (
                _unit("u1", NarrativeStage.OPENING, 1, **unit_change),
                plan.story_units[1],
            )
        }
    )
    with pytest.raises(StoryArchitectureValidationError, match=match):
        validate_story_plan(
            bad,
            DEFAULT_STORY_ARCHITECTURE,
            decision,
            audience,
            DEFAULT_AUDIENCE_MODEL,
            DEFAULT_SATIRICAL_VOICE,
        )


def test_duplicate_units_cycle_and_bad_spine_order_are_rejected():
    plan, decision, audience = _validated()
    cases = (
        plan.model_copy(
            update={"story_units": (plan.story_units[0], plan.story_units[0])}
        ),
        plan.model_copy(
            update={
                "story_units": (
                    plan.story_units[0].model_copy(
                        update={"prerequisite_unit_ids": ("u2",)}
                    ),
                    plan.story_units[1],
                )
            }
        ),
        plan.model_copy(
            update={
                "primary_narrative_spine": plan.primary_narrative_spine.model_copy(
                    update={"ordered_unit_ids": ("u2", "u1")}
                )
            }
        ),
    )
    for case in cases:
        with pytest.raises(StoryArchitectureValidationError):
            validate_story_plan(
                case,
                DEFAULT_STORY_ARCHITECTURE,
                decision,
                audience,
                DEFAULT_AUDIENCE_MODEL,
                DEFAULT_SATIRICAL_VOICE,
            )


def test_opening_core_payoff_transition_and_takeaway_safeguards():
    plan, decision, audience = _validated()
    cases = (
        plan.model_copy(
            update={
                "opening_plan": plan.opening_plan.model_copy(
                    update={"supported_unit_ids": ("missing",)}
                )
            }
        ),
        plan.model_copy(
            update={
                "payoff_plan": plan.payoff_plan.model_copy(
                    update={"setup_unit_ids": ("u2",)}
                )
            }
        ),
        plan.model_copy(
            update={
                "transitions": (
                    plan.transitions[0].model_copy(
                        update={"relationship_type": TransitionRelationshipType.CAUSAL}
                    ),
                )
            }
        ),
        plan.model_copy(
            update={
                "audience_takeaway": plan.audience_takeaway.model_copy(
                    update={"commands_political_opinion": True}
                )
            }
        ),
    )
    for case in cases:
        with pytest.raises(StoryArchitectureValidationError):
            validate_story_plan(
                case,
                DEFAULT_STORY_ARCHITECTURE,
                decision,
                audience,
                DEFAULT_AUDIENCE_MODEL,
                DEFAULT_SATIRICAL_VOICE,
            )


def test_upstream_fingerprints_and_mutation_flags_are_enforced():
    plan, decision, audience = _validated()
    for update in (
        {"decision_plan_fingerprint": "0" * 64},
        {"audience_assessment_fingerprint": "0" * 64},
        {"changes_editorial_decisions": True},
        {"contains_generated_joke": True},
    ):
        with pytest.raises(StoryArchitectureValidationError):
            validate_story_plan(
                plan.model_copy(update=update),
                DEFAULT_STORY_ARCHITECTURE,
                decision,
                audience,
                DEFAULT_AUDIENCE_MODEL,
                DEFAULT_SATIRICAL_VOICE,
            )


def test_readiness_propagates_blockers_review_and_advisories():
    plan, decision, audience = _validated()
    blocked = plan.model_copy(
        update={
            "blocking_issues": ("missing setup",),
            "readiness": StoryArchitectureReadiness.BLOCKED,
        }
    )
    review = plan.model_copy(
        update={
            "requires_editor_in_chief_review": True,
            "readiness": StoryArchitectureReadiness.REQUIRES_EDITOR_REVIEW,
        }
    )
    advisory = plan.model_copy(
        update={
            "advisory_issues": ("optional compression",),
            "readiness": StoryArchitectureReadiness.READY_WITH_ADVISORIES,
        }
    )
    for candidate in (blocked, review, advisory):
        assert (
            validate_story_plan(
                candidate,
                DEFAULT_STORY_ARCHITECTURE,
                decision,
                audience,
                DEFAULT_AUDIENCE_MODEL,
                DEFAULT_SATIRICAL_VOICE,
            )
            is candidate
        )
    with pytest.raises(StoryArchitectureValidationError, match="readiness"):
        validate_story_plan(
            blocked.model_copy(update={"readiness": StoryArchitectureReadiness.READY}),
            DEFAULT_STORY_ARCHITECTURE,
            decision,
            audience,
            DEFAULT_AUDIENCE_MODEL,
            DEFAULT_SATIRICAL_VOICE,
        )


def test_rendering_is_deterministic_complete_utf8_and_reference_only():
    plan, decision, audience = _validated()
    canonical = render_story_architecture(DEFAULT_STORY_ARCHITECTURE)
    rendered = render_story_plan(
        plan,
        DEFAULT_STORY_ARCHITECTURE,
        decision,
        audience,
        DEFAULT_AUDIENCE_MODEL,
        DEFAULT_SATIRICAL_VOICE,
    )
    assert canonical == render_story_architecture(DEFAULT_STORY_ARCHITECTURE)
    assert rendered == render_story_plan(
        plan,
        DEFAULT_STORY_ARCHITECTURE,
        decision,
        audience,
        DEFAULT_AUDIENCE_MODEL,
        DEFAULT_SATIRICAL_VOICE,
    )
    assert (
        "Canonical Principles" in canonical and "Editor-in-Chief Authority" in canonical
    )
    assert "Ordered Story Units" in rendered and "m1" in rendered and "d1" in rendered
    assert (
        "generated hook" not in rendered.lower()
        and "punchline text" not in rendered.lower()
    )
    rendered.encode("utf-8")


def test_semantic_fingerprints_preserve_order_significance_and_normalize_sets():
    plan, _, _ = _validated()
    assert architecture_fingerprint(
        DEFAULT_STORY_ARCHITECTURE
    ) == architecture_fingerprint(DEFAULT_STORY_ARCHITECTURE)
    assert story_plan_fingerprint(plan) == story_plan_fingerprint(
        plan.model_copy(deep=True)
    )
    reordered_evidence = plan.story_units[0].model_copy(
        update={
            "source_material_ids": tuple(
                reversed(plan.story_units[0].source_material_ids)
            )
        }
    )
    assert unit_collection_fingerprint(plan.story_units) == unit_collection_fingerprint(
        (reordered_evidence, plan.story_units[1])
    )
    reversed_spine = plan.model_copy(
        update={
            "primary_narrative_spine": plan.primary_narrative_spine.model_copy(
                update={"ordered_unit_ids": ("u2", "u1")}
            )
        }
    )
    reversed_transition = plan.model_copy(
        update={
            "transitions": (
                plan.transitions[0].model_copy(
                    update={"from_unit_id": "u2", "to_unit_id": "u1"}
                ),
            )
        }
    )
    assert story_plan_fingerprint(plan) != story_plan_fingerprint(reversed_spine)
    assert story_plan_fingerprint(plan) != story_plan_fingerprint(reversed_transition)
    changed_pattern = DEFAULT_STORY_ARCHITECTURE.patterns[0].model_copy(
        update={"description": "Changed semantics."}
    )
    assert pattern_collection_fingerprint(
        DEFAULT_STORY_ARCHITECTURE.patterns
    ) != pattern_collection_fingerprint(
        (changed_pattern, *DEFAULT_STORY_ARCHITECTURE.patterns[1:])
    )


def test_story_package_has_no_forbidden_runtime_dependencies():
    from pastila_scout.editor import story

    source = " ".join(
        getattr(story, name).__module__
        for name in story.__all__
        if hasattr(getattr(story, name), "__module__")
    )
    for forbidden in ("openai", "httpx", "sqlite", "cli", "benchmark"):
        assert forbidden not in source
