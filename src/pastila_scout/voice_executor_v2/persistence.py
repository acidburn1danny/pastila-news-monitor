"""Canonical preview-only persistence for deterministic Voice V2."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from pastila_scout.voice_fact_atoms_v2.persistence import (
    canonical_bytes,
    canonical_identity,
)

from .models import (
    VoiceDeterministicExecutionRequestV2,
    VoiceDeterministicPreviewSidecarV2,
    VoiceDeterministicTerminalResultV2,
)


class DeterministicVoiceSidecarIntegrityError(ValueError):
    pass


class UnknownDeterministicVoiceSidecarVersionError(ValueError):
    pass


def finalize_preview_sidecar_v2(
    sidecar: VoiceDeterministicPreviewSidecarV2,
) -> VoiceDeterministicPreviewSidecarV2:
    provisional = sidecar.model_copy(update={"sidecar_identity": "sha256:" + "0" * 64})
    return sidecar.model_copy(
        update={"sidecar_identity": canonical_identity(provisional)}
    )


def build_preview_sidecar_v2(
    *,
    request: VoiceDeterministicExecutionRequestV2,
    result: VoiceDeterministicTerminalResultV2,
) -> VoiceDeterministicPreviewSidecarV2:
    expression_result = request.expression_eligibility
    expression_selection = request.expression_selection
    provisional = VoiceDeterministicPreviewSidecarV2(
        source_semantic_draft_revision_identity=(
            request.story_binding.semantic_draft_revision_identity
        ),
        event_id=request.story_binding.event_id,
        factual_summary_identity=request.story_binding.factual_summary_sha256,
        event_authority_identity=request.story_binding.event_authority_identity,
        background_authority_identity=(
            request.story_binding.commentary_background_authority_identity
        ),
        fact_atom_bundle_identity=request.fact_atom_bundle.bundle_identity,
        relationship_binding_identities=tuple(
            item.binding_identity for item in request.relationship_bindings
        ),
        program_eligibility_identity=request.program_eligibility.result_identity,
        program_selection_receipt_identity=request.program_selection.receipt_identity,
        expression_eligibility_identity=(
            None if expression_result is None else expression_result.result_identity
        ),
        expression_selection_receipt_identity=(
            None
            if expression_selection is None
            else expression_selection.receipt_identity
        ),
        repetition_snapshot_identity=request.repetition_snapshot.snapshot_identity,
        activation_policy_identity=request.activation_policy.policy_identity,
        request_identity=request.request_identity,
        terminal_result=result,
    )
    return finalize_preview_sidecar_v2(provisional)


class VoiceDeterministicPreviewSidecarStoreV2:
    def __init__(self, path: Path):
        self.path = path

    def save(self, sidecar: VoiceDeterministicPreviewSidecarV2) -> None:
        if finalize_preview_sidecar_v2(sidecar) != sidecar:
            raise DeterministicVoiceSidecarIntegrityError("sidecar identity mismatch")
        raw = canonical_bytes(sidecar)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temporary.open("wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def load(self) -> VoiceDeterministicPreviewSidecarV2:
        raw = self.path.read_bytes()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DeterministicVoiceSidecarIntegrityError(
                "invalid sidecar JSON"
            ) from exc
        if (
            not isinstance(payload, dict)
            or payload.get("schema_name")
            != "pastilaacida-voice-deterministic-preview-sidecar"
            or payload.get("schema_version") != "2"
        ):
            raise UnknownDeterministicVoiceSidecarVersionError(
                "unsupported deterministic Voice sidecar version"
            )
        try:
            sidecar = TypeAdapter(VoiceDeterministicPreviewSidecarV2).validate_python(
                payload
            )
        except ValidationError as exc:
            raise DeterministicVoiceSidecarIntegrityError("invalid sidecar") from exc
        if canonical_bytes(sidecar) != raw:
            raise DeterministicVoiceSidecarIntegrityError("sidecar is not canonical")
        if finalize_preview_sidecar_v2(sidecar) != sidecar:
            raise DeterministicVoiceSidecarIntegrityError("sidecar identity mismatch")
        return sidecar


__all__ = [
    "DeterministicVoiceSidecarIntegrityError",
    "UnknownDeterministicVoiceSidecarVersionError",
    "VoiceDeterministicPreviewSidecarStoreV2",
    "build_preview_sidecar_v2",
    "finalize_preview_sidecar_v2",
]
