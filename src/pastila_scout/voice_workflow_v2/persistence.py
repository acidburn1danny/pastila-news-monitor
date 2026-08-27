"""Deterministic atomic storage for Voice V2 workflow sidecars."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from pastila_scout.editor.generation.semantic_draft_v2 import (
    PastilaEditorSemanticDraftV2,
    SemanticDraftModeV2,
)
from pastila_scout.voice_workflow_v2.models import (
    VOICE_WORKFLOW_SIDECAR_SCHEMA_NAME,
    VOICE_WORKFLOW_SIDECAR_SCHEMA_VERSION,
    PersistedVoiceAttemptOutcomeV1,
    PublicCommentaryStateV1,
    VoiceAttemptRecordV1,
    VoiceWorkflowSidecarV1,
)


class UnknownVoiceWorkflowSidecarVersionError(ValueError):
    """The sidecar is not the one exact supported schema version."""


class VoiceWorkflowSidecarIntegrityError(ValueError):
    """The sidecar does not bind exactly to the supplied native V2 draft."""


def sha256_identity(value: bytes | str) -> str:
    encoded = value.encode("utf-8") if isinstance(value, str) else value
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def canonical_voice_sidecar_bytes(sidecar: VoiceWorkflowSidecarV1) -> bytes:
    return (
        json.dumps(
            sidecar.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def voice_sidecar_identity(sidecar: VoiceWorkflowSidecarV1) -> str:
    return sha256_identity(canonical_voice_sidecar_bytes(sidecar))


def semantic_draft_revision_identity(
    draft: PastilaEditorSemanticDraftV2,
) -> str:
    """Return the canonical exact identity of one native V2 revision."""

    payload = json.dumps(
        draft.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_identity(payload)


def _validate_against_draft(
    sidecar: VoiceWorkflowSidecarV1,
    draft: PastilaEditorSemanticDraftV2,
) -> None:
    binding = sidecar.binding
    if binding.semantic_draft_revision_identity != semantic_draft_revision_identity(
        draft
    ):
        raise VoiceWorkflowSidecarIntegrityError("semantic draft revision mismatch")
    stories = tuple(story for story in draft.stories if story.event_id == binding.event_id)
    if len(stories) != 1:
        raise VoiceWorkflowSidecarIntegrityError("bound V2 story is missing")
    story = stories[0]
    if binding.factual_summary_sha256 != sha256_identity(story.factual_summary.text):
        raise VoiceWorkflowSidecarIntegrityError("factual summary bytes changed")
    if (
        binding.event_authority_identity
        != story.factual_summary.authority_bundle_identity
    ):
        raise VoiceWorkflowSidecarIntegrityError("event authority identity mismatch")

    if sidecar.commentary_state is PublicCommentaryStateV1.GENERATED:
        accepted = sidecar.accepted_commentary
        if accepted is None or story.acid_commentary is None:
            raise VoiceWorkflowSidecarIntegrityError(
                "accepted commentary is not adjacent to the V2 story"
            )
        if draft.mode is not SemanticDraftModeV2.CORE_PLUS_VOICE:
            raise VoiceWorkflowSidecarIntegrityError(
                "generated commentary requires Core-plus-Voice mode"
            )
        commentary = story.acid_commentary
        if (
            accepted.output_sha256 != sha256_identity(commentary.text)
            or accepted.voice_model_package_identity
            != commentary.voice_model_identity
            or accepted.factual_boundary_validation_receipt
            != commentary.factual_boundary_receipt
        ):
            raise VoiceWorkflowSidecarIntegrityError(
                "accepted commentary does not match V2 authored content"
            )
    elif story.acid_commentary is not None:
        raise VoiceWorkflowSidecarIntegrityError(
            "sidecar omits commentary present in V2 authored content"
        )


def append_voice_attempt(
    sidecar: VoiceWorkflowSidecarV1,
    attempt: VoiceAttemptRecordV1,
    *,
    updated_at: datetime,
) -> VoiceWorkflowSidecarV1:
    """Return a new immutable sidecar revision for one story-scoped attempt."""

    if sidecar.commentary_state is PublicCommentaryStateV1.GENERATED:
        raise ValueError("accepted commentary requires an explicit new material revision")
    if attempt.ordinal != len(sidecar.attempts) + 1:
        raise ValueError("Voice retry ordinal must append exactly one attempt")
    if (
        sidecar.binding.runtime_input_identity is None
        or attempt.runtime_input_identity != sidecar.binding.runtime_input_identity
    ):
        raise ValueError("Voice retry cannot change immutable runtime input")
    state = (
        PublicCommentaryStateV1.FAILED
        if attempt.outcome is PersistedVoiceAttemptOutcomeV1.FAILED
        else PublicCommentaryStateV1.GENERATED
    )
    if state is PublicCommentaryStateV1.GENERATED:
        raise ValueError(
            "generated attempts require an adjacent AcidCommentaryV2 binding"
        )
    payload = sidecar.model_dump(mode="python")
    payload.update(
        commentary_state=state,
        attempts=sidecar.attempts + (attempt,),
        updated_at=updated_at,
    )
    return VoiceWorkflowSidecarV1.model_validate(payload)


class VoiceWorkflowSidecarStoreV1:
    """Read/write exactly one canonical UTF-8 JSON sidecar atomically."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(
        self,
        sidecar: VoiceWorkflowSidecarV1,
        *,
        draft: PastilaEditorSemanticDraftV2,
    ) -> str:
        _validate_against_draft(sidecar, draft)
        payload = canonical_voice_sidecar_bytes(sidecar)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temporary.open("wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                temporary.unlink()
        if self.path.read_bytes() != payload:
            raise VoiceWorkflowSidecarIntegrityError("sidecar read-back mismatch")
        return sha256_identity(payload)

    def load(
        self, *, draft: PastilaEditorSemanticDraftV2
    ) -> VoiceWorkflowSidecarV1:
        raw = self.path.read_bytes()
        try:
            value: Any = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise VoiceWorkflowSidecarIntegrityError("invalid Voice sidecar JSON") from error
        if not isinstance(value, dict) or (
            value.get("schema_name") != VOICE_WORKFLOW_SIDECAR_SCHEMA_NAME
            or value.get("schema_version") != VOICE_WORKFLOW_SIDECAR_SCHEMA_VERSION
        ):
            raise UnknownVoiceWorkflowSidecarVersionError(
                "unsupported Voice workflow sidecar version"
            )
        try:
            sidecar = VoiceWorkflowSidecarV1.model_validate(value)
        except ValidationError as error:
            raise VoiceWorkflowSidecarIntegrityError(
                "invalid Voice workflow sidecar"
            ) from error
        if canonical_voice_sidecar_bytes(sidecar) != raw:
            raise VoiceWorkflowSidecarIntegrityError(
                "Voice sidecar is not canonical deterministic JSON"
            )
        _validate_against_draft(sidecar, draft)
        return sidecar


__all__ = [
    "UnknownVoiceWorkflowSidecarVersionError",
    "VoiceWorkflowSidecarIntegrityError",
    "VoiceWorkflowSidecarStoreV1",
    "append_voice_attempt",
    "canonical_voice_sidecar_bytes",
    "semantic_draft_revision_identity",
    "sha256_identity",
    "voice_sidecar_identity",
]
