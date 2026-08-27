"""Canonical identity, exact binding validation, and atomic fact-bundle storage."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter, ValidationError

from pastila_scout.editor.generation.semantic_draft_v2 import (
    PastilaEditorSemanticDraftV2,
)
from pastila_scout.voice_workflow_v2 import (
    semantic_draft_revision_identity,
    sha256_identity,
)

from .models import SCHEMA_NAME, VoiceFactAtomBundleV1, VoiceFactAtomBundleV2

_BUNDLE_ADAPTER = TypeAdapter(VoiceFactAtomBundleV1 | VoiceFactAtomBundleV2)


class UnknownFactAtomBundleVersionError(ValueError):
    pass


class FactAtomBundleIntegrityError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    payload = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
    return (
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        + b"\n"
    )


def canonical_identity(value: Any) -> str:
    return sha256_identity(canonical_bytes(value))


def bundle_payload_identity(bundle: VoiceFactAtomBundleV1) -> str:
    payload = bundle.model_dump(mode="json")
    payload["bundle_identity"] = "sha256:" + "0" * 64
    return canonical_identity(payload)


def finalize_bundle_identity(bundle: VoiceFactAtomBundleV1) -> VoiceFactAtomBundleV1:
    """Seal a provisional bundle whose identity field contains the zero digest."""
    return bundle.model_copy(
        update={"bundle_identity": bundle_payload_identity(bundle)}
    )


def validate_binding(
    bundle: VoiceFactAtomBundleV1, draft: PastilaEditorSemanticDraftV2
) -> None:
    if bundle.bundle_identity != bundle_payload_identity(bundle):
        raise FactAtomBundleIntegrityError("bundle identity mismatch")
    if bundle.semantic_draft_revision_identity != semantic_draft_revision_identity(
        draft
    ):
        raise FactAtomBundleIntegrityError("stale Semantic Draft V2 revision")
    matches = [
        story
        for story in draft.stories
        if story.event_id == bundle.event_id and story.position == bundle.story_position
    ]
    if len(matches) != 1:
        raise FactAtomBundleIntegrityError("bound V2 story is missing")
    story = matches[0]
    if bundle.factual_summary_identity != sha256_identity(story.factual_summary.text):
        raise FactAtomBundleIntegrityError("factual summary identity mismatch")
    if (
        bundle.event_authority_identity
        != story.factual_summary.authority_bundle_identity
    ):
        raise FactAtomBundleIntegrityError("event authority identity mismatch")


class VoiceFactAtomBundleStoreV1:
    def __init__(self, path: Path):
        self.path = path

    def save(
        self, bundle: VoiceFactAtomBundleV1, *, draft: PastilaEditorSemanticDraftV2
    ) -> str:
        validate_binding(bundle, draft)
        raw = canonical_bytes(bundle)
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
        if self.path.read_bytes() != raw:
            raise FactAtomBundleIntegrityError("bundle read-back mismatch")
        return canonical_identity(bundle)

    def load(self, *, draft: PastilaEditorSemanticDraftV2) -> VoiceFactAtomBundleV1:
        raw = self.path.read_bytes()
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise FactAtomBundleIntegrityError("invalid fact-atom JSON") from exc
        if (
            not isinstance(value, dict)
            or value.get("schema_name") != SCHEMA_NAME
            or value.get("schema_version") not in {"1", "2"}
        ):
            raise UnknownFactAtomBundleVersionError(
                "unsupported fact-atom bundle version"
            )
        try:
            bundle = _BUNDLE_ADAPTER.validate_python(value)
        except ValidationError as exc:
            raise FactAtomBundleIntegrityError("invalid fact-atom bundle") from exc
        if canonical_bytes(bundle) != raw:
            raise FactAtomBundleIntegrityError("fact-atom bundle is not canonical")
        validate_binding(bundle, draft)
        return bundle
