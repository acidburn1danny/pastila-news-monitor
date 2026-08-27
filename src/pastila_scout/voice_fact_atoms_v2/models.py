"""Closed contracts for deterministic Voice fact-atom adjudication."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_NAME = "pastilaacida-voice-fact-atom-bundle"
SCHEMA_VERSION = "1"
EXTRACTION_POLICY_VERSION = "voice-fact-candidate-extraction-v1"
EXTRACTION_POLICY_VERSION_V2 = "voice-fact-candidate-extraction-v2"
ADJUDICATION_POLICY_VERSION = "voice-fact-atom-adjudication-v1"
_SHA = r"^sha256:[0-9a-f]{64}$"


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorityClass(StrEnum):
    EVENT = "event_authority"
    BACKGROUND = "commentary_background_authority"


class CandidateKind(StrEnum):
    EXACT_SPAN = "exact_span"
    NAMED_ENTITY = "named_entity"
    COMPLETE_QUANTITY = "complete_quantity"
    ATTRIBUTION_MARKER = "attribution_marker"
    ALLEGATION_MARKER = "allegation_marker"
    UNCERTAINTY_MARKER = "uncertainty_marker"
    DATE_TIME = "date_time"
    REPEATED_SURFACE = "repeated_surface"


class AtomKind(StrEnum):
    ACTOR_ENTITY = "actor_entity"
    PROFESSIONAL_OR_INSTITUTIONAL_ROLE = "professional_or_institutional_role"
    EVENT_PROPOSITION = "event_proposition"
    COMPLETE_QUANTITY = "complete_quantity"
    ATTRIBUTION = "attribution"
    ALLEGATION_STATUS = "allegation_status"
    UNCERTAINTY_STATUS = "uncertainty_status"
    LEGAL_STATUS = "legal_status"
    OPERATIONAL_STATUS = "operational_status"
    CHRONOLOGY = "chronology"
    CAUSAL_BOUNDARY = "causal_boundary"
    NEGATIVE_BOUNDARY = "negative_boundary"
    BACKGROUND_PROPOSITION = "background_proposition"
    PROFESSIONAL_DOMAIN_PREMISE = "professional_domain_premise"


class AdjudicationAction(StrEnum):
    ACCEPT = "accept_as_typed_atom"
    RECLASSIFY = "reclassify"
    SPLIT = "split"
    MERGE = "merge"
    REJECT = "reject"


class AuthorityPassageV1(_Frozen):
    authority_class: AuthorityClass
    # Core V2 authority fingerprints predate workflow SHA-URI identities and
    # are stored as bare 64-hex digests in historical/native V2 artifacts.
    authority_identity: str = Field(min_length=1)
    source_identity: str = Field(min_length=1)
    passage: str = Field(min_length=1)
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def valid_span(self):
        if self.end <= self.start or self.end - self.start != len(self.passage):
            raise ValueError("authority span length mismatch")
        return self


class SurfaceCandidateV1(_Frozen):
    candidate_id: str = Field(min_length=1)
    kind: CandidateKind
    evidence: AuthorityPassageV1
    normalized_key: str = Field(min_length=1)
    requires_semantic_adjudication: Literal[True] = True
    extraction_receipt_identity: str = Field(pattern=_SHA)


class CompleteQuantityV1(_Frozen):
    exact_surface: str = Field(min_length=1)
    numeric_surface: str = Field(min_length=1)
    approximation: str | None = None
    bound_semantics: Literal["exact", "approximate", "lower_bound", "upper_bound"]
    unit_or_currency: str = Field(min_length=1)
    denominator: str | None = None
    period: str | None = None
    subject_scope: str = Field(min_length=1)
    attribution_atom_id: str | None = None
    epistemic_atom_id: str | None = None

    @model_validator(mode="after")
    def complete(self):
        if self.numeric_surface not in self.exact_surface:
            raise ValueError("quantity numeric surface was detached")
        if self.unit_or_currency not in self.exact_surface:
            raise ValueError("quantity unit/currency was detached")
        if self.approximation and self.approximation not in self.exact_surface:
            raise ValueError("quantity approximation was detached")
        return self


class FactAtomV1(_Frozen):
    atom_id: str = Field(min_length=1)
    kind: AtomKind
    proposition: str = Field(min_length=1)
    authority_class: AuthorityClass
    evidence: tuple[AuthorityPassageV1, ...] = Field(min_length=1)
    candidate_ids: tuple[str, ...] = Field(min_length=1)
    quantity: CompleteQuantityV1 | None = None
    qualification_target_atom_ids: tuple[str, ...] = ()
    prohibits_event_projection: bool = False

    @model_validator(mode="after")
    def semantics(self):
        if self.kind is AtomKind.COMPLETE_QUANTITY and self.quantity is None:
            raise ValueError("complete quantity atom requires indivisible quantity")
        if self.kind is not AtomKind.COMPLETE_QUANTITY and self.quantity is not None:
            raise ValueError("quantity payload belongs only to quantity atoms")
        if (
            self.authority_class is AuthorityClass.BACKGROUND
            and not self.prohibits_event_projection
        ):
            raise ValueError("background atom must prohibit event projection")
        if (
            self.kind
            in {
                AtomKind.ALLEGATION_STATUS,
                AtomKind.UNCERTAINTY_STATUS,
                AtomKind.CAUSAL_BOUNDARY,
                AtomKind.NEGATIVE_BOUNDARY,
            }
            and not self.qualification_target_atom_ids
        ):
            raise ValueError("epistemic/boundary atom requires an exact target")
        return self


class AdjudicationDecisionV1(_Frozen):
    decision_id: str = Field(min_length=1)
    action: AdjudicationAction
    candidate_ids: tuple[str, ...] = Field(min_length=1)
    resulting_atom_ids: tuple[str, ...] = ()
    adjudicator_identity: str = Field(min_length=1)
    decided_at: datetime
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def result_shape(self):
        if self.action is AdjudicationAction.REJECT and self.resulting_atom_ids:
            raise ValueError("rejected candidate cannot produce atoms")
        if self.action is not AdjudicationAction.REJECT and not self.resulting_atom_ids:
            raise ValueError("accepted adjudication must identify result atoms")
        return self


class AdjudicationReceiptV1(_Frozen):
    schema_name: Literal["pastilaacida-voice-fact-atom-adjudication"] = (
        "pastilaacida-voice-fact-atom-adjudication"
    )
    schema_version: Literal["1"] = "1"
    prior_bundle_identity: str | None = Field(default=None, pattern=_SHA)
    decisions: tuple[AdjudicationDecisionV1, ...] = Field(min_length=1)
    receipt_identity: str = Field(pattern=_SHA)


class VoiceFactAtomBundleV1(_Frozen):
    schema_name: Literal["pastilaacida-voice-fact-atom-bundle"] = SCHEMA_NAME
    schema_version: Literal["1"] = SCHEMA_VERSION
    revision: int = Field(ge=1)
    semantic_draft_revision_identity: str = Field(pattern=_SHA)
    event_id: int = Field(gt=0)
    story_position: int = Field(gt=0)
    factual_summary_identity: str = Field(pattern=_SHA)
    event_authority_identity: str = Field(min_length=1)
    background_authority_identity: str | None = Field(default=None, pattern=_SHA)
    extraction_policy_version: Literal["voice-fact-candidate-extraction-v1"] = (
        EXTRACTION_POLICY_VERSION
    )
    adjudication_policy_version: Literal["voice-fact-atom-adjudication-v1"] = (
        ADJUDICATION_POLICY_VERSION
    )
    candidates: tuple[SurfaceCandidateV1, ...]
    atoms: tuple[FactAtomV1, ...]
    adjudication_receipt_identities: tuple[str, ...] = ()
    bundle_identity: str = Field(pattern=_SHA)

    @model_validator(mode="after")
    def integrity(self):
        candidate_ids = {item.candidate_id for item in self.candidates}
        atom_ids = {item.atom_id for item in self.atoms}
        if len(candidate_ids) != len(self.candidates) or len(atom_ids) != len(
            self.atoms
        ):
            raise ValueError("duplicate candidate or atom identity")
        if any(not set(atom.candidate_ids) <= candidate_ids for atom in self.atoms):
            raise ValueError("orphan atom candidate provenance")
        if any(
            not set(atom.qualification_target_atom_ids) <= atom_ids
            for atom in self.atoms
        ):
            raise ValueError("orphan epistemic target")
        return self


class VoiceFactAtomBundleV2(VoiceFactAtomBundleV1):
    """Typed-field candidate inventory; historical V1 meaning is unchanged."""

    schema_version: Literal["2"] = "2"
    extraction_policy_version: Literal["voice-fact-candidate-extraction-v2"] = (
        EXTRACTION_POLICY_VERSION_V2
    )
    extraction_source_input_contract: Literal[
        "typed-authority-fields-v2"
    ] = "typed-authority-fields-v2"


VoiceFactAtomBundle = Annotated[
    VoiceFactAtomBundleV1 | VoiceFactAtomBundleV2,
    Field(discriminator="schema_version"),
]
