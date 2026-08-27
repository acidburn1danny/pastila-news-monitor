"""Typed Chief Editor lifecycle for exact V2 story adjacencies."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from enum import StrEnum
from itertools import pairwise
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.chief_editor_v2_handoff import (
    ChiefEditorV2StoryReferenceV1,
    resolve_chief_editor_v2_story_reference,
)

TRANSITION_WORKFLOW_SCHEMA_NAME = "pastila-chief-editor-transition-workflow"
TRANSITION_WORKFLOW_SCHEMA_VERSION = "1"
_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PublicTransitionStateV1(StrEnum):
    UNAVAILABLE = "unavailable"
    UNGENERATED = "ungenerated"
    GENERATED = "generated"
    FAILED = "failed"
    INVALID_BINDING = "invalid_binding"


class TransitionValidationResultV1(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_REACHED = "not_reached"


class TransitionEndpointV1(_FrozenModel):
    chief_story_reference_identity: str = Field(pattern=_SHA256_PATTERN)
    event_id: int = Field(gt=0)
    story_revision_identity: str = Field(pattern=_SHA256_PATTERN)
    factual_summary_identity: str = Field(pattern=_SHA256_PATTERN)
    acid_commentary_identity: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    event_authority_identity: str = Field(min_length=1)


class TransitionAttemptV1(_FrozenModel):
    attempt_identity: str = Field(pattern=_SHA256_PATTERN)
    ordinal: int = Field(gt=0)
    outcome: Literal["generated", "failed"]
    transition_input_identity: str = Field(pattern=_SHA256_PATTERN)
    model_package_identity: str | None = None
    output_sha256: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    validation_result: TransitionValidationResultV1
    validation_receipt: str | None = None
    failure_identity: str | None = None
    started_at: datetime
    completed_at: datetime

    @model_validator(mode="after")
    def validate_attempt(self):
        if (
            self.started_at.tzinfo is None
            or self.completed_at.tzinfo is None
            or self.completed_at < self.started_at
        ):
            raise ValueError("invalid transition attempt timestamps")
        if self.outcome == "generated":
            if (
                self.validation_result is not TransitionValidationResultV1.PASSED
                or self.output_sha256 is None
                or not self.model_package_identity
                or not self.validation_receipt
                or self.failure_identity is not None
            ):
                raise ValueError("generated transition attempt is incomplete")
        elif (
            self.validation_result is TransitionValidationResultV1.PASSED
            or not self.failure_identity
        ):
            raise ValueError("failed transition attempt lacks failure evidence")
        return self


class AcceptedTransitionV1(_FrozenModel):
    text: str = Field(min_length=1)
    output_sha256: str = Field(pattern=_SHA256_PATTERN)
    attempt_identity: str = Field(pattern=_SHA256_PATTERN)
    model_package_identity: str = Field(min_length=1)
    validation_receipt: str = Field(min_length=1)
    provenance_references: tuple[str, ...] = ()


class TransitionAdjacencySlotV1(_FrozenModel):
    adjacency_identity: str = Field(pattern=_SHA256_PATTERN)
    from_story: TransitionEndpointV1
    to_story: TransitionEndpointV1
    transition_input_identity: str = Field(pattern=_SHA256_PATTERN)
    transition_intent: str = Field(default="", max_length=500)
    state: PublicTransitionStateV1
    accepted_transition: AcceptedTransitionV1 | None = None
    attempts: tuple[TransitionAttemptV1, ...] = ()

    @model_validator(mode="after")
    def validate_slot(self):
        if self.from_story.event_id == self.to_story.event_id:
            raise ValueError("transition cannot bind a story to itself")
        if self.adjacency_identity != _identity(
            (
                self.from_story.chief_story_reference_identity,
                self.to_story.chief_story_reference_identity,
            )
        ):
            raise ValueError("transition adjacency identity is invalid")
        ordinals = tuple(item.ordinal for item in self.attempts)
        if ordinals != tuple(range(1, len(self.attempts) + 1)):
            raise ValueError("transition attempt ordinals are not contiguous")
        if any(
            item.transition_input_identity != self.transition_input_identity
            for item in self.attempts
        ):
            raise ValueError("transition attempt uses another input")
        if self.state is PublicTransitionStateV1.GENERATED:
            if self.accepted_transition is None:
                raise ValueError("generated transition has no accepted prose")
            matches = tuple(
                item
                for item in self.attempts
                if item.attempt_identity
                == self.accepted_transition.attempt_identity
                and item.outcome == "generated"
            )
            if len(matches) != 1 or (
                self.accepted_transition.output_sha256
                != f"sha256:{hashlib.sha256(self.accepted_transition.text.encode('utf-8')).hexdigest()}"
                or
                matches[0].output_sha256 != self.accepted_transition.output_sha256
                or matches[0].model_package_identity
                != self.accepted_transition.model_package_identity
                or matches[0].validation_receipt
                != self.accepted_transition.validation_receipt
            ):
                raise ValueError("accepted transition does not match its attempt")
        elif self.accepted_transition is not None:
            raise ValueError("non-generated slot contains accepted transition")
        if self.state is PublicTransitionStateV1.UNGENERATED and self.attempts:
            raise ValueError("ungenerated transition contains attempts")
        if self.state is PublicTransitionStateV1.FAILED and (
            not self.attempts or self.attempts[-1].outcome != "failed"
        ):
            raise ValueError("failed transition lacks a terminal failed attempt")
        if self.state is PublicTransitionStateV1.INVALID_BINDING:
            raise ValueError("invalid_binding is derived and cannot be persisted")
        return self


class ChiefEditorTransitionWorkflowSidecarV1(_FrozenModel):
    schema_name: Literal["pastila-chief-editor-transition-workflow"] = (
        TRANSITION_WORKFLOW_SCHEMA_NAME
    )
    schema_version: Literal["1"] = TRANSITION_WORKFLOW_SCHEMA_VERSION
    ordered_chief_story_identities: tuple[str, ...]
    active_slots: tuple[TransitionAdjacencySlotV1, ...] = ()
    retired_slots: tuple[TransitionAdjacencySlotV1, ...] = ()
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_sidecar(self):
        if (
            self.created_at.tzinfo is None
            or self.updated_at.tzinfo is None
            or self.updated_at < self.created_at
        ):
            raise ValueError("invalid transition sidecar timestamps")
        active = tuple(item.adjacency_identity for item in self.active_slots)
        if len(active) != len(set(active)):
            raise ValueError("duplicate active transition adjacency")
        expected = set(pairwise(self.ordered_chief_story_identities))
        actual = {
            (
                item.from_story.chief_story_reference_identity,
                item.to_story.chief_story_reference_identity,
            )
            for item in self.active_slots
        }
        if not actual.issubset(expected):
            raise ValueError("active transition slots do not match final ordering")
        return self


def _identity(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def chief_story_reference_identity(
    reference: ChiefEditorV2StoryReferenceV1,
) -> str:
    return _identity(reference.model_dump(mode="json"))


def build_transition_adjacency_slot(
    *,
    from_reference: ChiefEditorV2StoryReferenceV1,
    to_reference: ChiefEditorV2StoryReferenceV1,
    transition_intent: str = "",
) -> TransitionAdjacencySlotV1:
    """Build one unavailable slot only after both exact endpoints resolve."""

    from_story = resolve_chief_editor_v2_story_reference(from_reference)
    to_story = resolve_chief_editor_v2_story_reference(to_reference)
    if from_reference.event_id == to_reference.event_id:
        raise ValueError("transition cannot bind a story to itself")
    from_identity = chief_story_reference_identity(from_reference)
    to_identity = chief_story_reference_identity(to_reference)
    from_endpoint = TransitionEndpointV1(
        chief_story_reference_identity=from_identity,
        event_id=from_reference.event_id,
        story_revision_identity=from_reference.story_revision_identity,
        factual_summary_identity=from_reference.factual_summary_identity,
        acid_commentary_identity=from_reference.acid_commentary_identity,
        event_authority_identity=from_reference.event_authority_identity,
    )
    to_endpoint = TransitionEndpointV1(
        chief_story_reference_identity=to_identity,
        event_id=to_reference.event_id,
        story_revision_identity=to_reference.story_revision_identity,
        factual_summary_identity=to_reference.factual_summary_identity,
        acid_commentary_identity=to_reference.acid_commentary_identity,
        event_authority_identity=to_reference.event_authority_identity,
    )
    bounded_input = {
        "from": {
            "factual_summary": from_story.factual_summary_text,
            "acid_commentary": from_story.acid_commentary_text,
            "event_authority_identity": from_reference.event_authority_identity,
        },
        "to": {
            "factual_summary": to_story.factual_summary_text,
            "acid_commentary": to_story.acid_commentary_text,
            "event_authority_identity": to_reference.event_authority_identity,
        },
        "transition_intent": transition_intent,
    }
    return TransitionAdjacencySlotV1(
        adjacency_identity=_identity((from_identity, to_identity)),
        from_story=from_endpoint,
        to_story=to_endpoint,
        transition_input_identity=_identity(bounded_input),
        transition_intent=transition_intent,
        state=PublicTransitionStateV1.UNAVAILABLE,
    )


def reconcile_transition_workflow(
    *,
    references_and_intents: tuple[
        tuple[ChiefEditorV2StoryReferenceV1 | None, str, str], ...
    ],
    existing: ChiefEditorTransitionWorkflowSidecarV1 | None,
    now: datetime,
) -> ChiefEditorTransitionWorkflowSidecarV1:
    """Preserve only unchanged exact directed adjacencies as active."""

    identities = tuple(
        (
            chief_story_reference_identity(reference)
            if reference is not None
            else f"historical-v1:{material_reference}"
        )
        for reference, material_reference, _intent in references_and_intents
    )
    desired = tuple(
        build_transition_adjacency_slot(
            from_reference=left[0],
            to_reference=right[0],
            transition_intent=left[2],
        )
        for left, right in pairwise(references_and_intents)
        if left[0] is not None and right[0] is not None
    )
    existing_by_identity = (
        {}
        if existing is None
        else {item.adjacency_identity: item for item in existing.active_slots}
    )
    active = tuple(
        existing_by_identity.get(item.adjacency_identity, item)
        if existing_by_identity.get(item.adjacency_identity, item).transition_input_identity
        == item.transition_input_identity
        else item
        for item in desired
    )
    active_ids = {item.adjacency_identity for item in active}
    retired = (
        () if existing is None else existing.retired_slots
    ) + tuple(
        item
        for item in (() if existing is None else existing.active_slots)
        if item.adjacency_identity not in active_ids
        or item.transition_input_identity
        != next(
            (
                candidate.transition_input_identity
                for candidate in active
                if candidate.adjacency_identity == item.adjacency_identity
            ),
            None,
        )
    )
    return ChiefEditorTransitionWorkflowSidecarV1(
        ordered_chief_story_identities=identities,
        active_slots=active,
        retired_slots=retired,
        created_at=now if existing is None else existing.created_at,
        updated_at=now,
    )


def canonical_transition_sidecar_bytes(
    sidecar: ChiefEditorTransitionWorkflowSidecarV1,
) -> bytes:
    return (
        json.dumps(
            sidecar.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


class ChiefEditorTransitionWorkflowStoreV1:
    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, sidecar: ChiefEditorTransitionWorkflowSidecarV1) -> str:
        payload = canonical_transition_sidecar_bytes(sidecar)
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
            raise ValueError("transition sidecar read-back mismatch")
        return _identity(json.loads(payload))

    def load(self) -> ChiefEditorTransitionWorkflowSidecarV1:
        raw = self.path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict) or (
            value.get("schema_name") != TRANSITION_WORKFLOW_SCHEMA_NAME
            or value.get("schema_version") != TRANSITION_WORKFLOW_SCHEMA_VERSION
        ):
            raise ValueError("unsupported transition sidecar version")
        sidecar = ChiefEditorTransitionWorkflowSidecarV1.model_validate(value)
        if canonical_transition_sidecar_bytes(sidecar) != raw:
            raise ValueError("transition sidecar is not canonical")
        return sidecar


def transition_sidecar_path(project_path: Path) -> Path:
    return project_path.with_suffix(project_path.suffix + ".transitions-v1.json")


__all__ = (
    "AcceptedTransitionV1",
    "ChiefEditorTransitionWorkflowSidecarV1",
    "ChiefEditorTransitionWorkflowStoreV1",
    "PublicTransitionStateV1",
    "TransitionAdjacencySlotV1",
    "TransitionAttemptV1",
    "TransitionEndpointV1",
    "TransitionValidationResultV1",
    "build_transition_adjacency_slot",
    "canonical_transition_sidecar_bytes",
    "chief_story_reference_identity",
    "reconcile_transition_workflow",
    "transition_sidecar_path",
)
