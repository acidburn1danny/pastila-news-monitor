"""Immutable contracts for Editor-to-Voice application orchestration."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.editor.generation.semantic_draft_v2 import (
    PastilaEditorSemanticDraftV2,
)
from pastila_scout.voice_workflow_v2 import (
    PublicCommentaryStateV1,
    VoiceStoryBindingV1,
)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VoiceExecutorAvailabilityV1(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class VoiceExecutorCapabilityV1(_FrozenModel):
    executor_identity: str = Field(min_length=1)
    availability: VoiceExecutorAvailabilityV1
    voice_model_package_identity: str | None = None
    safe_reason: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_capability(self):
        if self.availability is VoiceExecutorAvailabilityV1.AVAILABLE:
            if not self.voice_model_package_identity or self.safe_reason is not None:
                raise ValueError("available Voice capability lacks model binding")
        elif self.voice_model_package_identity is not None or not self.safe_reason:
            raise ValueError("unavailable Voice capability is not explicit")
        return self


class EditorVoiceStoryRequestV1(_FrozenModel):
    """Exact native V2 revision and authority identities presented by Editor."""

    draft: PastilaEditorSemanticDraftV2
    story_material_reference: str = Field(min_length=1)
    event_id: int = Field(gt=0)
    expected_semantic_draft_revision_identity: str = Field(
        pattern=r"^sha256:[0-9a-f]{64}$"
    )
    expected_event_authority_identity: str = Field(min_length=1)
    commentary_background_authority_identity: str | None = None
    runtime_input_identity: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )


class VoiceExecutorRequestV1(_FrozenModel):
    binding: VoiceStoryBindingV1
    next_attempt_ordinal: int = Field(gt=0)


class VoiceUnavailableExecutionResultV1(_FrozenModel):
    outcome: VoiceExecutorAvailabilityV1 = VoiceExecutorAvailabilityV1.UNAVAILABLE
    executor_identity: str = Field(min_length=1)
    safe_reason: str = Field(min_length=1)
    provider_calls: int = Field(default=0, ge=0, le=0)
    model_loads: int = Field(default=0, ge=0, le=0)
    generations: int = Field(default=0, ge=0, le=0)
    attempts_created: int = Field(default=0, ge=0, le=0)


class EditorVoiceApplicationOutcomeV1(StrEnum):
    UNAVAILABLE = "unavailable"
    UNGENERATED = "ungenerated"
    GENERATED = "generated"
    FAILED = "failed"
    INVALID_BINDING = "invalid_binding"


class EditorVoiceApplicationResultV1(_FrozenModel):
    outcome: EditorVoiceApplicationOutcomeV1
    commentary_state: PublicCommentaryStateV1 | None
    generation_possible: bool
    binding: VoiceStoryBindingV1 | None = None
    sidecar_identity: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    executor_identity: str | None = None
    executor_port_invoked: bool = False
    attempt_created: bool = False
    safe_failure_code: str | None = None

    @model_validator(mode="after")
    def validate_result(self):
        if self.outcome is EditorVoiceApplicationOutcomeV1.INVALID_BINDING:
            if (
                self.commentary_state is not None
                or self.generation_possible
                or self.binding is not None
                or not self.safe_failure_code
            ):
                raise ValueError("invalid binding result exposes invalid state")
        elif self.commentary_state is None or self.binding is None:
            raise ValueError("valid application result lacks Voice binding")
        if self.outcome is EditorVoiceApplicationOutcomeV1.UNAVAILABLE and (
            self.commentary_state is not PublicCommentaryStateV1.UNAVAILABLE
            or self.generation_possible
            or self.attempt_created
        ):
            raise ValueError("unavailable application result is inconsistent")
        if self.outcome is EditorVoiceApplicationOutcomeV1.UNGENERATED and (
            self.commentary_state is not PublicCommentaryStateV1.UNGENERATED
            or not self.generation_possible
        ):
            raise ValueError("ungenerated application result is inconsistent")
        if self.outcome is EditorVoiceApplicationOutcomeV1.GENERATED and (
            self.commentary_state is not PublicCommentaryStateV1.GENERATED
            or self.generation_possible
        ):
            raise ValueError("generated application result is inconsistent")
        if self.outcome is EditorVoiceApplicationOutcomeV1.FAILED and (
            self.commentary_state is not PublicCommentaryStateV1.FAILED
            or not self.generation_possible
        ):
            raise ValueError("failed application result is inconsistent")
        return self


__all__ = [
    "EditorVoiceApplicationOutcomeV1",
    "EditorVoiceApplicationResultV1",
    "EditorVoiceStoryRequestV1",
    "VoiceExecutorAvailabilityV1",
    "VoiceExecutorCapabilityV1",
    "VoiceExecutorRequestV1",
    "VoiceUnavailableExecutionResultV1",
]
