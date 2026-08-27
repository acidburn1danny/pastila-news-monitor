"""Authoritative append-only repetition and acceptance contracts for Voice V2."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.editor.generation.semantic_draft_v2 import (
    PastilaEditorSemanticDraftV2,
)
from pastila_scout.voice_eligibility_v2.models import VoiceRepetitionSnapshotV1
from pastila_scout.voice_executor_v2.models import (
    VoiceDeterministicExecutionRequestV2,
    VoiceDeterministicPreviewSidecarV2,
)

SHA = r"^sha256:[0-9a-f]{64}$"
ZERO = "sha256:" + "0" * 64


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PublicationStateV1(StrEnum):
    UNPUBLISHED = "unpublished"
    PUBLISHED = "published"


class RepetitionLedgerEventKindV1(StrEnum):
    COMMIT = "commit"
    REVOKE = "revoke"
    PUBLISH = "publish"


class EpisodeOrderAuthorityV1(FrozenModel):
    schema_version: Literal["VOICE_EPISODE_ORDER_AUTHORITY_V1"] = (
        "VOICE_EPISODE_ORDER_AUTHORITY_V1"
    )
    episode_id: str = Field(min_length=1)
    episode_ordinal: int = Field(ge=1)
    ordered_event_ids: tuple[int, ...] = Field(min_length=1)
    publication_state: PublicationStateV1
    publication_authority_identity: str | None = Field(default=None, pattern=SHA)
    authority_identity: str = Field(default=ZERO, pattern=SHA)

    @model_validator(mode="after")
    def validate_authority(self):
        if len(self.ordered_event_ids) != len(set(self.ordered_event_ids)):
            raise ValueError("episode order contains duplicate stories")
        if (self.publication_state is PublicationStateV1.PUBLISHED) != (
            self.publication_authority_identity is not None
        ):
            raise ValueError("published state requires exact publication authority")
        return self


class CommittedVoiceUseV1(FrozenModel):
    commit_identity: str = Field(pattern=SHA)
    episode_id: str = Field(min_length=1)
    episode_ordinal: int = Field(ge=1)
    event_id: int = Field(gt=0)
    story_position: int = Field(ge=1)
    order_authority_identity: str = Field(pattern=SHA)
    accepted_commentary_revision_identity: str = Field(pattern=SHA)
    mechanic_identity: str = Field(min_length=1)
    realization_program_identity: str = Field(min_length=1)
    cadence_signature: str = Field(min_length=1)
    approved_voice_surface_identities: tuple[str, ...] = ()
    expression_identity: str | None = None
    expression_surface_identity: str | None = None
    expression_family_identity: str | None = None
    expression_pool_identity: str | None = None
    callback_identities: tuple[str, ...] = ()
    mapping_identities: tuple[str, ...] = ()
    publication_state: PublicationStateV1 = PublicationStateV1.UNPUBLISHED
    committed_at: datetime

    @model_validator(mode="after")
    def expression_shape(self):
        values = (
            self.expression_identity,
            self.expression_surface_identity,
            self.expression_family_identity,
        )
        if any(values) and not all(values):
            raise ValueError("expression repetition identity is incomplete")
        return self


class RepetitionLedgerEventV1(FrozenModel):
    sequence: int = Field(ge=1)
    event_kind: RepetitionLedgerEventKindV1
    transaction_identity: str = Field(pattern=SHA)
    commit: CommittedVoiceUseV1 | None = None
    target_commit_identity: str | None = Field(default=None, pattern=SHA)
    actor_identity: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    occurred_at: datetime
    event_identity: str = Field(default=ZERO, pattern=SHA)

    @model_validator(mode="after")
    def validate_shape(self):
        if self.event_kind is RepetitionLedgerEventKindV1.COMMIT:
            if self.commit is None or self.target_commit_identity is not None:
                raise ValueError("commit event shape is invalid")
        elif self.commit is not None or self.target_commit_identity is None:
            raise ValueError("revocation/publication event shape is invalid")
        return self


class VoiceRepetitionLedgerV1(FrozenModel):
    schema_name: Literal["pastilaacida-voice-repetition-ledger"] = (
        "pastilaacida-voice-repetition-ledger"
    )
    schema_version: Literal["1"] = "1"
    prior_ledger_identity: str | None = Field(default=None, pattern=SHA)
    events: tuple[RepetitionLedgerEventV1, ...] = ()
    ledger_identity: str = Field(default=ZERO, pattern=SHA)

    @model_validator(mode="after")
    def validate_history(self):
        if tuple(item.sequence for item in self.events) != tuple(
            range(1, len(self.events) + 1)
        ):
            raise ValueError("ledger sequence is noncanonical")
        commits: dict[str, CommittedVoiceUseV1] = {}
        revoked: set[str] = set()
        published: set[str] = set()
        for item in self.events:
            if item.event_kind is RepetitionLedgerEventKindV1.COMMIT:
                assert item.commit is not None
                if item.commit.commit_identity in commits:
                    raise ValueError("duplicate repetition commit")
                commits[item.commit.commit_identity] = item.commit
            else:
                target = item.target_commit_identity
                assert target is not None
                if target not in commits:
                    raise ValueError("orphan repetition event")
                if item.event_kind is RepetitionLedgerEventKindV1.REVOKE:
                    if target in revoked or target in published:
                        raise ValueError("impossible repetition revocation")
                    revoked.add(target)
                elif target in revoked or target in published:
                    raise ValueError("impossible publication event")
                else:
                    published.add(target)
        return self


class AcceptanceCandidatePreviewV1(FrozenModel):
    schema_version: Literal["VOICE_ACCEPTANCE_CANDIDATE_PREVIEW_V1"] = (
        "VOICE_ACCEPTANCE_CANDIDATE_PREVIEW_V1"
    )
    preview: VoiceDeterministicPreviewSidecarV2
    execution_request: VoiceDeterministicExecutionRequestV2
    order_authority_identity: str = Field(pattern=SHA)
    candidate_identity: str = Field(default=ZERO, pattern=SHA)

    @model_validator(mode="after")
    def exact_preview_request(self):
        if self.preview.request_identity != self.execution_request.request_identity:
            raise ValueError("preview and execution request differ")
        return self


class VoiceAcceptanceRequestV1(FrozenModel):
    schema_version: Literal["VOICE_ACCEPTANCE_REQUEST_V1"] = (
        "VOICE_ACCEPTANCE_REQUEST_V1"
    )
    idempotency_key: str = Field(min_length=1)
    draft: PastilaEditorSemanticDraftV2
    candidate: AcceptanceCandidatePreviewV1
    order_authority: EpisodeOrderAuthorityV1
    owner_identity: str = Field(min_length=1)
    accepted_at: datetime
    replaces_commit_identity: str | None = Field(default=None, pattern=SHA)
    request_identity: str = Field(default=ZERO, pattern=SHA)


class VoiceAcceptanceReceiptV1(FrozenModel):
    schema_name: Literal["pastilaacida-voice-acceptance-receipt"] = (
        "pastilaacida-voice-acceptance-receipt"
    )
    schema_version: Literal["1"] = "1"
    transaction_identity: str = Field(pattern=SHA)
    request_identity: str = Field(pattern=SHA)
    preview_sidecar_identity: str = Field(pattern=SHA)
    source_semantic_draft_revision_identity: str = Field(pattern=SHA)
    authority_identity: str = Field(min_length=1)
    fact_atom_bundle_identity: str = Field(pattern=SHA)
    relationship_binding_identities: tuple[str, ...]
    program_eligibility_identity: str = Field(pattern=SHA)
    program_selection_receipt_identity: str = Field(pattern=SHA)
    expression_eligibility_identity: str | None = Field(default=None, pattern=SHA)
    expression_selection_receipt_identity: str | None = Field(default=None, pattern=SHA)
    repetition_snapshot_identity: str = Field(pattern=SHA)
    order_authority_identity: str = Field(pattern=SHA)
    activation_policy_identity: str = Field(pattern=SHA)
    executor_identity: str = Field(min_length=1)
    canonical_ir_identity: str = Field(pattern=r"^[0-9a-f]{64}$")
    rendered_output_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance_identity: str = Field(pattern=SHA)
    resulting_semantic_draft_revision_identity: str = Field(pattern=SHA)
    committed_repetition_identity: str = Field(pattern=SHA)
    owner_identity: str = Field(min_length=1)
    accepted_at: datetime
    receipt_identity: str = Field(default=ZERO, pattern=SHA)


class VoiceRemovalReceiptV1(FrozenModel):
    schema_name: Literal["pastilaacida-voice-removal-receipt"] = (
        "pastilaacida-voice-removal-receipt"
    )
    schema_version: Literal["1"] = "1"
    transaction_identity: str = Field(pattern=SHA)
    removed_commit_identity: str = Field(pattern=SHA)
    source_semantic_draft_revision_identity: str = Field(pattern=SHA)
    resulting_semantic_draft_revision_identity: str = Field(pattern=SHA)
    committed_repetition_identity: str = Field(pattern=SHA)
    owner_identity: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    removed_at: datetime
    receipt_identity: str = Field(default=ZERO, pattern=SHA)


class VoicePublicationReceiptV1(FrozenModel):
    schema_name: Literal["pastilaacida-voice-publication-receipt"] = (
        "pastilaacida-voice-publication-receipt"
    )
    schema_version: Literal["1"] = "1"
    transaction_identity: str = Field(pattern=SHA)
    published_commit_identities: tuple[str, ...] = Field(min_length=1)
    publication_authority_identity: str = Field(pattern=SHA)
    resulting_semantic_draft_revision_identity: str = Field(pattern=SHA)
    committed_repetition_identity: str = Field(pattern=SHA)
    publisher_identity: str = Field(min_length=1)
    published_at: datetime
    receipt_identity: str = Field(default=ZERO, pattern=SHA)


class RepetitionSnapshotEnvelopeV1(FrozenModel):
    schema_version: Literal["VOICE_REPETITION_SNAPSHOT_ENVELOPE_V1"] = (
        "VOICE_REPETITION_SNAPSHOT_ENVELOPE_V1"
    )
    ledger_identity: str = Field(pattern=SHA)
    order_authority_identity: str = Field(pattern=SHA)
    snapshot: VoiceRepetitionSnapshotV1
    exact_surface_identities: tuple[str, ...] = ()
    expression_family_identities: tuple[str, ...] = ()
    expression_pool_identities: tuple[str, ...] = ()
    callback_identities: tuple[str, ...] = ()
    mapping_identities: tuple[str, ...] = ()
    envelope_identity: str = Field(default=ZERO, pattern=SHA)
