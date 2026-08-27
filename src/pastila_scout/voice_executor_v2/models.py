"""Versioned contracts for model-free deterministic Voice V2 execution."""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.expression_catalog_v2.eligibility_models import (
    CommentaryRelationBinding,
    ExpressionEligibilityResultV1,
    ExpressionOwnerSelectionReceiptV1,
)
from pastila_scout.voice_deterministic_v2.models import (
    AcidCommentaryIRV1_1,
    ProductionAcidCommentaryIRV1_1,
    RenderedProvenanceSpanV1,
)
from pastila_scout.voice_eligibility_v2.models import (
    MechanicEligibilityClaimV1,
    VoiceEligibilityResultV1,
    VoiceOwnerSelectionReceiptV1,
    VoiceRepetitionSnapshotV1,
)
from pastila_scout.voice_fact_atoms_v2.models import VoiceFactAtomBundle
from pastila_scout.voice_governed_realization_v1 import GovernedRealizationReceiptV1
from pastila_scout.voice_workflow_v2.models import VoiceStoryBindingV1

SHA256 = r"^sha256:[0-9a-f]{64}$"
HEX_SHA256 = r"^[0-9a-f]{64}$"
ZERO_IDENTITY = "sha256:" + "0" * 64


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DeterministicBackendKindV2(StrEnum):
    DETERMINISTIC_RENDERER = "deterministic_renderer"
    GOVERNED_MODEL_REALIZER = "governed_model_realizer"


class DeterministicTerminalKindV2(StrEnum):
    GENERATED = "generated"
    SAFELY_ABSTAINED = "safely_abstained"
    INTEGRITY_FAILURE = "integrity_failure"


class ProductionActivationEntryV1(FrozenModel):
    expression_identity: str = Field(min_length=1)
    surface_identity: str = Field(min_length=1)
    eligibility_spec_identity: str = Field(pattern=SHA256)
    relationship_scope_identity: str = Field(pattern=SHA256)


