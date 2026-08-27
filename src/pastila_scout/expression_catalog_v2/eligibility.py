"""Deterministic eligibility for owner-approved expression scopes."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from pastila_scout.voice_eligibility_v2 import (
    ProgramCandidateV1,
    VoiceEligibilityResultV1,
    VoiceRepetitionSnapshotV1,
)
from pastila_scout.voice_fact_atoms_v2 import AuthorityClass, VoiceFactAtomBundleV1
from pastila_scout.voice_fact_atoms_v2.persistence import (
    bundle_payload_identity,
    canonical_identity,
)

from .eligibility_models import (
    CommentaryRelationBinding,
    CommentaryRelationBindingV2,
    CommentaryRelationshipV1,
    ExpressionCandidateV1,
    ExpressionEligibilityOutcomeV1,
    ExpressionEligibilityResultV1,
    ExpressionEligibilityStatusV1,
    ExpressionOwnerSelectionReceiptV1,
)
from .models import (
    AdjudicationStatusV2,
    ExpressionCatalogOverlayV2,
    RenderabilityStatusV2,
)


class ExpressionEligibilityIntegrityError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExpressionScopeSpecV1:
    expression_id: str
    family_identity: str
    relationship: CommentaryRelationshipV1
    required_roles: tuple[str, ...]
    required_constraint_codes: tuple[str, ...]
    cooldown_episodes: int
    background_allowed_roles: tuple[str, ...] = ()
    pool_identity: str | None = None


def _spec(
    expression_id,
    family,
    relationship,
    roles,
    constraints,
    cooldown,
    background_allowed_roles=(),
    pool_identity=None,
):
    return ExpressionScopeSpecV1(
        expression_id,
        family,
        relationship,
        tuple(roles),
        tuple(sorted(constraints)),
        cooldown,
        tuple(background_allowed_roles),
        pool_identity,
    )


SCOPE_SPECS_V1 = (
    _spec(
        "ro-expression-v1:2e5417acdb78ee504d4b",
        "EXPR_FAMILY_DELAYED_ACTION_AFTER_OUTCOME_V1",
        CommentaryRelationshipV1.DELAYED_ACTION_AFTER_OUTCOME,
        ("problem_outcome", "later_intervention", "chronology"),
        (
            "action_is_meaningfully_post_outcome",
            "not_later_reporting_of_earlier_action",
            "problem_is_not_ongoing",
            "same_event_chronology",
        ),
        2,
    ),
    _spec(
        "ro-expression-v1:746823d11b1460dac265",
        "EXPR_FAMILY_BATE_APA_N_PIUA_V1",
        CommentaryRelationshipV1.REPETITION_WITHOUT_PROGRESS,
        ("repeated_action_first", "repeated_action_later", "lack_of_progress"),
        (
            "actions_are_materially_same",
            "not_multiple_source_reporting",
            "outcome_is_not_merely_pending",
            "zero_material_progress",
        ),
        5,
    ),
    _spec(
        "ro-expression-v1:41136a4e8443b1239535",
        "EXPR_FAMILY_CASTRAVETI_GRADINARULUI_V1",
        CommentaryRelationshipV1.EXPERTISE_ROLE_REVERSAL,
        ("domain_expertise", "same_domain_attempted_action", "target_actor"),
        (
            "expertise_is_explicitly_supported",
            "not_ordinary_disagreement",
            "not_unsupported_deception",
            "same_domain",
            "same_target_actor",
            "target_was_not_receiving_new_information",
        ),
        5,
    ),
    _spec(
        "ro-expression-v1:b37979ce96f5d03deda3",
        "EXPR_FAMILY_COADA_DE_PESTE_V1",
        CommentaryRelationshipV1.UNRESOLVED_OUTCOME,
        ("terminated_or_abandoned_process", "unresolved_result"),
        (
            "no_material_partial_result",
            "not_active_investigation",
            "not_incomplete_local_knowledge",
            "not_pending_appeal",
            "not_temporary_suspension",
            "process_is_terminal_or_abandoned",
        ),
        5,
    ),
    _spec(
        "ro-expression-v1:2aaa6fa3011f6a2ea8f0",
        "EXPR_FAMILY_BATISTA_PE_TAMBAL_V1",
        CommentaryRelationshipV1.CONCEALMENT_OR_SUPPRESSION,
        ("actor", "deliberate_concealment_or_suppression", "concealed_subject"),
        (
            "actor_attribution_is_explicit",
            "conduct_is_established_not_alleged",
            "deliberate_intent_is_supported",
            "not_confidentiality",
            "not_missing_information",
            "not_refusal_to_comment",
            "not_silence",
        ),
        5,
    ),
    _spec(
        "ro-expression-v1:2b65e40f861c797989a7",
        "EXPR_FAMILY_INTOARCERE_CA_LA_PLOIESTI_V1",
        CommentaryRelationshipV1.POSITION_OR_VERSION_REVERSAL,
        ("actor", "earlier_position", "later_position", "chronology"),
        (
            "material_reversal",
            "not_changed_legal_or_procedural_status",
            "not_clarification",
            "not_correction_based_on_new_evidence",
            "not_source_disagreement",
            "same_actor",
        ),
        5,
    ),
    _spec(
        "ro-expression-v1:8c165e82d1f7002717ed",
        "EXPR_FAMILY_CALUL_DE_DAR_V1",
        CommentaryRelationshipV1.GIFT_OR_FREE_ADVANTAGE,
        ("gift_or_free_advantage", "recipient", "funding_status"),
        (
            "funding_source_is_certain",
            "genuinely_free_unconditional_advantage",
            "not_alleged_bribe_or_inducement",
            "not_conditional_benefit",
            "not_grant_or_subsidy",
            "not_procurement_or_public_expenditure",
            "not_sponsorship",
        ),
        5,
    ),
)

FIRST_TWELVE_SCOPE_SPECS_V1 = (
    _spec(
        "ro-expression-v1:291dc70a3335d6c5a326",
        "EXPRESSION_FAMILY_SUPPORTED_STRENGTHENING_V1",
        CommentaryRelationshipV1.CONDUCT_STRENGTHENS_POSITION_OR_PROCESS,
        (
            "contributing_event",
            "existing_recipient_position_or_process",
            "supported_strengthening_relation",
            "actor_identity",
            "recipient_identity",
        ),
        (
            "actor_and_recipient_identity_preserved",
            "existing_recipient_precedes_or_exists_independently",
            "future_effect_not_inferred",
            "intention_coordination_endorsement_not_inferred",
            "material_directional_relationship_supported",
            "not_hypothetical_beneficiary",
            "not_thematic_similarity",
            "same_supported_context_or_explicit_relationship",
        ),
        5,
        ("existing_recipient_position_or_process",),
    ),
    _spec(
        "ro-expression-v1:499847b2e206c615cb3f",
        "EXPRESSION_FAMILY_DIRECT_DISCOVERY_OR_CAUGHT_WITH_EVIDENCE_V1",
        CommentaryRelationshipV1.DIRECT_DISCOVERY_OF_CONDUCT,
        ("actor", "conduct", "discovery", "direct_evidence", "discovery_timing"),
        (
            "actor_conduct_and_evidence_match",
            "allegation_status_preserved",
            "direct_evidence_materially_links_conduct",
            "no_broader_misconduct_or_intent_inferred",
            "not_arrest_investigation_or_allegation_alone",
            "not_circumstantial_association",
            "not_presence_at_scene_alone",
            "possession_link_is_established",
        ),
        5,
    ),
    _spec(
        "ro-expression-v1:5d8d914aa7485bd00357",
        "EXPRESSION_FAMILY_EXPLICIT_HIGH_CONFIDENCE_GUARANTEE_V1",
        CommentaryRelationshipV1.EXPLICIT_HIGH_CONFIDENCE_GUARANTEE,
        (
            "guarantor",
            "guaranteed_proposition",
            "confidence_strength",
            "temporal_status",
        ),
        (
            "future_proposition_remains_unresolved",
            "guarantee_is_attributed_position_not_proof",
            "guarantor_and_proposition_explicit",
            "likely_not_promoted_to_certainty",
            "no_motive_inferred",
            "not_optimism_support_forecast_or_hope",
            "strength_of_assurance_preserved",
        ),
        5,
    ),
    _spec(
        "ro-expression-v1:741a112a615fd83b70c7",
        "EXPRESSION_FAMILY_PUBLIC_CONTRITION_OR_FAULT_ACKNOWLEDGMENT_V1",
        CommentaryRelationshipV1.PUBLIC_ACKNOWLEDGMENT_OF_FAULT_OR_REGRET,
        (
            "acknowledging_actor",
            "acknowledged_matter",
            "contrition_type",
            "public_expression",
            "temporal_order",
            "responsibility_scope",
        ),
        (
            "actor_identity_stable",
            "admission_apology_regret_distinguished",
            "institutional_and_personal_responsibility_distinguished",
            "no_sincerity_motive_culpability_or_remediation_inferred",
            "not_correction_withdrawal_sympathy_resignation_or_silence",
            "partial_responsibility_not_promoted_to_complete",
            "regret_not_promoted_to_admission_of_causation",
        ),
        5,
    ),
    _spec(
        "ro-expression-v1:7ad0710287d639d1402e",
        "EXPRESSION_FAMILY_BENIGN_APPEARANCE_HARMFUL_REALITY_V1",
        CommentaryRelationshipV1.BENIGN_PRESENTATION_HARMFUL_CONDUCT,
        (
            "subject",
            "benign_presentation",
            "harmful_conduct_or_effect",
            "same_subject_binding",
            "material_contrast",
        ),
        (
            "alleged_harm_status_preserved",
            "benign_presentation_is_supported",
            "different_subjects_not_merged",
            "harm_is_concrete_and_authority_bound",
            "hidden_character_or_deceptive_intent_not_inferred",
            "not_benign_appearance_alone",
            "not_speculative_harm",
            "same_subject_anchors_both_sides",
        ),
        10,
    ),
    _spec(
        "ro-expression-v1:844dedd262d2b832d6ee",
        "EXPRESSION_FAMILY_OPEN_ENDED_AUTHORITY_OR_COMMITMENT_V1",
        CommentaryRelationshipV1.OPEN_ENDED_AUTHORITY_OR_COMMITMENT,
        (
            "grantor",
            "recipient",
            "authorized_domain",
            "open_material_limit",
            "grant_status",
        ),
        (
            "broad_not_promoted_to_unlimited",
            "existing_constraints_preserved",
            "genuinely_open_material_limit_supported",
            "grantor_recipient_and_domain_explicit",
            "missing_reporting_detail_not_treated_as_open_limit",
            "no_corruption_recklessness_waste_or_misuse_inferred",
            "not_large_but_capped_budget",
            "proposal_not_promoted_to_effective_authorization",
        ),
        5,
    ),
    _spec(
        "ro-expression-v1:9061edfa9121f3caa7c6",
        "EXPRESSION_FAMILY_DISPROPORTIONATE_ANALYSIS_V1",
        CommentaryRelationshipV1.DISPROPORTIONATE_ANALYTICAL_COMPLEXITY,
        (
            "bounded_issue",
            "issue_scope",
            "analytical_activity",
            "complexity_or_duration",
            "same_issue_binding",
            "necessity_context",
        ),
        (
            "analytical_extent_is_evidenced",
            "disagreement_alone_insufficient",
            "duration_alone_insufficient",
            "issue_and_analysis_match",
            "issue_is_demonstrably_bounded",
            "legitimate_detail_not_mocked",
            "no_obstruction_bad_faith_or_delay_intent_inferred",
            "necessary_uncertainty_and_qualification_preserved",
        ),
        5,
        ("necessity_context",),
    ),
    _spec(
        "ro-expression-v1:a128853989c1ea8dbc10",
        "EXPRESSION_FAMILY_RULE_BREACH_OR_ERROR_WITH_CONSEQUENCE_V1",
        CommentaryRelationshipV1.RULE_BREACH_OR_ERROR_WITH_CONSEQUENCE,
        (
            "actor",
            "rule_or_standard",
            "breach_or_error",
            "breach_status",
            "consequence",
            "causal_binding",
            "temporal_order",
        ),
        (
            "actor_rule_and_breach_match",
            "appeal_and_nonfinal_status_preserved",
            "consequence_derives_from_same_breach_or_error",
            "mistake_not_promoted_to_intentional_misconduct",
            "no_broader_character_judgment",
            "not_allegation_charge_arrest_or_investigation_alone",
            "rule_is_applicable_at_relevant_time",
        ),
        5,
    ),
    _spec(
        "ro-expression-v1:a932575dfe8f1ed9134b",
        "EXPRESSION_FAMILY_PROMOTED_EXPECTATION_UNDERDELIVERY_V1",
        CommentaryRelationshipV1.PROMOTED_EXPECTATION_UNDERDELIVERED,
        (
            "promoter",
            "promoted_expectation",
            "expectation_status",
            "outcome",
            "comparison_dimension",
            "material_shortfall",
            "temporal_order",
        ),
        (
            "expectation_and_outcome_same_subject_and_dimension",
            "expectation_status_preserved",
            "material_shortfall_supported",
            "no_audience_disappointment_or_deceptive_intent_inferred",
            "not_preliminary_or_temporary_outcome",
            "quantitative_scope_preserved",
            "third_party_praise_not_promoted_to_actor_promise",
        ),
        10,
    ),
    _spec(
        "ro-expression-v1:cb128a3e07f2dbd87808",
        "EXPRESSION_FAMILY_DELIBERATE_FALSE_PRESENTATION_V1",
        CommentaryRelationshipV1.DELIBERATE_FALSE_PRESENTATION,
        (
            "presenting_actor",
            "presented_item_or_claim",
            "claimed_identity_or_status",
            "actual_identity_or_status",
            "material_difference",
            "knowledge_or_intent",
            "procedural_status",
        ),
        (
            "allegation_status_preserved",
            "claimed_and_actual_status_same_item",
            "deliberateness_is_supported",
            "institutional_and_individual_responsibility_distinguished",
            "material_mismatch_supported",
            "no_motive_benefit_reaction_or_consequence_inferred",
            "not_concealment_alone",
            "not_error_negligence_parody_or_disclosed_imitation",
            "using_altered_item_does_not_prove_knowing_use",
        ),
        10,
    ),
    _spec(
        "ro-expression-v1:ee71f9fb9de0fe424b4c",
        "EXPRESSION_FAMILY_ESTABLISHED_RESPONSIBILITY_WITHOUT_CONSEQUENCE_V1",
        CommentaryRelationshipV1.RESPONSIBILITY_WITHOUT_CONSEQUENCE,
        (
            "responsible_actor",
            "conduct",
            "responsibility_basis",
            "applicable_consequence",
            "non_imposition_outcome",
            "procedural_finality",
            "temporal_order",
        ),
        (
            "applicable_consequence_matches_conduct",
            "institutional_and_personal_responsibility_distinguished",
            "missing_reporting_not_treated_as_no_consequence",
            "no_corruption_favoritism_or_evasion_inferred",
            "not_acquittal_or_dismissal_negating_responsibility",
            "not_allegation_investigation_or_preventive_measure",
            "partial_sanction_not_promoted_to_none",
            "pending_proceeding_not_promoted_to_finality",
            "responsibility_is_established",
        ),
        10,
    ),
    _spec(
        "ro-expression-v1:fd75f40659d177a3a038",
        "EXPRESSION_FAMILY_HUMOR_RESPONSE_TO_ADVERSITY_V1",
        CommentaryRelationshipV1.HUMOR_RESPONSE_TO_ADVERSITY,
        ("adverse_situation", "affected_subject", "humor_response_binding"),
        (
            "adversity_is_real_and_authority_bound",
            "comic_response_is_editorial_voice_unless_actor_response_supported",
            "generic_satire_insufficient",
            "no_event_fact_cause_motive_reaction_consequence_or_actor_added",
            "not_unrelated_comic_ornament",
            "sensitive_harm_boundary_satisfied",
            "victim_or_event_actor_humor_not_inferred",
        ),
        10,
    ),
)

BOUNDED_POOL_SCOPE_SPECS_V1 = (
    _spec(
        "ro-expression-v1:1068794b4bf34c8914dc",
        "EXPRESSION_FAMILY_OBVIOUS_BLUNDER_OR_FAILED_EXECUTION_V1",
        CommentaryRelationshipV1.OBVIOUS_BLUNDER_OR_FAILED_EXECUTION,
        (
            "bounded_actor",
            "intended_action_or_applicable_task",
            "supported_execution_error_or_blunder",
            "direct_failed_or_adverse_result",
        ),
        (
            "actor_and_action_chain_match",
            "causal_connection_supported",
            "error_not_promoted_to_intent",
            "institutional_and_personal_responsibility_distinguished",
            "material_execution_error_supported",
            "no_general_competence_or_character_judgment",
            "status_and_epistemic_qualification_preserved",
        ),
        5,
        pool_identity="EXPRESSION_POOL_OBVIOUS_BLUNDER_OR_FAILED_EXECUTION_V1",
    ),
    _spec(
        "ro-expression-v1:65f9b0c32e8e886b8d0f",
        "EXPRESSION_FAMILY_OBVIOUS_BLUNDER_OR_FAILED_EXECUTION_V1",
        CommentaryRelationshipV1.OBVIOUS_BLUNDER_OR_FAILED_EXECUTION,
        (
            "bounded_actor",
            "intended_action_or_applicable_task",
            "supported_execution_error_or_blunder",
            "direct_failed_or_adverse_result",
        ),
        (
            "actor_and_action_chain_match",
            "causal_connection_supported",
            "error_not_promoted_to_intent",
            "institutional_and_personal_responsibility_distinguished",
            "material_execution_error_supported",
            "no_general_competence_or_character_judgment",
            "status_and_epistemic_qualification_preserved",
        ),
        5,
        pool_identity="EXPRESSION_POOL_OBVIOUS_BLUNDER_OR_FAILED_EXECUTION_V1",
    ),
    _spec(
        "ro-expression-v1:0e6562965022d3dd391f",
        "EXPRESSION_FAMILY_SUPPORTED_ANGER_OR_IRRITATED_REACTION_V1",
        CommentaryRelationshipV1.EXPLICIT_ANGER_OR_IRRITATED_REACTION,
        (
            "reacting_actor",
            "supported_anger_or_strong_irritation",
            "identified_reaction_trigger_or_context",
            "reaction_attribution",
        ),
        (
            "actor_identity_explicit",
            "anger_not_inferred_from_disagreement",
            "institutional_and_individual_reaction_distinguished",
            "no_motive_temperament_or_future_conduct_inferred",
            "reaction_attribution_preserved",
            "reaction_chronology_supported",
        ),
        4,
        pool_identity="EXPRESSION_POOL_SUPPORTED_ANGER_OR_IRRITATED_REACTION_V1",
    ),
    _spec(
        "ro-expression-v1:2ae8cdb574c10fbc2328",
        "EXPRESSION_FAMILY_SUPPORTED_ANGER_OR_IRRITATED_REACTION_V1",
        CommentaryRelationshipV1.EXPLICIT_ANGER_OR_IRRITATED_REACTION,
        (
            "reaction_trigger_actor_or_occurrence",
            "reacting_actor",
            "supported_anger_or_strong_irritation",
            "supported_trigger_to_reaction_connection",
            "reaction_attribution",
        ),
        (
            "actor_identity_explicit",
            "anger_not_inferred_from_disagreement",
            "causal_connection_explicitly_supported",
            "institutional_and_individual_reaction_distinguished",
            "no_motive_temperament_or_future_conduct_inferred",
            "reaction_attribution_preserved",
            "reaction_chronology_supported",
        ),
        4,
        pool_identity="EXPRESSION_POOL_SUPPORTED_ANGER_OR_IRRITATED_REACTION_V1",
    ),
    _spec(
        "ro-expression-v1:3df48761977436d385be",
        "EXPRESSION_FAMILY_SUSTAINED_FUTILE_EFFORT_V1",
        CommentaryRelationshipV1.SUSTAINED_EFFORT_WITHOUT_EFFECT,
        (
            "effort_actor",
            "defined_objective",
            "supported_sustained_or_repeated_effort",
            "target_or_structural_constraint",
            "supported_absence_of_material_effect",
        ),
        (
            "actor_objective_and_target_match",
            "changed_circumstances_preserved",
            "ineffectiveness_supported",
            "no_irrationality_motive_or_bad_faith_inferred",
            "not_difficulty_or_single_failure",
            "not_pending_or_temporary_setback",
            "sustained_or_repeated_effort_supported",
        ),
        5,
    ),
    _spec(
        "ro-expression-v1:e9c624855a4d33760669",
        "EXPRESSION_FAMILY_PREMATURE_COMMITMENT_TO_UNSECURED_OUTCOME_V1",
        CommentaryRelationshipV1.PREMATURE_COMMITMENT_TO_UNSECURED_OUTCOME,
        (
            "commitment_actor",
            "specific_future_outcome_or_resource",
            "supported_premature_commitment_or_reliance",
            "unmet_prerequisite_or_unsecured_status",
            "relevant_timepoint",
        ),
        (
            "actor_and_outcome_match",
            "chronology_precedes_completion",
            "conditional_status_preserved",
            "no_failure_motive_or_deception_inferred",
            "proposal_or_hope_not_promoted_to_commitment",
            "unmet_prerequisite_supported",
        ),
        5,
    ),
    _spec(
        "ro-expression-v1:7a7cb37228c5608408c6",
        "EXPRESSION_FAMILY_CRITICAL_ACTION_THRESHOLD_V1",
        CommentaryRelationshipV1.ACCUMULATION_REACHES_CRITICAL_THRESHOLD,
        (
            "affected_actor_or_system",
            "accumulating_or_persistent_problem",
            "supported_critical_threshold",
            "bounded_response_or_response_requirement",
            "chronology",
        ),
        (
            "accumulation_supported",
            "affected_actor_or_system_stable",
            "critical_threshold_materially_supported",
            "no_crisis_panic_or_blame_inferred",
            "not_isolated_or_projected_risk",
            "response_follows_threshold",
        ),
        5,
    ),
    _spec(
        "ro-expression-v1:34d94191a3c600bc4f26",
        "EXPRESSION_FAMILY_MATERIAL_LOSS_OR_NULLIFIED_RESULT_V1",
        CommentaryRelationshipV1.MATERIAL_LOSS_OR_NULLIFIED_RESULT,
        (
            "affected_actor_or_holder",
            "identified_asset_resource_or_result",
            "supported_loss_destruction_or_nullification",
            "material_scope",
            "finality_or_current_status",
        ),
        (
            "affected_item_explicit",
            "complete_and_partial_loss_distinguished",
            "finality_and_recoverability_preserved",
            "material_scope_preserved",
            "no_responsibility_waste_or_motive_inferred",
            "not_delay_risk_or_temporary_impairment",
            "quantitative_scope_preserved",
        ),
        5,
    ),
)


ALL_SCOPE_SPECS_V1 = (
    SCOPE_SPECS_V1 + FIRST_TWELVE_SCOPE_SPECS_V1 + BOUNDED_POOL_SCOPE_SPECS_V1
)

SCOPE_BY_EXPRESSION_V1 = {item.expression_id: item for item in ALL_SCOPE_SPECS_V1}
EVIDENCE_ONLY_EXPRESSION_ID = "ro-expression-v1:993a3b3354ec1705d963"


def _sealed(value, field: str) -> str:
    return canonical_identity(value.model_copy(update={field: "sha256:" + "0" * 64}))


def finalize_relation_binding_identity(binding: CommentaryRelationBinding):
    return binding.model_copy(
        update={"binding_identity": _sealed(binding, "binding_identity")}
    )


def expression_repetition_identity(
    expression_id: str, family_identity: str, relationship: CommentaryRelationshipV1
) -> str:
    return f"expression-v2|{expression_id}|{family_identity}|{relationship.value}"


def _surface_for(record, overlay, catalog, spec):
    if record.renderability_status is RenderabilityStatusV2.APPROVED_CLOSED_SURFACE:
        surface = next(
            item
            for item in overlay.approved_surfaces
            if item.surface_id == record.approved_surface_ids[0]
        )
        if (
            surface.expression_family_identity != spec.family_identity
            or surface.equivalence_group_identity != spec.family_identity
            or surface.pool_identity != spec.pool_identity
            or not surface.requires_preceding_authority_binding
            or surface.runtime_morphology
            or surface.cross_episode_cooldown != spec.cooldown_episodes
        ):
            raise ExpressionEligibilityIntegrityError(
                "approved surface contract does not match frozen scope"
            )
        return surface.surface_id, surface.exact_surface, surface.surface_utf8_sha256
    if record.renderability_status is RenderabilityStatusV2.EXACT_V1_SURFACE:
        source = next(
            item
            for item in catalog.expressions
            if item.expression_id == record.expression_id
        )
        return (
            f"CATALOG_V1_EXACT:{record.expression_id}",
            source.text,
            hashlib.sha256(source.text.encode("utf-8")).hexdigest(),
        )
    raise ExpressionEligibilityIntegrityError("approved expression is not renderable")


def _validate_inputs(bundle, bindings, program_result, program_candidate, snapshot):
    if bundle.bundle_identity != bundle_payload_identity(bundle):
        raise ExpressionEligibilityIntegrityError("fact-atom bundle identity mismatch")
    if program_result.fact_atom_bundle_identity != bundle.bundle_identity:
        raise ExpressionEligibilityIntegrityError("program result/bundle mismatch")
    if program_result.repetition_snapshot_identity != snapshot.snapshot_identity:
        raise ExpressionEligibilityIntegrityError("program result/snapshot mismatch")
    candidates = {item.candidate_id: item for item in program_result.shortlist}
    if (
        program_candidate.candidate_id not in candidates
        or candidates[program_candidate.candidate_id] != program_candidate
    ):
        raise ExpressionEligibilityIntegrityError(
            "program candidate is not shortlisted"
        )
    atom_ids = {item.atom_id for item in bundle.atoms}
    identities = set()
    for binding in bindings:
        if binding.binding_identity != _sealed(binding, "binding_identity"):
            raise ExpressionEligibilityIntegrityError(
                "relation binding identity mismatch"
            )
        if binding.binding_identity in identities:
            raise ExpressionEligibilityIntegrityError("duplicate relation binding")
        identities.add(binding.binding_identity)
        if isinstance(binding, CommentaryRelationBindingV2):
            # Revalidate the exact serialized shape at the eligibility boundary;
            # no V1 binding is promoted or interpreted as V2.
            CommentaryRelationBindingV2.model_validate(binding.model_dump(mode="json"))
        if binding.fact_atom_bundle_identity != bundle.bundle_identity:
            raise ExpressionEligibilityIntegrityError("stale relation binding")
        referenced = {atom for role in binding.atom_roles for atom in role.atom_ids}
        if not referenced <= atom_ids:
            raise ExpressionEligibilityIntegrityError(
                "relation binding references unknown atom"
            )


def _binding_reasons(spec, binding, program_candidate, bundle):
    if binding is None:
        return ["missing_explicit_relation_binding"]
    reasons = []
    roles = tuple(item.role for item in binding.atom_roles)
    if roles != spec.required_roles:
        reasons.append("required_atom_roles_mismatch")
    if not set(spec.required_constraint_codes) <= set(
        binding.satisfied_constraint_codes
    ):
        reasons.append("frozen_relationship_constraints_unsatisfied")
    if program_candidate.program_id not in binding.compatible_program_ids:
        reasons.append("selected_program_incompatible")
    atoms = {item.atom_id: item for item in bundle.atoms}
    for role in binding.atom_roles:
        if role.role in spec.background_allowed_roles:
            continue
        if any(
            atoms[atom].authority_class is not AuthorityClass.EVENT
            for atom in role.atom_ids
        ):
            reasons.append("event_relationship_requires_event_authority")
            break
    return reasons


def _repetition_reasons(spec, surface_id, snapshot):
    current = [
        use
        for use in snapshot.uses
        if use.episode_ordinal == snapshot.current_episode_ordinal
    ]
    prior_enrichments = [use for use in snapshot.uses if use.enrichment_identity]
    identity = expression_repetition_identity(
        spec.expression_id, spec.family_identity, spec.relationship
    )
    reasons = []
    if any(use.enrichment_identity == identity for use in current):
        reasons.append("expression_episode_ceiling")
    if any(surface_id in use.surface_ids for use in current):
        reasons.append("exact_surface_episode_block")
    if any(
        use.story_position == snapshot.current_story_position - 1
        and use.episode_ordinal == snapshot.current_episode_ordinal
        for use in prior_enrichments
    ):
        reasons.append("adjacent_expression_enrichment_block")
    if any(
        use.enrichment_identity == identity
        and use.episode_ordinal < snapshot.current_episode_ordinal
        and snapshot.current_episode_ordinal - use.episode_ordinal
        <= spec.cooldown_episodes
        for use in prior_enrichments
    ):
        reasons.append("expression_family_cross_episode_cooldown")
    family_marker = f"|{spec.family_identity}|{spec.relationship.value}"
    if any(
        use.enrichment_identity
        and family_marker in use.enrichment_identity
        and use.episode_ordinal == snapshot.current_episode_ordinal
        for use in prior_enrichments
    ):
        reasons.append("expression_family_episode_ceiling")
    if any(
        use.enrichment_identity
        and family_marker in use.enrichment_identity
        and use.episode_ordinal < snapshot.current_episode_ordinal
        and snapshot.current_episode_ordinal - use.episode_ordinal
        <= spec.cooldown_episodes
        for use in prior_enrichments
    ):
        reasons.append("expression_family_cross_episode_cooldown")
    return reasons


def evaluate_expression_eligibility_v1(
    *,
    bundle: VoiceFactAtomBundleV1,
    bindings: tuple[CommentaryRelationBinding, ...],
    program_result: VoiceEligibilityResultV1,
    selected_program_candidate: ProgramCandidateV1,
    repetition_snapshot: VoiceRepetitionSnapshotV1,
    overlay: ExpressionCatalogOverlayV2,
    catalog,
) -> ExpressionEligibilityResultV1:
    _validate_inputs(
        bundle,
        bindings,
        program_result,
        selected_program_candidate,
        repetition_snapshot,
    )
    records = {item.expression_id: item for item in overlay.records}
    outcomes = []
    candidates = []
    for spec in sorted(ALL_SCOPE_SPECS_V1, key=lambda item: item.expression_id):
        record = records[spec.expression_id]
        reasons = []
        if (
            record.adjudication_status
            is not AdjudicationStatusV2.APPROVED_CANDIDATE_SCOPE
        ):
            reasons.append("expression_scope_not_approved")
        try:
            surface_id, exact_surface, surface_sha = _surface_for(
                record, overlay, catalog, spec
            )
        except ExpressionEligibilityIntegrityError:
            surface_id = "UNAVAILABLE"
            exact_surface = ""
            surface_sha = "0" * 64
            reasons.append("approved_exact_surface_unavailable")
        relationship_bindings = tuple(
            item for item in bindings if item.relationship is spec.relationship
        )
        binding = next(
            (
                item
                for item in relationship_bindings
                if tuple(role.role for role in item.atom_roles) == spec.required_roles
            ),
            relationship_bindings[0] if relationship_bindings else None,
        )
        reasons.extend(
            _binding_reasons(spec, binding, selected_program_candidate, bundle)
        )
        reasons.extend(_repetition_reasons(spec, surface_id, repetition_snapshot))
        reasons = sorted(set(reasons))
        status = (
            ExpressionEligibilityStatusV1.INELIGIBLE
            if reasons
            else ExpressionEligibilityStatusV1.ELIGIBLE
        )
        outcomes.append(
            ExpressionEligibilityOutcomeV1(
                expression_id=spec.expression_id,
                status=status,
                reason_codes=tuple(reasons)
                or ("all_frozen_expression_gates_satisfied",),
            )
        )
        if status is ExpressionEligibilityStatusV1.ELIGIBLE and binding is not None:
            repetition_identity = expression_repetition_identity(
                spec.expression_id, spec.family_identity, spec.relationship
            )
            candidate_id = canonical_identity(
                f"{bundle.bundle_identity}|{binding.binding_identity}|"
                f"{selected_program_candidate.candidate_id}|{spec.expression_id}|{surface_id}"
            )
            candidates.append(
                ExpressionCandidateV1(
                    candidate_id=candidate_id,
                    expression_id=spec.expression_id,
                    expression_family_identity=spec.family_identity,
                    pool_identity=spec.pool_identity,
                    relationship=spec.relationship,
                    relation_binding_identity=binding.binding_identity,
                    selected_program_candidate_id=selected_program_candidate.candidate_id,
                    surface_id=surface_id,
                    exact_surface=exact_surface,
                    surface_utf8_sha256=surface_sha,
                    repetition_identity=repetition_identity,
                )
            )
    outcomes.append(
        ExpressionEligibilityOutcomeV1(
            expression_id=EVIDENCE_ONLY_EXPRESSION_ID,
            status=ExpressionEligibilityStatusV1.INELIGIBLE,
            reason_codes=("evidence_only_never_eligible",),
        )
    )
    provisional = ExpressionEligibilityResultV1(
        fact_atom_bundle_identity=bundle.bundle_identity,
        program_eligibility_result_identity=program_result.result_identity,
        repetition_snapshot_identity=repetition_snapshot.snapshot_identity,
        outcomes=tuple(outcomes),
        shortlist=tuple(sorted(candidates, key=lambda item: item.expression_id)),
    )
    return provisional.model_copy(
        update={"result_identity": _sealed(provisional, "result_identity")}
    )


def finalize_expression_selection_receipt(
    receipt: ExpressionOwnerSelectionReceiptV1,
    *,
    result: ExpressionEligibilityResultV1,
    snapshot: VoiceRepetitionSnapshotV1,
) -> ExpressionOwnerSelectionReceiptV1:
    if result.result_identity != _sealed(result, "result_identity"):
        raise ExpressionEligibilityIntegrityError(
            "eligibility result identity mismatch"
        )
    expected = tuple(item.candidate_id for item in result.shortlist)
    if receipt.shortlist_candidate_ids != expected:
        raise ExpressionEligibilityIntegrityError("selection shortlist mismatch")
    if (
        receipt.fact_atom_bundle_identity != result.fact_atom_bundle_identity
        or receipt.expression_eligibility_result_identity != result.result_identity
        or receipt.repetition_snapshot_identity != snapshot.snapshot_identity
        or result.repetition_snapshot_identity != snapshot.snapshot_identity
    ):
        raise ExpressionEligibilityIntegrityError("selection binding mismatch")
    return receipt.model_copy(
        update={"receipt_identity": _sealed(receipt, "receipt_identity")}
    )


__all__ = [
    "ALL_SCOPE_SPECS_V1",
    "BOUNDED_POOL_SCOPE_SPECS_V1",
    "EVIDENCE_ONLY_EXPRESSION_ID",
    "FIRST_TWELVE_SCOPE_SPECS_V1",
    "SCOPE_SPECS_V1",
    "ExpressionEligibilityIntegrityError",
    "evaluate_expression_eligibility_v1",
    "expression_repetition_identity",
    "finalize_expression_selection_receipt",
    "finalize_relation_binding_identity",
]
