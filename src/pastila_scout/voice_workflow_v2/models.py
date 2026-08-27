"""Frozen Voice workflow contracts; authored prose remains in Semantic Draft V2."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

VOICE_WORKFLOW_SIDECAR_SCHEMA_NAME = "pastila-voice-workflow-sidecar"
VOICE_WORKFLOW_SIDECAR_SCHEMA_VERSION = "1"
_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PublicCommentaryStateV1(StrEnum):
    UNAVAILABLE = "unavailable"
    UNGENERATED = "ungenerated"
    GENERATED = "generated"
    FAILED = "failed"


class TransientCommentaryStateV1(StrEnum):
    """Process-local state deliberately excluded from the sidecar contract."""

    EXECUTING = "executing"


class PersistedVoiceAttemptOutcomeV1(StrEnum):
    GENERATED = "generated"
    FAILED = "failed"


class VoiceValidationResultV1(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_REACHED = "not_reached"


class VoiceStoryBindingV1(_FrozenModel):
    """Exact immutable story inputs to which all attempts are bound."""

    story_material_reference: str = Field(min_length=1)
    semantic_draft_revision_identity: str = Field(pattern=_SHA256_PATTERN)
    event_id: int = Field(gt=0)
    factual_summary_sha256: str = Field(pattern=_SHA256_PATTERN)
    event_authority_identity: str = Field(min_length=1)
    commentary_background_authority_identity: str | None = None
    runtime_input_identity: str | None = Field(default=None, pattern=_SHA256_PATTERN)


class VoiceAttemptRecordV1(_FrozenModel):
    """A terminal attempt record. ``executing`` is intentionally not persistable."""

    attempt_identity: str = Field(pattern=_SHA256_PATTERN)
    ordinal: int = Field(gt=0)
    outcome: PersistedVoiceAttemptOutcomeV1
    runtime_input_identity: str = Field(pattern=_SHA256_PATTERN)
    voice_model_package_identity: str | None = None
    validation_result: VoiceValidationResultV1
    output_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    failure_identity: str | None = Field(default=None, min_length=1)
    started_at: datetime
    completed_at: datetime
    execution_provenance: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_terminal_attempt(self):
        if self.started_at.tzinfo is None or self.completed_at.tzinfo is None:
            raise ValueError("Voice attempt timestamps must be timezone-aware")
        if self.completed_at < self.started_at:
            raise ValueError("Voice attempt completion precedes start")
        if self.outcome is PersistedVoiceAttemptOutcomeV1.GENERATED:
            if (
                self.validation_result is not VoiceValidationResultV1.PASSED
                or self.output_sha256 is None
                or self.failure_identity is not None
                or not self.voice_model_package_identity
            ):
                raise ValueError("generated Voice attempt lacks accepted identities")
        elif (
            self.validation_result is VoiceValidationResultV1.PASSED
            or not self.failure_identity
        ):
            raise ValueError("failed Voice attempt lacks a safe failure identity")
        return self


class AcceptedCommentaryBindingV1(_FrozenModel):
    """Identity of commentary already stored adjacent to its V2 story."""

    attempt_identity: str = Field(pattern=_SHA256_PATTERN)
    attempt_ordinal: int = Field(gt=0)
    acid_commentary_identity: str = Field(pattern=_SHA256_PATTERN)
    output_sha256: str = Field(pattern=_SHA256_PATTERN)
    voice_model_package_identity: str = Field(min_length=1)
    factual_boundary_validation_receipt: str = Field(min_length=1)
    accepted_at: datetime

    @model_validator(mode="after")
    def validate_timestamp(self):
        if self.accepted_at.tzinfo is None:
            raise ValueError("commentary acceptance timestamp must be timezone-aware")
        return self


class VoiceWorkflowSidecarV1(_FrozenModel):
    """Versioned operational state stored separately from authored V2 content."""

    schema_name: Literal["pastila-voice-workflow-sidecar"] = (
        VOICE_WORKFLOW_SIDECAR_SCHEMA_NAME
    )
    schema_version: Literal["1"] = VOICE_WORKFLOW_SIDECAR_SCHEMA_VERSION
    binding: VoiceStoryBindingV1
    commentary_state: PublicCommentaryStateV1
    attempts: tuple[VoiceAttemptRecordV1, ...] = ()
    accepted_commentary: AcceptedCommentaryBindingV1 | None = None
    created_at: datetime
    updated_at: datetime
    provenance_references: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_workflow(self):
        if self.created_at.tzinfo is None or self.updated_at.tzinfo is None:
            raise ValueError("Voice sidecar timestamps must be timezone-aware")
        if self.updated_at < self.created_at:
            raise ValueError("Voice sidecar update precedes creation")

        ordinals = tuple(attempt.ordinal for attempt in self.attempts)
        if ordinals != tuple(range(1, len(self.attempts) + 1)):
            raise ValueError("Voice attempt ordinals must be contiguous")
        identities = tuple(attempt.attempt_identity for attempt in self.attempts)
        if len(identities) != len(set(identities)):
            raise ValueError("duplicate Voice attempt identity")
        if any(
            self.binding.runtime_input_identity is None
            or attempt.runtime_input_identity != self.binding.runtime_input_identity
            for attempt in self.attempts
        ):
            raise ValueError("Voice attempt is bound to another runtime input")

        generated_attempts = tuple(
            attempt
            for attempt in self.attempts
            if attempt.outcome is PersistedVoiceAttemptOutcomeV1.GENERATED
        )
        if self.commentary_state is PublicCommentaryStateV1.GENERATED:
            if self.accepted_commentary is None:
                raise ValueError("generated state requires accepted commentary")
            matches = tuple(
                attempt
                for attempt in generated_attempts
                if attempt.attempt_identity
                == self.accepted_commentary.attempt_identity
                and attempt.ordinal == self.accepted_commentary.attempt_ordinal
            )
            if len(matches) != 1:
                raise ValueError("accepted commentary attempt is missing")
            attempt = matches[0]
            if (
                attempt.output_sha256 != self.accepted_commentary.output_sha256
                or attempt.voice_model_package_identity
                != self.accepted_commentary.voice_model_package_identity
            ):
                raise ValueError("accepted commentary identities do not match attempt")
        elif self.accepted_commentary is not None:
            raise ValueError("non-generated state cannot bind accepted commentary")

        if (
            self.commentary_state is PublicCommentaryStateV1.UNGENERATED
            and self.attempts
        ):
            raise ValueError("ungenerated commentary cannot contain attempts")
        if self.commentary_state is PublicCommentaryStateV1.FAILED and (
            not self.attempts
            or self.attempts[-1].outcome
            is not PersistedVoiceAttemptOutcomeV1.FAILED
        ):
            raise ValueError("failed state requires a terminal failed attempt")
        return self


__all__ = [
    "VOICE_WORKFLOW_SIDECAR_SCHEMA_NAME",
    "VOICE_WORKFLOW_SIDECAR_SCHEMA_VERSION",
    "AcceptedCommentaryBindingV1",
    "PersistedVoiceAttemptOutcomeV1",
    "PublicCommentaryStateV1",
    "TransientCommentaryStateV1",
    "VoiceAttemptRecordV1",
    "VoiceStoryBindingV1",
    "VoiceValidationResultV1",
    "VoiceWorkflowSidecarV1",
]
