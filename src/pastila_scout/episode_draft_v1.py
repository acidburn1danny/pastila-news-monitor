"""Immutable persistence authority for ready desktop Episode Draft revisions."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.editor.generation.models import EpisodeDraft
from pastila_scout.editor_application_v1 import (
    EditorAtomicExporterV1,
    EditorOutputDestinationV1,
    EditorOverwritePolicyV1,
)

_SCHEMA_NAME = "pastila-episode-draft-revision"
_SCHEMA_VERSION = "1"
_CHECKSUM_PREFIX = "sha256:"


class EpisodeDraftPersistenceError(ValueError):
    """One safe public failure for invalid or unavailable revision artifacts."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EpisodeDraftIncludedMaterialV1(_FrozenModel):
    event_id: int = Field(gt=0)
    material_reference: str = Field(min_length=1)
    payload_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def reject_bool_identity(self):
        if type(self.event_id) is not int or not _canonical_text(
            self.material_reference
        ):
            raise ValueError("invalid included material identity")
        return self


class EpisodeDraftExcludedFailureV1(_FrozenModel):
    event_id: int = Field(gt=0)
    attempt_count: int = Field(ge=1, le=3)
    failure_category: str = Field(min_length=1, max_length=80)
    sanitized_reason: str = Field(min_length=1, max_length=500)
    failure_evidence_reference: str | None = Field(default=None, min_length=1)
    final_disposition: Literal["excluded_exhausted_failure"] = (
        "excluded_exhausted_failure"
    )

    @model_validator(mode="after")
    def safe_terminal_failure(self):
        if type(self.event_id) is not int or type(self.attempt_count) is not int:
            raise ValueError("invalid excluded failure identity")
        text_values = (self.failure_category, self.sanitized_reason)
        if self.failure_evidence_reference is not None:
            text_values += (self.failure_evidence_reference,)
        if any(not _canonical_text(value) for value in text_values):
            raise ValueError("terminal failure reason is blank")
        unsafe = (
            "api_key",
            "api key",
            "apikey",
            "bearer ",
            "authorization:",
            "access_token",
            "access token",
            "token=",
            "sk-",
        )
        if any(token in self.sanitized_reason.casefold() for token in unsafe):
            raise ValueError("unsafe terminal failure reason")
        return self


class EpisodeDraftRevisionV1(_FrozenModel):
    schema_name: Literal["pastila-episode-draft-revision"] = _SCHEMA_NAME
    schema_version: Literal["1"] = _SCHEMA_VERSION
    draft_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    parent_revision_id: str | None = Field(default=None, min_length=1)
    project_id: str = Field(min_length=1)
    episode_id: str = Field(min_length=1)
    created_at: datetime
    requested_event_ids: tuple[int, ...] = Field(min_length=5)
    included_event_ids: tuple[int, ...] = Field(min_length=5)
    excluded_failed_event_ids: tuple[int, ...]
    included_materials: tuple[EpisodeDraftIncludedMaterialV1, ...] = Field(min_length=5)
    excluded_failures: tuple[EpisodeDraftExcludedFailureV1, ...]
    episode_draft: EpisodeDraft
    provenance_references: tuple[str, ...] = ()
    readiness: Literal["ready"] = "ready"
    payload_sha256: str = ""

    @model_validator(mode="after")
    def validate_revision(self):
        identities = (self.draft_id, self.revision_id, self.project_id, self.episode_id)
        if any(not _canonical_text(value) for value in identities):
            raise ValueError("blank revision identity")
        if self.parent_revision_id is not None and not _canonical_text(
            self.parent_revision_id
        ):
            raise ValueError("blank parent revision identity")
        requested = self.requested_event_ids
        included = self.included_event_ids
        excluded = self.excluded_failed_event_ids
        for values in (requested, included, excluded):
            if any(type(value) is not int or value <= 0 for value in values):
                raise ValueError("invalid event identity")
            if len(values) != len(set(values)):
                raise ValueError("duplicate event identity")
        if set(included).intersection(excluded) or set(included).union(excluded) != set(
            requested
        ):
            raise ValueError("incomplete requested event partition")
        if included != tuple(value for value in requested if value in set(included)):
            raise ValueError("included event order mismatch")
        if excluded != tuple(value for value in requested if value in set(excluded)):
            raise ValueError("excluded event order mismatch")
        if tuple(item.event_id for item in self.included_materials) != included:
            raise ValueError("included material lineage mismatch")
        material_references = tuple(
            item.material_reference for item in self.included_materials
        )
        material_checksums = tuple(
            item.payload_sha256 for item in self.included_materials
        )
        if len(set(material_references)) != len(material_references) or len(
            set(material_checksums)
        ) != len(material_checksums):
            raise ValueError("duplicate included material lineage")
        if tuple(item.event_id for item in self.excluded_failures) != excluded:
            raise ValueError("excluded failure lineage mismatch")
        if tuple(item.story_id for item in self.episode_draft.stories) != included:
            raise ValueError("episode story lineage mismatch")
        if self.episode_draft.episode_id != self.episode_id:
            raise ValueError("episode identity mismatch")
        if self.parent_revision_id == self.revision_id:
            raise ValueError("revision cannot parent itself")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("revision timestamp must be timezone-aware")
        if any(
            not _canonical_text(value) for value in self.provenance_references
        ) or len(set(self.provenance_references)) != len(self.provenance_references):
            raise ValueError("duplicate provenance reference")
        if self.payload_sha256 and not _valid_checksum(self.payload_sha256):
            raise ValueError("invalid payload checksum")
        return self


