"""Typed relationship, eligibility, and selection contracts for expressions."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from .models import ZERO_SHA256, FrozenModel

SHA256_URI_PATTERN = r"^sha256:[0-9a-f]{64}$"


class CommentaryRelationshipV1(StrEnum):
    DELAYED_ACTION_AFTER_OUTCOME = "SUPPORTED_DELAYED_ACTION_AFTER_OUTCOME"
    REPETITION_WITHOUT_PROGRESS = "SUPPORTED_REPETITION_WITHOUT_PROGRESS"
    EXPERTISE_ROLE_REVERSAL = "SUPPORTED_EXPERTISE_ROLE_REVERSAL"
    UNRESOLVED_OUTCOME = "SUPPORTED_UNRESOLVED_OUTCOME"
    CONCEALMENT_OR_SUPPRESSION = "SUPPORTED_CONCEALMENT_OR_SUPPRESSION"
    POSITION_OR_VERSION_REVERSAL = "SUPPORTED_POSITION_OR_VERSION_REVERSAL"
    GIFT_OR_FREE_ADVANTAGE = "SUPPORTED_GIFT_OR_FREE_ADVANTAGE"
    CONDUCT_STRENGTHENS_POSITION_OR_PROCESS = (
        "SUPPORTED_CONDUCT_STRENGTHENS_EXISTING_POSITION_OR_PROCESS"
    )
    DIRECT_DISCOVERY_OF_CONDUCT = (
        "SUPPORTED_DISCOVERY_DURING_OR_WITH_DIRECT_EVIDENCE_OF_CONDUCT"
    )
    EXPLICIT_HIGH_CONFIDENCE_GUARANTEE = "SUPPORTED_EXPLICIT_HIGH_CONFIDENCE_GUARANTEE"
    PUBLIC_ACKNOWLEDGMENT_OF_FAULT_OR_REGRET = (
        "SUPPORTED_PUBLIC_ACKNOWLEDGMENT_OF_FAULT_OR_REGRET"
    )
    BENIGN_PRESENTATION_HARMFUL_CONDUCT = (
        "SUPPORTED_BENIGN_PRESENTATION_CONTRASTS_WITH_HARMFUL_CONDUCT"
    )
    OPEN_ENDED_AUTHORITY_OR_COMMITMENT = "SUPPORTED_OPEN_ENDED_AUTHORITY_OR_COMMITMENT"
    DISPROPORTIONATE_ANALYTICAL_COMPLEXITY = (
        "SUPPORTED_ANALYTICAL_COMPLEXITY_DISPROPORTIONATE_TO_BOUNDED_ISSUE"
    )
    RULE_BREACH_OR_ERROR_WITH_CONSEQUENCE = (
        "SUPPORTED_RULE_BREACH_OR_ERROR_WITH_BOUND_CONSEQUENCE"
    )
    PROMOTED_EXPECTATION_UNDERDELIVERED = (
        "SUPPORTED_PROMOTED_EXPECTATION_UNDERDELIVERED_BY_OUTCOME"
    )
    DELIBERATE_FALSE_PRESENTATION = (
        "SUPPORTED_DELIBERATE_FALSE_PRESENTATION_AS_AUTHENTIC"
    )
    RESPONSIBILITY_WITHOUT_CONSEQUENCE = (
        "SUPPORTED_ESTABLISHED_RESPONSIBILITY_WITHOUT_EXPECTED_CONSEQUENCE"
    )
    HUMOR_RESPONSE_TO_ADVERSITY = "SUPPORTED_HUMOR_RESPONSE_TO_REAL_ADVERSITY"
    OBVIOUS_BLUNDER_OR_FAILED_EXECUTION = (
        "SUPPORTED_OBVIOUS_BLUNDER_OR_FAILED_EXECUTION"
    )
    EXPLICIT_ANGER_OR_IRRITATED_REACTION = (
        "SUPPORTED_EXPLICIT_ANGER_OR_IRRITATED_REACTION"
    )
    SUSTAINED_EFFORT_WITHOUT_EFFECT = (
        "SUPPORTED_SUSTAINED_EFFORT_WITHOUT_PLAUSIBLE_EFFECT_ON_TARGET"
    )
    PREMATURE_COMMITMENT_TO_UNSECURED_OUTCOME = (
        "SUPPORTED_PREMATURE_COMMITMENT_TO_UNSECURED_OUTCOME"
    )
    ACCUMULATION_REACHES_CRITICAL_THRESHOLD = (
        "SUPPORTED_ACCUMULATION_REACHES_CRITICAL_ACTION_THRESHOLD"
    )
    MATERIAL_LOSS_OR_NULLIFIED_RESULT = "SUPPORTED_MATERIAL_LOSS_OR_NULLIFIED_RESULT"


class ExpressionEligibilityStatusV1(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"


class ExpressionSelectionKindV1(StrEnum):
    EXPRESSION = "expression"
    NONE = "none"


class RelationAtomRoleV1(FrozenModel):
    role: str = Field(min_length=1)
    atom_ids: tuple[str, ...] = Field(min_length=1)


class MultiRoleAtomReuseAuthorizationV2(FrozenModel):
    atom_id: str = Field(min_length=1)
    shared_roles: tuple[str, ...] = Field(min_length=2)
    semantic_reason: str = Field(min_length=1)
    creates_new_proposition: Literal[False] = False
    widens_source_scope: Literal[False] = False
    strengthens_causality: Literal[False] = False
    changes_attribution: Literal[False] = False
    collapses_actor_and_institution: Literal[False] = False

    @model_validator(mode="after")
    def validate_roles(self):
        if len(self.shared_roles) != len(set(self.shared_roles)):
            raise ValueError("reuse authorization roles must be unique")
        return self


class CommentaryRelationBindingV1(FrozenModel):
    schema_version: Literal["COMMENTARY_RELATION_BINDING_V1"] = (
        "COMMENTARY_RELATION_BINDING_V1"
    )
    fact_atom_bundle_identity: str = Field(pattern=SHA256_URI_PATTERN)
    relationship: CommentaryRelationshipV1
    atom_roles: tuple[RelationAtomRoleV1, ...] = Field(min_length=1)
    directionality: Literal["role_ordered"] = "role_ordered"
    satisfied_constraint_codes: tuple[str, ...] = ()
    compatible_program_ids: tuple[str, ...] = Field(min_length=1)
    insertion_point: Literal["commentary_conclusion"] = "commentary_conclusion"
    adjudication_receipt_identity: str = Field(pattern=SHA256_URI_PATTERN)
    owner_or_editor_identity: str = Field(min_length=1)
    binding_identity: str = Field(pattern=SHA256_URI_PATTERN)

    @model_validator(mode="after")
    def validate_shape(self):
        roles = [item.role for item in self.atom_roles]
        if len(roles) != len(set(roles)):
            raise ValueError("duplicate relationship atom role")
        atom_ids = [atom for item in self.atom_roles for atom in item.atom_ids]
        if len(atom_ids) != len(set(atom_ids)):
            raise ValueError("relationship atom cannot satisfy multiple roles")
        if tuple(sorted(set(self.satisfied_constraint_codes))) != (
            self.satisfied_constraint_codes
        ):
            raise ValueError("constraint codes must be sorted and unique")
        if len(self.compatible_program_ids) != len(set(self.compatible_program_ids)):
            raise ValueError("compatible program IDs must be unique")
        return self


class CommentaryRelationBindingV2(FrozenModel):
    schema_version: Literal["COMMENTARY_RELATION_BINDING_V2"] = (
        "COMMENTARY_RELATION_BINDING_V2"
    )
    event_id: int = Field(gt=0)
    semantic_draft_revision_identity: str = Field(pattern=SHA256_URI_PATTERN)
    fact_atom_bundle_identity: str = Field(pattern=SHA256_URI_PATTERN)
    relationship: CommentaryRelationshipV1
    atom_roles: tuple[RelationAtomRoleV1, ...] = Field(min_length=1)
    multi_role_reuse_authorizations: tuple[
        MultiRoleAtomReuseAuthorizationV2, ...
    ] = ()
    directionality: Literal["role_ordered"] = "role_ordered"
    satisfied_constraint_codes: tuple[str, ...] = ()
    compatible_program_ids: tuple[str, ...] = Field(min_length=1)
    insertion_point: Literal["commentary_conclusion"] = "commentary_conclusion"
    adjudication_receipt_identity: str = Field(pattern=SHA256_URI_PATTERN)
    mechanic_claim_identity: str = Field(pattern=SHA256_URI_PATTERN)
    mechanic_receipt_identity: str = Field(pattern=SHA256_URI_PATTERN)
    program_selection_receipt_identity: str = Field(pattern=SHA256_URI_PATTERN)
    owner_or_editor_identity: str = Field(min_length=1)
    owner_authorized_at: datetime
    binding_identity: str = Field(pattern=SHA256_URI_PATTERN)

    @model_validator(mode="after")
    def validate_shape(self):
        roles = [item.role for item in self.atom_roles]
        if len(roles) != len(set(roles)):
            raise ValueError("duplicate relationship atom role")
        if tuple(sorted(set(self.satisfied_constraint_codes))) != (
            self.satisfied_constraint_codes
        ):
            raise ValueError("constraint codes must be sorted and unique")
        if len(self.compatible_program_ids) != len(set(self.compatible_program_ids)):
            raise ValueError("compatible program IDs must be unique")

        uses: dict[str, list[str]] = {}
        for role in self.atom_roles:
            for atom_id in role.atom_ids:
                uses.setdefault(atom_id, []).append(role.role)
        repeated = {atom: tuple(items) for atom, items in uses.items() if len(items) > 1}
        declarations = {
            item.atom_id: item.shared_roles
            for item in self.multi_role_reuse_authorizations
        }
        if len(declarations) != len(self.multi_role_reuse_authorizations):
            raise ValueError("duplicate multi-role reuse authorization")
        if declarations != repeated:
            raise ValueError("multi-role atom reuse authorization mismatch")
        return self


CommentaryRelationBinding = CommentaryRelationBindingV1 | CommentaryRelationBindingV2


class ExpressionEligibilityOutcomeV1(FrozenModel):
    expression_id: str = Field(min_length=1)
    status: ExpressionEligibilityStatusV1
    reason_codes: tuple[str, ...]


class ExpressionCandidateV1(FrozenModel):
    candidate_id: str = Field(pattern=SHA256_URI_PATTERN)
    expression_id: str = Field(min_length=1)
    expression_family_identity: str = Field(min_length=1)
    pool_identity: str | None = None
    relationship: CommentaryRelationshipV1
    relation_binding_identity: str = Field(pattern=SHA256_URI_PATTERN)
    selected_program_candidate_id: str = Field(pattern=SHA256_URI_PATTERN)
    surface_id: str = Field(min_length=1)
    exact_surface: str = Field(min_length=1)
    surface_utf8_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    insertion_point: Literal["commentary_conclusion"] = "commentary_conclusion"
    repetition_identity: str = Field(min_length=1)


class ExpressionEligibilityResultV1(FrozenModel):
    schema_version: Literal["VOICE_EXPRESSION_ELIGIBILITY_RESULT_V1"] = (
        "VOICE_EXPRESSION_ELIGIBILITY_RESULT_V1"
    )
    fact_atom_bundle_identity: str = Field(pattern=SHA256_URI_PATTERN)
    program_eligibility_result_identity: str = Field(pattern=SHA256_URI_PATTERN)
    repetition_snapshot_identity: str = Field(pattern=SHA256_URI_PATTERN)
    outcomes: tuple[ExpressionEligibilityOutcomeV1, ...]
    shortlist: tuple[ExpressionCandidateV1, ...]
    production_active: Literal[False] = False
    model_calls: Literal[0] = 0
    provider_calls: Literal[0] = 0
    result_identity: str = Field(
        default="sha256:" + ZERO_SHA256, pattern=SHA256_URI_PATTERN
    )


class ExpressionOwnerSelectionReceiptV1(FrozenModel):
    schema_name: Literal["pastilaacida-voice-expression-owner-selection-receipt"] = (
        "pastilaacida-voice-expression-owner-selection-receipt"
    )
    schema_version: Literal["1"] = "1"
    fact_atom_bundle_identity: str = Field(pattern=SHA256_URI_PATTERN)
    expression_eligibility_result_identity: str = Field(pattern=SHA256_URI_PATTERN)
    repetition_snapshot_identity: str = Field(pattern=SHA256_URI_PATTERN)
    shortlist_candidate_ids: tuple[str, ...]
    selection_kind: ExpressionSelectionKindV1
    selected_candidate_id: str | None = Field(default=None, pattern=SHA256_URI_PATTERN)
    selector_identity: str = Field(min_length=1)
    selected_at: datetime
    receipt_identity: str = Field(
        default="sha256:" + ZERO_SHA256, pattern=SHA256_URI_PATTERN
    )

    @model_validator(mode="after")
    def validate_selection(self):
        if len(self.shortlist_candidate_ids) != len(set(self.shortlist_candidate_ids)):
            raise ValueError("shortlist candidate IDs must be unique")
        if self.selection_kind is ExpressionSelectionKindV1.NONE:
            if self.selected_candidate_id is not None:
                raise ValueError("NONE selection cannot select an expression")
        elif (
            self.selected_candidate_id is None
            or self.selected_candidate_id not in self.shortlist_candidate_ids
        ):
            raise ValueError("selected expression is not in the shortlist")
        return self


__all__ = [
    "CommentaryRelationBinding",
    "CommentaryRelationBindingV1",
    "CommentaryRelationBindingV2",
    "CommentaryRelationshipV1",
    "ExpressionCandidateV1",
    "ExpressionEligibilityOutcomeV1",
    "ExpressionEligibilityResultV1",
    "ExpressionEligibilityStatusV1",
    "ExpressionOwnerSelectionReceiptV1",
    "ExpressionSelectionKindV1",
    "MultiRoleAtomReuseAuthorizationV2",
    "RelationAtomRoleV1",
]
