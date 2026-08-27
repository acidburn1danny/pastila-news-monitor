"""Versioned, structured Desktop actions for owner Voice adjudication."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.voice_adjudication_v2 import CandidateOwnerDispositionV1
from pastila_scout.voice_deterministic_v2.models import MechanicIdV1
from pastila_scout.voice_eligibility_v2.models import AtomRoleBindingV1
from pastila_scout.voice_fact_atoms_v2.models import AtomKind, CompleteQuantityV1


class VoiceDesktopFactAtomInputV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    atom_id: str = Field(min_length=1)
    atom_kind: AtomKind
    quantity: CompleteQuantityV1 | None = None
    qualification_target_atom_ids: tuple[str, ...] = ()
    prohibits_event_projection: bool = False

    @model_validator(mode="after")
    def complete_payload(self):
        if (self.atom_kind is AtomKind.COMPLETE_QUANTITY) != (
            self.quantity is not None
        ):
            raise ValueError("quantity payload and atom kind differ")
        return self


class VoiceDesktopAdjudicationActionV1(BaseModel):
    """No field is inferred: the owner supplies the complete governed payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_name: Literal["pastilaacida-voice-desktop-adjudication-action"] = (
        "pastilaacida-voice-desktop-adjudication-action"
    )
    schema_version: Literal["1"] = "1"
    event_id: int = Field(gt=0)
    action: Literal[
        "decide_fact",
        "finalize_facts",
        "confirm_mechanic_claim",
        "finalize_claims",
        "choose_no_claim",
    ]
    candidate_identity: str | None = None
    disposition: CandidateOwnerDispositionV1 | None = None
    atom_input: VoiceDesktopFactAtomInputV1 | None = None
    governed_object_or_scope: str | None = None
    decision_rationale: str | None = None
    actor_or_subject_atom_ids: tuple[str, ...] = ()
    chronology_atom_ids: tuple[str, ...] = ()
    uncertainty_target_atom_ids: tuple[str, ...] = ()
    attribution_atom_ids: tuple[str, ...] = ()
    mechanic_id: MechanicIdV1 | None = None
    atom_roles: tuple[AtomRoleBindingV1, ...] = ()
    satisfied_boundary_codes: tuple[str, ...] = ()
    owner_identity: str = Field(min_length=1)
    occurred_at: datetime
    supersession_reason: str | None = None
    no_claim_reason: str | None = None

    @model_validator(mode="after")
    def exact_action_shape(self):
        if self.occurred_at.tzinfo is None:
            raise ValueError("adjudication timestamp must be timezone-aware")
        if self.action == "decide_fact":
            if self.candidate_identity is None or self.disposition is None:
                raise ValueError("fact decision is incomplete")
            accepted = self.disposition is CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM
            if accepted != (self.atom_input is not None):
                raise ValueError("typed fact acceptance requires exactly one atom")
            if not self.decision_rationale:
                raise ValueError("fact decision requires an owner rationale")
        elif self.action == "confirm_mechanic_claim":
            if self.mechanic_id is None or not self.atom_roles:
                raise ValueError("mechanic confirmation is incomplete")
        elif self.action == "choose_no_claim":
            if not self.no_claim_reason:
                raise ValueError("NO CLAIM requires an owner reason")
        return self


__all__ = ["VoiceDesktopAdjudicationActionV1", "VoiceDesktopFactAtomInputV1"]