class VoiceProductionActivationPolicyV1(FrozenModel):
    schema_name: Literal["pastilaacida-voice-production-activation-policy"] = (
        "pastilaacida-voice-production-activation-policy"
    )
    schema_version: Literal["1"] = "1"
    entries: tuple[ProductionActivationEntryV1, ...] = ()
    policy_identity: str = Field(default=ZERO_IDENTITY, pattern=SHA256)

    @model_validator(mode="after")
    def unique_entries(self):
        keys = [
            (item.expression_identity, item.surface_identity) for item in self.entries
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate production activation entry")
        return self

    @property
    def active_expression_count(self) -> int:
        return len({item.expression_identity for item in self.entries})

    @property
    def active_surface_count(self) -> int:
        return len({item.surface_identity for item in self.entries})


class ProofActivationEntryV1(FrozenModel):
    proof_id: str = Field(pattern=r"^P[1-8]$")
    source_record_id: str = Field(min_length=1)
    realization_program_id: str = Field(min_length=1)
    realization_program_sha256: str | None = Field(default=None, pattern=HEX_SHA256)
    expected_output_sha256: str | None = Field(default=None, pattern=HEX_SHA256)
    expected_abstention_reason: str | None = None


class VoiceProofOnlyActivationAuthorityV1(FrozenModel):
    """Non-production authority for the immutable P1-P8 proof corpus only."""

    schema_name: Literal["pastilaacida-voice-proof-only-activation-authority"] = (
        "pastilaacida-voice-proof-only-activation-authority"
    )
    schema_version: Literal["1"] = "1"
    authority_scope: Literal["proof_only"] = "proof_only"
    entries: tuple[ProofActivationEntryV1, ...] = Field(min_length=1)
    production_eligible: Literal[False] = False
    ordinary_story_eligible: Literal[False] = False
    authority_identity: str = Field(default=ZERO_IDENTITY, pattern=SHA256)

    @model_validator(mode="after")
    def unique_proofs(self):
        proof_ids = [item.proof_id for item in self.entries]
        if len(proof_ids) != len(set(proof_ids)):
            raise ValueError("duplicate proof activation entry")
        return self


class OrdinaryStoryProofActivationEntryV1(FrozenModel):
    """Exact owner-governed tuple for one ordinary, proof-corpus story."""

    event_id: int = Field(gt=0)
    semantic_draft_revision_identity: str = Field(pattern=SHA256)
    story_state_identity: str = Field(pattern=SHA256)
    adjudication_state_identity: str = Field(pattern=SHA256)
    fact_atom_bundle_identity: str = Field(pattern=SHA256)
    mechanic_claim_receipt_identity: str | None = Field(default=None, pattern=SHA256)
    program_eligibility_identity: str | None = Field(default=None, pattern=SHA256)
    program_id: str | None = None
    program_selection_receipt_identity: str | None = Field(default=None, pattern=SHA256)
    expression_eligibility_identity: str | None = Field(default=None, pattern=SHA256)
    expression_selection_receipt_identity: str | None = Field(
        default=None, pattern=SHA256
    )
    expression_identity: str | None = None
    surface_identity: str | None = None
    relationship_binding_identities: tuple[str, ...] = ()

    @model_validator(mode="after")
    def exact_selection_shape(self):
        program_values = (
            self.program_id,
            self.program_selection_receipt_identity,
            self.program_eligibility_identity,
        )
        if any(value is None for value in program_values) and any(
            value is not None for value in program_values
        ):
            raise ValueError("program tuple must be complete or explicitly absent")
        if (self.expression_identity is None) != (self.surface_identity is None):
            raise ValueError("expression and surface identities must be paired")
        if self.program_id is None and self.expression_selection_receipt_identity:
            raise ValueError("expression selection requires a selected program")
        return self


class VoiceOrdinaryStoryProofOnlyAuthorityV1(FrozenModel):
    """Non-production authority for an exact ordinary-story proof corpus."""

    schema_name: Literal["pastilaacida-voice-ordinary-story-proof-only-authority"] = (
        "pastilaacida-voice-ordinary-story-proof-only-authority"
    )
    schema_version: Literal["1"] = "1"
    authority_scope: Literal["ordinary_story_proof_only"] = "ordinary_story_proof_only"
    proof_only: Literal[True] = True
    production_eligible: Literal[False] = False
    ordinary_story_eligible: Literal[True] = True
    corpus_ledger_sha256: str = Field(pattern=HEX_SHA256)
    corpus_manifest_sha256: str = Field(pattern=HEX_SHA256)
    renderer_identity: str = Field(min_length=1)
    ir_schema_version: Literal["ACID_COMMENTARY_IR_V1_1"] = "ACID_COMMENTARY_IR_V1_1"
    entries: tuple[OrdinaryStoryProofActivationEntryV1, ...] = Field(min_length=1)
    authority_identity: str = Field(default=ZERO_IDENTITY, pattern=SHA256)

    @model_validator(mode="after")
    def exact_unique_stories(self):
        event_ids = [item.event_id for item in self.entries]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("duplicate ordinary-story proof entry")
        return self


class OrdinaryStoryProofExpressionActivationAuthorityV1(FrozenModel):
    """One exact, selected expression tuple for an ordinary-story proof."""

    schema_name: Literal[
        "pastilaacida-voice-ordinary-story-proof-expression-activation-authority"
    ] = "pastilaacida-voice-ordinary-story-proof-expression-activation-authority"
    schema_version: Literal["1"] = "1"
    proof_only: Literal[True] = True
    production_eligible: Literal[False] = False
    proof_case_identity: str = Field(min_length=1)
    proof_corpus_identity: str = Field(pattern=SHA256)
    event_id: int = Field(gt=0)
    semantic_draft_revision_identity: str = Field(pattern=SHA256)
    story_state_identity: str = Field(pattern=SHA256)
    fact_atom_bundle_identity: str = Field(pattern=SHA256)
    mechanic_claim_identity: str = Field(pattern=SHA256)
    program_eligibility_identity: str = Field(pattern=SHA256)
    program_selection_receipt_identity: str = Field(pattern=SHA256)
    selected_program_id: str = Field(min_length=1)
    selected_program_candidate_identity: str = Field(pattern=SHA256)
    expression_eligibility_identity: str = Field(pattern=SHA256)
    expression_filter_evidence_identity: str = Field(pattern=SHA256)
    expression_selection_receipt_identity: str = Field(pattern=SHA256)
    selected_expression_candidate_identity: str = Field(pattern=SHA256)
    expression_identity: str = Field(min_length=1)
    expression_scope_identity: str = Field(pattern=SHA256)
    expression_surface_identity: str = Field(min_length=1)
    catalog_overlay_identity: str = Field(pattern=HEX_SHA256)
    repetition_snapshot_identity: str = Field(pattern=SHA256)
    relation_binding_identity: str = Field(pattern=SHA256)
    renderer_identity: str = Field(min_length=1)
    ir_schema_identity: Literal["ACID_COMMENTARY_IR_V1_1"] = "ACID_COMMENTARY_IR_V1_1"
    supersedes_authority_identity: str | None = Field(default=None, pattern=SHA256)
    authority_identity: str = Field(default=ZERO_IDENTITY, pattern=SHA256)


class OrdinaryStoryProofAuthorityAmendmentV1(FrozenModel):
    """Explicit owner supersession of one tuple in an immutable proof authority."""

    schema_name: Literal[
        "pastilaacida-voice-ordinary-story-proof-authority-amendment"
    ] = "pastilaacida-voice-ordinary-story-proof-authority-amendment"
    schema_version: Literal["1"] = "1"
    proof_only: Literal[True] = True
    production_eligible: Literal[False] = False
    parent_authority_identity: str = Field(pattern=SHA256)
    event_id: int = Field(gt=0)
    semantic_draft_revision_identity: str = Field(pattern=SHA256)
    ledger_identity: str = Field(pattern=SHA256)
    fresh_snapshot_identity: str = Field(pattern=SHA256)
    superseded_program_receipt_identity: str = Field(pattern=SHA256)
    replacement_selection_kind: Literal["none"] = "none"
    replacement_program_receipt: VoiceOwnerSelectionReceiptV1
    amendment_identity: str = Field(default=ZERO_IDENTITY, pattern=SHA256)

    @model_validator(mode="after")
    def explicit_none_only(self):
        if (
            self.replacement_program_receipt.selection_kind.value != "none"
            or self.replacement_program_receipt.selected_candidate_id is not None
            or self.replacement_program_receipt.repetition_snapshot_identity
            != self.fresh_snapshot_identity
        ):
            raise ValueError("proof authority amendment must bind explicit NONE")
        return self


class VoiceDeterministicCapabilityV2(FrozenModel):
    schema_version: Literal["VOICE_EXECUTOR_CAPABILITY_V2"] = (
        "VOICE_EXECUTOR_CAPABILITY_V2"
    )
    backend_kind: Literal[DeterministicBackendKindV2.DETERMINISTIC_RENDERER] = (
        DeterministicBackendKindV2.DETERMINISTIC_RENDERER
    )
    renderer_identity: str = Field(min_length=1)
    supported_ir_versions: tuple[Literal["ACID_COMMENTARY_IR_V1_1"], ...] = (
        "ACID_COMMENTARY_IR_V1_1",
    )
    supported_request_versions: tuple[Literal["VOICE_EXECUTOR_REQUEST_V2"], ...] = (
        "VOICE_EXECUTOR_REQUEST_V2",
    )
    activation_policy_identity: str = Field(pattern=SHA256)
    proof_activation_authority_identity: str | None = Field(
        default=None, pattern=SHA256
    )
    model_calls: Literal[0] = 0
    provider_calls: Literal[0] = 0
    model_loads: Literal[0] = 0


class VoiceDeterministicExecutionRequestV2(FrozenModel):
    schema_version: Literal["VOICE_EXECUTOR_REQUEST_V2"] = "VOICE_EXECUTOR_REQUEST_V2"
    story_binding: VoiceStoryBindingV1
    fact_atom_bundle: VoiceFactAtomBundle
    relationship_bindings: tuple[CommentaryRelationBinding, ...] = ()
    program_eligibility: VoiceEligibilityResultV1
    mechanic_claim: MechanicEligibilityClaimV1 | None = None
    program_selection: VoiceOwnerSelectionReceiptV1
    expression_eligibility: ExpressionEligibilityResultV1 | None = None
    expression_selection: ExpressionOwnerSelectionReceiptV1 | None = None
    repetition_snapshot: VoiceRepetitionSnapshotV1
    activation_policy: VoiceProductionActivationPolicyV1
    proof_activation_authority: VoiceProofOnlyActivationAuthorityV1 | None = None
    expected_renderer_identity: str = Field(min_length=1)
    expected_ir_version: Literal["ACID_COMMENTARY_IR_V1_1"] = "ACID_COMMENTARY_IR_V1_1"
    ir: AcidCommentaryIRV1_1 | ProductionAcidCommentaryIRV1_1 | None = None
    request_identity: str = Field(default=ZERO_IDENTITY, pattern=SHA256)

    @model_validator(mode="after")
    def expression_pair(self):
        if (self.expression_eligibility is None) != (self.expression_selection is None):
            raise ValueError("expression eligibility and selection must be paired")
        if self.proof_activation_authority is not None and not isinstance(
            self.ir, AcidCommentaryIRV1_1
        ):
            raise ValueError("proof activation authority requires frozen proof IR")
        return self


class _TerminalResult(FrozenModel):
    backend_kind: DeterministicBackendKindV2 = (
        DeterministicBackendKindV2.DETERMINISTIC_RENDERER
    )
    renderer_identity: str = Field(min_length=1)
    request_identity: str = Field(pattern=SHA256)
    model_calls: int = Field(default=0, ge=0, le=1)
    provider_calls: int = Field(default=0, ge=0, le=1)
    model_loads: int = Field(default=0, ge=0, le=1)
    model_identity: str | None = Field(default=None, min_length=1)
    realization_receipt_identity: str | None = Field(default=None, pattern=SHA256)
    realization_receipt: GovernedRealizationReceiptV1 | None = None
    acceptance_blocked: bool
    result_identity: str = Field(default=ZERO_IDENTITY, pattern=SHA256)

    @model_validator(mode="after")
    def truthful_execution_backend(self):
        counts = (self.model_calls, self.provider_calls, self.model_loads)
        if self.backend_kind is DeterministicBackendKindV2.DETERMINISTIC_RENDERER:
            if (
                any(counts)
                or self.model_identity
                or self.realization_receipt_identity
                or self.realization_receipt is not None
            ):
                raise ValueError("deterministic result cannot report model activity")
        elif (
            counts != (1, 1, 1)
            or self.model_identity is None
            or self.realization_receipt_identity is None
            or self.realization_receipt is None
            or self.realization_receipt.receipt_identity
            != self.realization_receipt_identity
        ):
            raise ValueError("governed model result lacks execution authority")
        return self


class VoiceGeneratedResultV2(_TerminalResult):
    kind: Literal[DeterministicTerminalKindV2.GENERATED] = (
        DeterministicTerminalKindV2.GENERATED
    )
    acceptance_blocked: Literal[False] = False
    canonical_ir_identity: str = Field(pattern=HEX_SHA256)
    rendered_utf8: bytes = Field(min_length=1)
    rendered_sha256: str = Field(pattern=HEX_SHA256)
    provenance: tuple[RenderedProvenanceSpanV1, ...] = Field(min_length=1)
    validation_identity: str = Field(pattern=SHA256)


class VoiceSafelyAbstainedResultV2(_TerminalResult):
    kind: Literal[DeterministicTerminalKindV2.SAFELY_ABSTAINED] = (
        DeterministicTerminalKindV2.SAFELY_ABSTAINED
    )
    acceptance_blocked: Literal[True] = True
    reason_code: str = Field(min_length=1)
    governed_identity: str = Field(min_length=1)


class VoiceIntegrityFailureResultV2(_TerminalResult):
    kind: Literal[DeterministicTerminalKindV2.INTEGRITY_FAILURE] = (
        DeterministicTerminalKindV2.INTEGRITY_FAILURE
    )
    acceptance_blocked: Literal[True] = True
    failure_code: str = Field(min_length=1)
    failed_identity: str = Field(min_length=1)


VoiceDeterministicTerminalResultV2 = Annotated[
    VoiceGeneratedResultV2
    | VoiceSafelyAbstainedResultV2
    | VoiceIntegrityFailureResultV2,
    Field(discriminator="kind"),
]


class VoiceDeterministicPreviewSidecarV2(FrozenModel):
    schema_name: Literal["pastilaacida-voice-deterministic-preview-sidecar"] = (
        "pastilaacida-voice-deterministic-preview-sidecar"
    )
    schema_version: Literal["2"] = "2"
    source_semantic_draft_revision_identity: str = Field(pattern=SHA256)
    event_id: int = Field(gt=0)
    factual_summary_identity: str = Field(pattern=SHA256)
    event_authority_identity: str = Field(min_length=1)
    background_authority_identity: str | None = None
    fact_atom_bundle_identity: str = Field(pattern=SHA256)
    relationship_binding_identities: tuple[str, ...]
    program_eligibility_identity: str = Field(pattern=SHA256)
    program_selection_receipt_identity: str = Field(pattern=SHA256)
    expression_eligibility_identity: str | None = Field(default=None, pattern=SHA256)
    expression_selection_receipt_identity: str | None = Field(
        default=None, pattern=SHA256
    )
    repetition_snapshot_identity: str = Field(pattern=SHA256)
    activation_policy_identity: str = Field(pattern=SHA256)
    request_identity: str = Field(pattern=SHA256)
    terminal_result: VoiceDeterministicTerminalResultV2
    preview_only: Literal[True] = True
    authored_v2_mutated: Literal[False] = False
    repetition_budget_consumed: Literal[False] = False
    sidecar_identity: str = Field(default=ZERO_IDENTITY, pattern=SHA256)
