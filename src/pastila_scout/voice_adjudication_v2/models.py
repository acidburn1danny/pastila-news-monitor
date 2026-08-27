"""Owner-authoritative contracts for ordinary-story Voice adjudication."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.voice_eligibility_v2.models import (
    AtomRoleBindingV1,
    MechanicEligibilityClaimV1,
    VoiceEligibilityResultV1,
    VoiceRepetitionSnapshotV1,
)
from pastila_scout.voice_fact_atoms_v2.extraction_v2 import TypedAuthorityFieldInputV2
from pastila_scout.voice_fact_atoms_v2.models import (
    AuthorityClass,
    CandidateKind,
    FactAtomV1,
    SurfaceCandidateV1,
    VoiceFactAtomBundleV1,
    VoiceFactAtomBundleV2,
)
from pastila_scout.voice_fact_atoms_v2.persistence import canonical_identity
from pastila_scout.voice_workflow_v2.models import VoiceStoryBindingV1

SHA = r"^sha256:[0-9a-f]{64}$"
ZERO = "sha256:" + "0" * 64


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AdjudicationLifecycleV1(StrEnum):
    CANDIDATES_EXTRACTED = "candidates_extracted"
    FACT_ATOMS_PARTIAL = "fact_atoms_partial"
    FACT_ATOMS_FINALIZED = "fact_atoms_finalized"
    MECHANIC_CLAIMS_PARTIAL = "mechanic_claims_partial"
    MECHANIC_CLAIMS_FINALIZED = "mechanic_claims_finalized"
    NO_CLAIM = "no_claim"
    STALE = "stale"


class CandidateOwnerDispositionV1(StrEnum):
    ACCEPT_TYPED_ATOM = "accept_typed_atom"
    REJECT = "reject"
    REQUIRES_QUALIFICATION = "requires_qualification"


class PriorCandidateProvenanceClassV1(StrEnum):
    NONCANONICAL_AD_HOC = "NONCANONICAL_AD_HOC"


class OwnerDecisionRebindAuthorizationV1(StrEnum):
    OWNER_AUTHORIZED_DECISION_REBIND = "OWNER_AUTHORIZED_DECISION_REBIND"


class AuthorityTextV1(_Frozen):
    authority_class: AuthorityClass
    # Semantic Draft V2 historically stores the Core authority fingerprint as
    # the bare 64-hex digest; do not reinterpret it as a workflow SHA URI.
    authority_identity: str = Field(min_length=1)
    source_identity: str = Field(min_length=1)
    text: str = Field(min_length=1)
    text_sha256: str = Field(pattern=SHA)


class FactAtomOwnerReceiptV1(_Frozen):
    schema_name: Literal["pastilaacida-voice-fact-atom-owner-receipt"] = (
        "pastilaacida-voice-fact-atom-owner-receipt"
    )
    schema_version: Literal["1"] = "1"
    semantic_draft_revision_identity: str = Field(pattern=SHA)
    event_authority_identity: str = Field(min_length=1)
    candidate_identity: str = Field(min_length=1)
    exact_source_span_sha256: str = Field(pattern=SHA)
    disposition: CandidateOwnerDispositionV1
    resulting_atom: FactAtomV1 | None = None
    governed_object_or_scope: str | None = None
    actor_or_subject_atom_ids: tuple[str, ...] = ()
    chronology_atom_ids: tuple[str, ...] = ()
    uncertainty_target_atom_ids: tuple[str, ...] = ()
    attribution_atom_ids: tuple[str, ...] = ()
    adjudicator_identity: str = Field(min_length=1)
    adjudicated_at: datetime
    prior_receipt_identity: str | None = Field(default=None, pattern=SHA)
    supersession_reason: str | None = None
    receipt_identity: str = Field(default=ZERO, pattern=SHA)

    @model_validator(mode="after")
    def decision_shape(self):
        accepted = self.disposition is CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM
        if accepted != (self.resulting_atom is not None):
            raise ValueError("accepted fact-atom decision requires exactly one atom")
        if (self.prior_receipt_identity is None) != (self.supersession_reason is None):
            raise ValueError("adjudication revision requires prior receipt and reason")
        return self


class FactAtomOwnerReceiptV2(_Frozen):
    schema_name: Literal["pastilaacida-voice-fact-atom-owner-receipt"] = (
        "pastilaacida-voice-fact-atom-owner-receipt"
    )
    schema_version: Literal["2"] = "2"
    semantic_draft_revision_identity: str = Field(pattern=SHA)
    event_authority_identity: str = Field(min_length=1)
    candidate_identity: str = Field(min_length=1)
    exact_source_span_sha256: str = Field(pattern=SHA)
    disposition: CandidateOwnerDispositionV1
    resulting_atom: FactAtomV1 | None = None
    governed_object_or_scope: str | None = None
    actor_or_subject_atom_ids: tuple[str, ...] = ()
    chronology_atom_ids: tuple[str, ...] = ()
    uncertainty_target_atom_ids: tuple[str, ...] = ()
    attribution_atom_ids: tuple[str, ...] = ()
    adjudicator_identity: str = Field(min_length=1)
    adjudicated_at: datetime
    decision_rationale: str = Field(min_length=1)
    prior_receipt_identity: str | None = Field(default=None, pattern=SHA)
    supersession_reason: str | None = None
    receipt_identity: str = Field(default=ZERO, pattern=SHA)

    @model_validator(mode="after")
    def decision_shape(self):
        if not self.decision_rationale.strip():
            raise ValueError("V2 fact-atom decision requires a non-empty rationale")
        accepted = self.disposition is CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM
        if accepted != (self.resulting_atom is not None):
            raise ValueError("accepted fact-atom decision requires exactly one atom")
        if (self.prior_receipt_identity is None) != (self.supersession_reason is None):
            raise ValueError("adjudication revision requires prior receipt and reason")
        return self


FactAtomOwnerReceipt = Annotated[
    FactAtomOwnerReceiptV1 | FactAtomOwnerReceiptV2,
    Field(discriminator="schema_version"),
]


class FactAtomOwnerDecisionRebindProvenanceV1(_Frozen):
    schema_name: Literal[
        "pastilaacida-voice-fact-atom-owner-decision-rebind-provenance"
    ] = "pastilaacida-voice-fact-atom-owner-decision-rebind-provenance"
    schema_version: Literal["1"] = "1"
    story_identity: str = Field(pattern=SHA)
    prior_candidate_identity: str = Field(min_length=1)
    prior_candidate_provenance_class: PriorCandidateProvenanceClassV1
    target_candidate_identity: str = Field(min_length=1)
    target_extraction_policy: Literal["voice-fact-candidate-extraction-v2"] = (
        "voice-fact-candidate-extraction-v2"
    )
    source_identity: str = Field(min_length=1)
    field_name: Literal["title", "summary"]
    passage: str = Field(min_length=1)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    candidate_kind: CandidateKind
    disposition: CandidateOwnerDispositionV1
    decision_rationale: str = Field(min_length=1)
    owner_authorization: OwnerDecisionRebindAuthorizationV1
    target_receipt_identity: str = Field(pattern=SHA)
    provenance_identity: str = Field(default=ZERO, pattern=SHA)

    @model_validator(mode="after")
    def occurrence_shape(self):
        if self.end <= self.start:
            raise ValueError("rebind occurrence range is invalid")
        if not self.decision_rationale.strip():
            raise ValueError("rebind rationale cannot be blank")
        return self


class MechanicClaimOwnerReceiptV1(_Frozen):
    schema_name: Literal["pastilaacida-voice-mechanic-claim-owner-receipt"] = (
        "pastilaacida-voice-mechanic-claim-owner-receipt"
    )
    schema_version: Literal["1"] = "1"
    semantic_draft_revision_identity: str = Field(pattern=SHA)
    fact_atom_bundle_identity: str = Field(pattern=SHA)
    mechanic_claim: MechanicEligibilityClaimV1
    confirmed_role_bindings: tuple[AtomRoleBindingV1, ...]
    confirmed_boundary_codes: tuple[str, ...]
    adjudicator_identity: str = Field(min_length=1)
    adjudicated_at: datetime
    prior_receipt_identity: str | None = Field(default=None, pattern=SHA)
    supersession_reason: str | None = None
    receipt_identity: str = Field(default=ZERO, pattern=SHA)

    @model_validator(mode="after")
    def exact_claim(self):
        if (
            self.mechanic_claim.atom_roles != self.confirmed_role_bindings
            or self.mechanic_claim.satisfied_boundary_codes
            != self.confirmed_boundary_codes
            or self.mechanic_claim.fact_atom_bundle_identity
            != self.fact_atom_bundle_identity
            or self.mechanic_claim.adjudication_receipt_identity
            != self.receipt_identity
        ):
            raise ValueError("mechanic receipt does not exactly describe its claim")
        if (self.prior_receipt_identity is None) != (self.supersession_reason is None):
            raise ValueError("claim revision requires prior receipt and reason")
        return self


class VoiceStoryAdjudicationStateV1(_Frozen):
    schema_name: Literal["pastilaacida-voice-story-adjudication-state"] = (
        "pastilaacida-voice-story-adjudication-state"
    )
    schema_version: Literal["1"] = "1"
    lifecycle: AdjudicationLifecycleV1
    binding: VoiceStoryBindingV1
    authority_texts: tuple[AuthorityTextV1, ...] = Field(min_length=1)
    candidates: tuple[SurfaceCandidateV1, ...]
    fact_atom_receipts: tuple[FactAtomOwnerReceipt, ...] = ()
    fact_atom_bundle: VoiceFactAtomBundleV1
    mechanic_claim_receipts: tuple[MechanicClaimOwnerReceiptV1, ...] = ()
    mechanic_claims: tuple[MechanicEligibilityClaimV1, ...] = ()
    repetition_snapshot: VoiceRepetitionSnapshotV1
    eligibility: VoiceEligibilityResultV1 | None = None
    explicit_no_claim_reason: str | None = None
    stale_reason: str | None = None
    prior_state_identity: str | None = Field(default=None, pattern=SHA)
    state_identity: str = Field(default=ZERO, pattern=SHA)

    @model_validator(mode="after")
    def lifecycle_integrity(self):
        for receipt in self.fact_atom_receipts:
            if receipt.receipt_identity != canonical_identity(
                receipt.model_copy(update={"receipt_identity": ZERO})
            ):
                raise ValueError("fact-atom receipt identity mismatch")
        for receipt in self.mechanic_claim_receipts:
            normalized = receipt.model_copy(
                update={
                    "receipt_identity": ZERO,
                    "mechanic_claim": receipt.mechanic_claim.model_copy(
                        update={
                            "adjudication_receipt_identity": ZERO,
                            "claim_identity": ZERO,
                        }
                    ),
                }
            )
            if receipt.receipt_identity != canonical_identity(normalized):
                raise ValueError("mechanic receipt identity mismatch")
        if self.fact_atom_bundle.candidates != self.candidates:
            raise ValueError("candidate inventory and fact bundle differ")
        if self.binding.semantic_draft_revision_identity != (
            self.fact_atom_bundle.semantic_draft_revision_identity
        ):
            raise ValueError("adjudication belongs to another story revision")
        if self.lifecycle is AdjudicationLifecycleV1.NO_CLAIM:
            if not self.explicit_no_claim_reason or self.mechanic_claims:
                raise ValueError("no-claim disposition is malformed")
        elif self.explicit_no_claim_reason is not None:
            raise ValueError("no-claim reason belongs only to no-claim state")
        if (self.lifecycle is AdjudicationLifecycleV1.STALE) != bool(self.stale_reason):
            raise ValueError("stale adjudication state is malformed")
        if self.eligibility is not None and (
            self.eligibility.fact_atom_bundle_identity
            != self.fact_atom_bundle.bundle_identity
            or self.eligibility.repetition_snapshot_identity
            != self.repetition_snapshot.snapshot_identity
        ):
            raise ValueError("eligibility is stale")
        return self


class VoiceStoryAdjudicationStateV2(VoiceStoryAdjudicationStateV1):
    schema_version: Literal["2"] = "2"
    extraction_fields: tuple[TypedAuthorityFieldInputV2, ...] = Field(min_length=1)
    fact_atom_bundle: VoiceFactAtomBundleV2

    @model_validator(mode="after")
    def typed_field_inventory(self):
        source_ids = {item.source_identity for item in self.extraction_fields}
        if any(
            candidate.evidence.source_identity not in source_ids
            for candidate in self.candidates
        ):
            raise ValueError("V2 candidate is outside typed authority fields")
        if len(source_ids) != len(self.extraction_fields):
            raise ValueError("duplicate typed authority field identity")
        return self


class VoiceStoryAdjudicationStateV3(VoiceStoryAdjudicationStateV2):
    """V2 typed extraction plus immutable owner-decision rebind lineage."""

    schema_version: Literal["3"] = "3"
    fact_atom_rebind_provenance: tuple[
        FactAtomOwnerDecisionRebindProvenanceV1, ...
    ] = ()

    @model_validator(mode="after")
    def rebind_integrity(self):
        priors: set[str] = set()
        targets: set[str] = set()
        pairs: set[tuple[str, str]] = set()
        candidate_by_id = {item.candidate_id: item for item in self.candidates}
        receipt_by_id = {
            item.receipt_identity: item for item in self.fact_atom_receipts
        }
        field_by_source = {
            item.source_identity: item for item in self.extraction_fields
        }
        for provenance in self.fact_atom_rebind_provenance:
            normalized = provenance.model_copy(update={"provenance_identity": ZERO})
            if provenance.provenance_identity != canonical_identity(normalized):
                raise ValueError("rebind provenance identity mismatch")
            pair = (
                provenance.prior_candidate_identity,
                provenance.target_candidate_identity,
            )
            if (
                provenance.prior_candidate_identity in priors
                or provenance.target_candidate_identity in targets
                or pair in pairs
            ):
                raise ValueError("rebind provenance is not one-to-one")
            priors.add(provenance.prior_candidate_identity)
            targets.add(provenance.target_candidate_identity)
            pairs.add(pair)
            candidate = candidate_by_id.get(provenance.target_candidate_identity)
            receipt = receipt_by_id.get(provenance.target_receipt_identity)
            field = field_by_source.get(provenance.source_identity)
            if candidate is None or receipt is None or field is None:
                raise ValueError("rebind target candidate, receipt, or field is missing")
            if (
                provenance.story_identity
                != self.binding.semantic_draft_revision_identity
                or field.field_name != provenance.field_name
                or field.text[provenance.start : provenance.end]
                != provenance.passage
                or candidate.evidence.source_identity != provenance.source_identity
                or candidate.evidence.passage != provenance.passage
                or candidate.evidence.start != provenance.start
                or candidate.evidence.end != provenance.end
                or candidate.kind is not provenance.candidate_kind
            ):
                raise ValueError("rebind occurrence does not match canonical candidate")
            if (
                receipt.candidate_identity != provenance.target_candidate_identity
                or receipt.disposition is not provenance.disposition
                or not isinstance(receipt, FactAtomOwnerReceiptV2)
                or receipt.decision_rationale != provenance.decision_rationale
            ):
                raise ValueError("rebind provenance and target receipt disagree")
        return self


VoiceStoryAdjudicationState = Annotated[
    VoiceStoryAdjudicationStateV1
    | VoiceStoryAdjudicationStateV2
    | VoiceStoryAdjudicationStateV3,
    Field(discriminator="schema_version"),
]


__all__ = [
    "AdjudicationLifecycleV1",
    "AuthorityTextV1",
    "CandidateOwnerDispositionV1",
    "FactAtomOwnerDecisionRebindProvenanceV1",
    "FactAtomOwnerReceiptV1",
    "FactAtomOwnerReceiptV2",
    "MechanicClaimOwnerReceiptV1",
    "OwnerDecisionRebindAuthorizationV1",
    "PriorCandidateProvenanceClassV1",
    "VoiceStoryAdjudicationStateV1",
    "VoiceStoryAdjudicationStateV2",
    "VoiceStoryAdjudicationStateV3",
]
