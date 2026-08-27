"""Closed types for the deterministic Voice V2 proof renderer."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MechanicIdV1(StrEnum):
    NUMERIC_EXPECTATION_LADDER = "NUMERIC_EXPECTATION_LADDER_V1"
    FICTIONAL_INTAKE_OR_INTERFACE = "FICTIONAL_INTAKE_OR_INTERFACE_V1"
    SUPPORTED_ROLE_REVERSAL = "SUPPORTED_ROLE_REVERSAL_V1"
    UNCERTAINTY_SANDWICHED_FICTION = "UNCERTAINTY_SANDWICHED_FICTION_V1"
    PROCEDURAL_ESCALATION_TO_DOMAIN_METAPHOR = (
        "PROCEDURAL_ESCALATION_TO_DOMAIN_METAPHOR_V1"
    )
    SUPPORTED_TERM_NONLITERALIZATION = "SUPPORTED_TERM_NONLITERALIZATION_V1"
    BACKGROUND_CAPABILITY_EVENT_CONTRAST = "BACKGROUND_CAPABILITY_EVENT_CONTRAST_V1"


class ProvenanceClassV1(StrEnum):
    AUTHORIZED_EVENT_FACT_ATOM = "AUTHORIZED_EVENT_FACT_ATOM"
    AUTHORIZED_BACKGROUND_FACT_ATOM = "AUTHORIZED_BACKGROUND_FACT_ATOM"
    NONFACTUAL_COMIC_SURFACE = "NONFACTUAL_COMIC_SURFACE"
    NONLITERAL_SUPPORTED_FACT_PARAPHRASE = "NONLITERAL_SUPPORTED_FACT_PARAPHRASE"
    DETERMINISTIC_FORMATTING_OR_OPERATOR = "DETERMINISTIC_FORMATTING_OR_OPERATOR"
    APPROVED_EXPRESSION_SURFACE = "APPROVED_EXPRESSION_SURFACE"


class BackgroundKindV1(StrEnum):
    PUBLIC_CONTEXT = "PUBLIC_CONTEXT"
    CULTURAL_OR_DOMAIN_CALLBACK = "CULTURAL_OR_DOMAIN_CALLBACK"
    PROFESSIONAL_DOMAIN_PREMISE = "PROFESSIONAL_DOMAIN_PREMISE"


class IRDispositionV1(StrEnum):
    REALIZE = "realize"
    ABSTAIN = "abstain"


class AbstentionReasonV1(StrEnum):
    AMBIGUOUS_FACT_ATOM = "AMBIGUOUS_FACT_ATOM"
    UNSUPPORTED_RELATIONSHIP_RISK = "UNSUPPORTED_RELATIONSHIP_RISK"
    REPETITION_BUDGET_EXHAUSTED = "REPETITION_BUDGET_EXHAUSTED"


class RenderOutcomeV1(StrEnum):
    ACCEPTED = "accepted"
    ABSTAINED = "abstained"


class FictionalRoleplayActorV1(_FrozenModel):
    fictional_actor_id: str = Field(min_length=1)
    fictional_role: str = Field(min_length=1)
    explicit_frame_span: str = Field(min_length=1)
    identity_isolation_from_event_actor_ids: tuple[str, ...]
    allowed_invented_dialogue: bool
    allowed_invented_internal_state: bool
    allowed_invented_fictional_history: bool
    professional_domain_premise_atom_ids: tuple[str, ...] = ()
    forbidden_projection_back_to_event_actors: Literal[True] = True
    explicit_frame_termination: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_isolation(self):
        if self.fictional_actor_id in self.identity_isolation_from_event_actor_ids:
            raise ValueError("fictional actor intersects real event actors")
        return self


class CommentaryBackgroundAtomV1(_FrozenModel):
    atom_id: str = Field(min_length=1)
    background_kind: BackgroundKindV1
    exact_proposition: str = Field(min_length=1)
    provenance_identity: str = Field(min_length=1)
    jurisdiction: str | None = None
    procedural_stage: str | None = None
    professional_role: str | None = None

    @model_validator(mode="after")
    def validate_professional_domain(self):
        if self.background_kind is BackgroundKindV1.PROFESSIONAL_DOMAIN_PREMISE and (
            not self.jurisdiction
            or not self.procedural_stage
            or not self.professional_role
        ):
            raise ValueError("professional-domain premise lacks scoped metadata")
        return self


class ExpressionSpanBindingV1(_FrozenModel):
    catalog_expression_id: str = Field(min_length=1)
    selected_surface_id: str = Field(min_length=1)
    selected_surface_utf8_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    relationship_binding_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    pool_identity: str | None = None
    selected_program_candidate_id: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    insertion_point: Literal["commentary_conclusion"] = "commentary_conclusion"
    owner_selection_receipt_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    repetition_snapshot_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    repetition_identity: str = Field(min_length=1)
    character_provenance_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class IRSpanV1(_FrozenModel):
    text: str
    provenance_class: ProvenanceClassV1
    source_identity: str = Field(min_length=1)
    fictional_actor_id: str | None = None
    nonliteral_mapping_id: str | None = None
    callback_id: str | None = None
    expression_binding: ExpressionSpanBindingV1 | None = None

    @model_validator(mode="after")
    def validate_typed_binding(self):
        if (
            self.provenance_class
            is ProvenanceClassV1.NONLITERAL_SUPPORTED_FACT_PARAPHRASE
            and not self.nonliteral_mapping_id
        ):
            raise ValueError("nonliteral span lacks approved mapping")
        if (self.provenance_class is ProvenanceClassV1.APPROVED_EXPRESSION_SURFACE) != (
            self.expression_binding is not None
        ):
            raise ValueError(
                "expression provenance requires a typed expression binding"
            )
        return self


class AcidCommentaryIRV1_1(_FrozenModel):
    schema_version: Literal["ACID_COMMENTARY_IR_V1_1"] = "ACID_COMMENTARY_IR_V1_1"
    proof_id: str = Field(pattern=r"^P[1-8]$")
    source_record_id: str = Field(min_length=1)
    realization_program_id: str = Field(min_length=1)
    realization_program_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    mechanic_id: MechanicIdV1
    disposition: IRDispositionV1
    spans: tuple[IRSpanV1, ...] = ()
    fictional_actors: tuple[FictionalRoleplayActorV1, ...] = ()
    background_atoms: tuple[CommentaryBackgroundAtomV1, ...] = ()
    repetition_signature: str = Field(min_length=1)
    abstention_reason: AbstentionReasonV1 | None = None
    expected_output_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    base_span_count: int | None = Field(default=None, ge=1)
    base_output_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_disposition(self):
        if self.disposition is IRDispositionV1.REALIZE:
            if (
                not self.spans
                or not self.expected_output_sha256
                or self.abstention_reason
            ):
                raise ValueError("realization IR is incomplete")
        elif self.spans or self.expected_output_sha256 or not self.abstention_reason:
            raise ValueError("abstention IR cannot contain output prose")

        actor_ids = {actor.fictional_actor_id for actor in self.fictional_actors}
        if len(actor_ids) != len(self.fictional_actors):
            raise ValueError("duplicate fictional actor identity")
        if any(
            span.fictional_actor_id and span.fictional_actor_id not in actor_ids
            for span in self.spans
        ):
            raise ValueError("span references an unknown fictional actor")
        expression_spans = tuple(
            span
            for span in self.spans
            if span.provenance_class is ProvenanceClassV1.APPROVED_EXPRESSION_SURFACE
        )
        if expression_spans:
            if (
                len(expression_spans) != 1
                or self.base_span_count is None
                or self.base_output_sha256 is None
                or self.base_span_count >= len(self.spans)
            ):
                raise ValueError("integrated expression IR shape is invalid")
            if self.spans[-1] != expression_spans[0]:
                raise ValueError("expression must occupy the final typed span")
        elif self.base_span_count is not None or self.base_output_sha256 is not None:
            raise ValueError("base rendering metadata requires an expression span")
        return self


class ProductionAcidCommentaryIRV1_1(_FrozenModel):
    """Canonical IR for an ordinary persisted story, independent of P1-P8."""

    schema_version: Literal["ACID_COMMENTARY_IR_V1_1"] = "ACID_COMMENTARY_IR_V1_1"
    authority_kind: Literal["reusable_production_program"] = (
        "reusable_production_program"
    )
    semantic_draft_revision_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    event_id: int = Field(gt=0)
    story_position: int = Field(gt=0)
    fact_atom_bundle_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mechanic_id: MechanicIdV1
    mechanic_eligibility_claim_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    realization_program_id: str = Field(min_length=1)
    realization_program_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    program_eligibility_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    program_selection_receipt_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_program_candidate_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    atom_role_bindings: tuple[tuple[str, tuple[str, ...]], ...] = Field(min_length=1)
    relationship_binding_identities: tuple[str, ...] = ()
    expression_selection_receipt_identity: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    repetition_snapshot_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    activation_policy_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    renderer_identity: str = Field(min_length=1)
    spans: tuple[IRSpanV1, ...] = Field(min_length=1)
    repetition_signature: str = Field(min_length=1)
    expected_output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_roles_and_expression_shape(self):
        roles = [role for role, _ in self.atom_role_bindings]
        if len(roles) != len(set(roles)):
            raise ValueError("duplicate production atom role")
        atom_ids = [atom_id for _, ids in self.atom_role_bindings for atom_id in ids]
        if len(atom_ids) != len(set(atom_ids)):
            raise ValueError("one atom cannot occupy multiple production roles")
        expression_spans = tuple(
            span
            for span in self.spans
            if span.provenance_class is ProvenanceClassV1.APPROVED_EXPRESSION_SURFACE
        )
        if expression_spans:
            raise ValueError("production expression activation is currently zero")
        return self


class ProofOnlyOrdinaryStoryAcidCommentaryIRV1_1(_FrozenModel):
    """Expression-bearing ordinary-story IR that is never production authority."""

    schema_version: Literal["ACID_COMMENTARY_IR_V1_1"] = "ACID_COMMENTARY_IR_V1_1"
    authority_kind: Literal["ordinary_story_expression_proof_only"] = (
        "ordinary_story_expression_proof_only"
    )
    proof_only: Literal[True] = True
    production_eligible: Literal[False] = False
    proof_expression_authority_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    semantic_draft_revision_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    event_id: int = Field(gt=0)
    story_position: int = Field(gt=0)
    fact_atom_bundle_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    mechanic_id: MechanicIdV1
    mechanic_eligibility_claim_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    realization_program_id: str = Field(min_length=1)
    realization_program_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    program_eligibility_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    program_selection_receipt_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    selected_program_candidate_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    atom_role_bindings: tuple[tuple[str, tuple[str, ...]], ...] = Field(min_length=1)
    relationship_binding_identities: tuple[str, ...] = Field(min_length=1)
    expression_eligibility_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    expression_selection_receipt_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    repetition_snapshot_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    catalog_overlay_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    renderer_identity: str = Field(min_length=1)
    spans: tuple[IRSpanV1, ...] = Field(min_length=1)
    repetition_signature: str = Field(min_length=1)
    expected_output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def exact_expression_shape(self):
        expression_spans = tuple(
            span
            for span in self.spans
            if span.provenance_class is ProvenanceClassV1.APPROVED_EXPRESSION_SURFACE
        )
        if len(expression_spans) != 1 or self.spans[-1] != expression_spans[0]:
            raise ValueError(
                "proof-only ordinary-story IR requires one final expression"
            )
        return self


class RenderedProvenanceSpanV1(_FrozenModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    provenance_class: ProvenanceClassV1
    source_identity: str
    fictional_actor_id: str | None = None
    nonliteral_mapping_id: str | None = None
    callback_id: str | None = None
    expression_binding: ExpressionSpanBindingV1 | None = None


class DeterministicVoiceResultV1(_FrozenModel):
    outcome: RenderOutcomeV1
    commentary_bytes: bytes = b""
    output_sha256: str | None = None
    abstention_reason: AbstentionReasonV1 | None = None
    provenance: tuple[RenderedProvenanceSpanV1, ...] = ()
    ir_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_calls: Literal[0] = 0
    provider_calls: Literal[0] = 0
    model_loads: Literal[0] = 0


__all__ = [
    "AbstentionReasonV1",
    "AcidCommentaryIRV1_1",
    "BackgroundKindV1",
    "CommentaryBackgroundAtomV1",
    "DeterministicVoiceResultV1",
    "ExpressionSpanBindingV1",
    "FictionalRoleplayActorV1",
    "IRDispositionV1",
    "IRSpanV1",
    "MechanicIdV1",
    "ProductionAcidCommentaryIRV1_1",
    "ProofOnlyOrdinaryStoryAcidCommentaryIRV1_1",
    "ProvenanceClassV1",
    "RenderOutcomeV1",
    "RenderedProvenanceSpanV1",
]