class EpisodeDraftRevisionRefV1(_FrozenModel):
    draft_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    parent_revision_id: str | None = Field(default=None, min_length=1)
    project_id: str = Field(min_length=1)
    episode_id: str = Field(min_length=1)
    artifact_path: str = Field(min_length=1)
    artifact_sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    requested_event_ids: tuple[int, ...] = Field(min_length=5)
    included_event_ids: tuple[int, ...] = Field(min_length=5)
    excluded_failed_event_ids: tuple[int, ...]
    created_at: datetime

    @model_validator(mode="after")
    def validate_reference(self):
        identities = (
            self.draft_id,
            self.revision_id,
            self.project_id,
            self.episode_id,
            self.artifact_path,
        )
        if any(not _canonical_text(value) for value in identities):
            raise ValueError("blank revision reference identity")
        if self.parent_revision_id is not None and not _canonical_text(
            self.parent_revision_id
        ):
            raise ValueError("blank parent revision identity")
        if not Path(self.artifact_path).is_absolute():
            raise ValueError("revision artifact path must be absolute")
        return self


class EpisodeDraftRevisionRepositoryV1:
    """Publish and strictly reconstruct immutable revision artifacts."""

    def publish(
        self, *, revision: EpisodeDraftRevisionV1, destination: Path
    ) -> EpisodeDraftRevisionRefV1:
        try:
            if (
                type(revision) is not EpisodeDraftRevisionV1
                or not isinstance(destination, Path)
                or not destination.is_absolute()
            ):
                raise TypeError
            payload = _serialize_revision(revision)
            destination.parent.mkdir(parents=True, exist_ok=True)
            EditorAtomicExporterV1().publish(
                payload=payload,
                destination=EditorOutputDestinationV1(
                    destination, EditorOverwritePolicyV1.FAIL_IF_EXISTS
                ),
            )
            artifact_sha256 = _checksum(payload)
            loaded = self.load(path=destination, artifact_sha256=artifact_sha256)
            if loaded != _with_checksum(revision):
                raise EpisodeDraftPersistenceError("revision verification failed")
            return _reference(loaded, destination, artifact_sha256)
        except EpisodeDraftPersistenceError:
            raise
        except Exception as exc:
            raise EpisodeDraftPersistenceError("revision publication failed") from exc

    def load(self, *, path: Path, artifact_sha256: str) -> EpisodeDraftRevisionV1:
        try:
            if not isinstance(path, Path) or not _valid_checksum(artifact_sha256):
                raise TypeError
            payload = path.read_bytes()
            if _checksum(payload) != artifact_sha256:
                raise ValueError
            parsed = json.loads(payload.decode("utf-8"))
            if type(parsed) is not dict:
                raise TypeError
            embedded = parsed.get("payload_sha256")
            if not _valid_checksum(embedded):
                raise ValueError
            parsed["payload_sha256"] = ""
            if _checksum(_encode(parsed)) != embedded:
                raise ValueError
            parsed["payload_sha256"] = embedded
            revision = EpisodeDraftRevisionV1.model_validate_json(payload, strict=True)
            if _serialize_revision(revision) != payload:
                raise ValueError
            return revision
        except Exception as exc:
            raise EpisodeDraftPersistenceError("revision artifact is invalid") from exc


def _serialize_revision(revision: EpisodeDraftRevisionV1) -> bytes:
    values = revision.model_dump(mode="json")
    values["payload_sha256"] = ""
    checksum = _checksum(_encode(values))
    values["payload_sha256"] = checksum
    return _encode(values)


def _with_checksum(revision: EpisodeDraftRevisionV1) -> EpisodeDraftRevisionV1:
    payload = _serialize_revision(revision)
    return EpisodeDraftRevisionV1.model_validate_json(payload, strict=True)


def _reference(
    revision: EpisodeDraftRevisionV1, path: Path, artifact_sha256: str
) -> EpisodeDraftRevisionRefV1:
    return EpisodeDraftRevisionRefV1(
        draft_id=revision.draft_id,
        revision_id=revision.revision_id,
        parent_revision_id=revision.parent_revision_id,
        project_id=revision.project_id,
        episode_id=revision.episode_id,
        artifact_path=str(path),
        artifact_sha256=artifact_sha256,
        requested_event_ids=revision.requested_event_ids,
        included_event_ids=revision.included_event_ids,
        excluded_failed_event_ids=revision.excluded_failed_event_ids,
        created_at=revision.created_at,
    )


def _encode(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _checksum(payload: bytes) -> str:
    return _CHECKSUM_PREFIX + hashlib.sha256(payload).hexdigest()


def _valid_checksum(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 71
        and value.startswith(_CHECKSUM_PREFIX)
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _canonical_text(value: str) -> bool:
    return (
        bool(value)
        and value == value.strip()
        and unicodedata.is_normalized("NFC", value)
    )


__all__ = (
    "EpisodeDraftExcludedFailureV1",
    "EpisodeDraftIncludedMaterialV1",
    "EpisodeDraftPersistenceError",
    "EpisodeDraftRevisionRefV1",
    "EpisodeDraftRevisionRepositoryV1",
    "EpisodeDraftRevisionV1",
)
