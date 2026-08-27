"""Fail-closed contracts for deterministic Voice V2 eligibility and selection."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.voice_deterministic_v2.models import MechanicIdV1

SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"
ZERO_IDENTITY = "sha256:" + "0" * 64


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EligibilityStatusV1(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"


class SelectionKindV1(StrEnum):
    PROGRAM = "program"
    NONE = "none"


class EnrichmentStatusV1(StrEnum):
    INACTIVE = "inactive"


class AtomRoleBindingV1(FrozenModel):
    role: str = Field(min_length=1)
    atom_ids: tuple[str, ...] = Field(min_length=1)


class MechanicEligibilityClaimV1(FrozenModel):
    schema_version: Literal["VOICE_MECHANIC_ELIGIBILITY_CLAIM_V1"] = (
        "VOICE_MECHANIC_ELIGIBILITY_CLAIM_V1"
    )
    fact_atom_bundle_identity: str = Field(pattern=SHA256_PATTERN)
    mechanic_id: MechanicIdV1
    atom_roles: tuple[AtomRoleBindingV1, ...] = Field(min_length=1)
    satisfied_boundary_codes: tuple[str, ...] = ()
    adjudication_receipt_identity: str = Field(pattern=SHA256_PATTERN)
    claim_identity: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_roles(self):
        roles = [item.role for item in self.atom_roles]
        if len(roles) != len(set(roles)):
            raise ValueError("duplicate mechanic atom role")
        atom_ids = [atom_id for item in self.atom_roles for atom_id in item.atom_ids]
        if len(atom_ids) != len(set(atom_ids)):
            raise ValueError("one atom cannot satisfy multiple mechanic roles")
        if tuple(sorted(set(self.satisfied_boundary_codes))) != (
            self.satisfied_boundary_codes
        ):
            raise ValueError("boundary codes must be sorted and unique")
        return self


class RepetitionUseV1(FrozenModel):
    episode_ordinal: int = Field(ge=1)
    story_position: int = Field(ge=1)
    mechanic_id: MechanicIdV1
    program_id: str = Field(min_length=1)
    cadence_signature: str = Field(min_length=1)
    surface_ids: tuple[str, ...] = ()
    enrichment_identity: str | None = None


class VoiceRepetitionSnapshotV1(FrozenModel):
    schema_version: Literal["VOICE_REPETITION_SNAPSHOT_V1"] = (
        "VOICE_REPETITION_SNAPSHOT_V1"
    )
    current_episode_ordinal: int = Field(ge=1)
    current_story_position: int = Field(ge=1)
    history_complete: Literal[True] = True
    uses: tuple[RepetitionUseV1, ...] = ()
    snapshot_identity: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_history(self):
        keys = []
        for use in self.uses:
            if use.episode_ordinal > self.current_episode_ordinal or (
                use.episode_ordinal == self.current_episode_ordinal
                and use.story_position >= self.current_story_position
            ):
                raise ValueError("repetition history contains a future use")
            keys.append(
                (
                    use.episode_ordinal,
                    use.story_position,
                    use.mechanic_id,
                    use.program_id,
                    use.cadence_signature,
                    use.surface_ids,
                    use.enrichment_identity,
                )
            )
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate repetition history use")
        return self


class EligibilityOutcomeV1(FrozenModel):
    subject_id: str = Field(min_length=1)
    status: EligibilityStatusV1
    reason_codes: tuple[str, ...]


class ProgramCandidateV1(FrozenModel):
    candidate_id: str = Field(pattern=SHA256_PATTERN)
    program_id: str = Field(min_length=1)
    mechanic_id: MechanicIdV1
    cadence_signature: str = Field(min_length=1)
    surface_ids: tuple[str, ...]
    repetition_signature: str = Field(min_length=1)


class OptionalEnrichmentExtensionV1(FrozenModel):
    schema_version: Literal["VOICE_OPTIONAL_ENRICHMENT_EXTENSION_V1"] = (
        "VOICE_OPTIONAL_ENRICHMENT_EXTENSION_V1"
    )
    status: Literal[EnrichmentStatusV1.INACTIVE] = EnrichmentStatusV1.INACTIVE
    relation_binding_identities: tuple[str, ...] = ()
    candidate_pool_identities: tuple[str, ...] = ()
    candidates: tuple[object, ...] = ()
    selected_identity: None = None
    emitted_surface: None = None

    @model_validator(mode="after")
    def remain_inactive(self):
        if (
            self.relation_binding_identities
            or self.candidate_pool_identities
            or self.candidates
            or self.selected_identity is not None
            or self.emitted_surface is not None
        ):
            raise ValueError("inactive enrichment extension cannot carry behavior")
        return self


class VoiceEligibilityResultV1(FrozenModel):
    schema_version: Literal["VOICE_ELIGIBILITY_RESULT_V1"] = (
        "VOICE_ELIGIBILITY_RESULT_V1"
    )
    fact_atom_bundle_identity: str = Field(pattern=SHA256_PATTERN)
    repetition_snapshot_identity: str = Field(pattern=SHA256_PATTERN)
    mechanic_outcomes: tuple[EligibilityOutcomeV1, ...]
    program_outcomes: tuple[EligibilityOutcomeV1, ...]
    shortlist: tuple[ProgramCandidateV1, ...]
    enrichment: OptionalEnrichmentExtensionV1 = OptionalEnrichmentExtensionV1()
    result_identity: str = Field(pattern=SHA256_PATTERN)


class VoiceOwnerSelectionReceiptV1(FrozenModel):
    schema_name: Literal["pastilaacida-voice-owner-selection-receipt"] = (
        "pastilaacida-voice-owner-selection-receipt"
    )
    schema_version: Literal["1"] = "1"
    fact_atom_bundle_identity: str = Field(pattern=SHA256_PATTERN)
    eligibility_result_identity: str = Field(pattern=SHA256_PATTERN)
    repetition_snapshot_identity: str = Field(pattern=SHA256_PATTERN)
    shortlist_candidate_ids: tuple[str, ...]
    selection_kind: SelectionKindV1
    selected_candidate_id: str | None = Field(default=None, pattern=SHA256_PATTERN)
    selected_enrichment_identity: None = None
    selector_identity: str = Field(min_length=1)
    selected_at: datetime
    receipt_identity: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_selection(self):
        if self.selection_kind is SelectionKindV1.NONE:
            if self.selected_candidate_id is not None:
                raise ValueError("NONE selection cannot identify a candidate")
        elif (
            self.selected_candidate_id is None
            or self.selected_candidate_id not in self.shortlist_candidate_ids
        ):
            raise ValueError("selected candidate is not in the frozen shortlist")
        if tuple(sorted(set(self.shortlist_candidate_ids))) != tuple(
            sorted(self.shortlist_candidate_ids)
        ):
            raise ValueError("shortlist candidate identities must be unique")
        return self


__all__ = [
    "ZERO_IDENTITY",
    "AtomRoleBindingV1",
    "EligibilityOutcomeV1",
    "EligibilityStatusV1",
    "EnrichmentStatusV1",
    "MechanicEligibilityClaimV1",
    "OptionalEnrichmentExtensionV1",
    "ProgramCandidateV1",
    "RepetitionUseV1",
    "SelectionKindV1",
    "VoiceEligibilityResultV1",
    "VoiceOwnerSelectionReceiptV1",
    "VoiceRepetitionSnapshotV1",
]
