"""Deterministic preparation of persisted Editor materials for episode generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.active_project_v1 import EditorWorkItemStatusV1
from pastila_scout.editor.generation.models import DraftStory
from pastila_scout.editor_application_v1 import load_editor_operational_result_v1
from pastila_scout.episode_draft_v1 import (
    EpisodeDraftExcludedFailureV1,
    EpisodeDraftIncludedMaterialV1,
)


class EpisodeDraftAssemblyErrorCodeV1(StrEnum):
    INVALID_PROJECT = "invalid_project"
    UNRESOLVED_ITEM = "unresolved_item"
    TERMINAL_EVIDENCE_MISSING = "terminal_evidence_missing"
    INVALID_MATERIAL = "invalid_material"
    INVALID_ARTIFACT = "invalid_artifact"
    STORY_IDENTITY_MISMATCH = "story_identity_mismatch"
    MINIMUM_STORIES = "minimum_stories"
    STALE_PROJECT = "stale_project"


class EpisodeDraftAssemblyErrorV1(ValueError):
    def __init__(
        self,
        code: EpisodeDraftAssemblyErrorCodeV1,
        *,
        available: int = 0,
        minimum: int = 5,
    ):
        self.code = code
        self.available = available
        self.minimum = minimum
        super().__init__(f"episode draft assembly preparation failed: {code.value}")


class EpisodeDraftAssemblyInputV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    project_id: str = Field(min_length=1)
    draft_id: str = Field(min_length=1)
    parent_revision_id: str | None = Field(default=None, min_length=1)
    requested_event_ids: tuple[int, ...] = Field(min_length=5)
    included_event_ids: tuple[int, ...] = Field(min_length=5)
    excluded_failed_event_ids: tuple[int, ...]
    stories: tuple[DraftStory, ...] = Field(min_length=5)
    included_materials: tuple[EpisodeDraftIncludedMaterialV1, ...] = Field(min_length=5)
    excluded_failures: tuple[EpisodeDraftExcludedFailureV1, ...]
    scout_input_fingerprint: str = Field(min_length=1)
    chief_editor_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    preparation_fingerprint: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_input(self):
        requested = self.requested_event_ids
        included = self.included_event_ids
        excluded = self.excluded_failed_event_ids
        if (
            any(
                type(value) is not int or value <= 0
                for values in (requested, included, excluded)
                for value in values
            )
            or any(
                len(values) != len(set(values))
                for values in (requested, included, excluded)
            )
            or set(included).intersection(excluded)
            or set(included).union(excluded) != set(requested)
            or included != tuple(value for value in requested if value in set(included))
            or excluded != tuple(value for value in requested if value in set(excluded))
            or tuple(item.story_id for item in self.stories) != included
            or tuple(item.event_id for item in self.included_materials) != included
            or tuple(item.event_id for item in self.excluded_failures) != excluded
        ):
            raise ValueError("invalid assembly lineage")
        expected = _fingerprint(
            self.model_dump(mode="json", exclude={"preparation_fingerprint"})
        )
        if self.preparation_fingerprint != expected:
            raise ValueError("invalid preparation fingerprint")
        return self


class EpisodeDraftAssemblyPreparerV1:
    """Prepare one immutable input from one stable active-project snapshot."""

    def __init__(self, *, store, artifact_loader=load_editor_operational_result_v1):
        self.store = store
        self.artifact_loader = artifact_loader

    def prepare(self) -> EpisodeDraftAssemblyInputV1:
        project = self.store.load_runtime_state()
        if project is None:
            _raise(EpisodeDraftAssemblyErrorCodeV1.INVALID_PROJECT)
        worklist = project.editor_worklist
        worklist_ids = tuple(item.event_id for item in worklist)
        scout_ids = tuple(item.event_id for item in project.scout_input.ranked_events)
        if (
            not worklist_ids
            or worklist_ids != scout_ids
            or any(type(value) is not int or value <= 0 for value in worklist_ids)
            or len(worklist_ids) != len(set(worklist_ids))
        ):
            _raise(EpisodeDraftAssemblyErrorCodeV1.INVALID_PROJECT)
        if (
            len({item.event_id for item in project.editor_materials})
            != len(project.editor_materials)
            or len({item.reference for item in project.editor_materials})
            != len(project.editor_materials)
            or len({item.payload_sha256 for item in project.editor_materials})
            != len(project.editor_materials)
            or any(
                item.event_id not in set(worklist_ids)
                for item in project.editor_materials
            )
        ):
            _raise(EpisodeDraftAssemblyErrorCodeV1.INVALID_MATERIAL)
        materials = {item.event_id: item for item in project.editor_materials}
        failures = {item.event_id: item for item in project.editor_terminal_failures}
        if len(failures) != len(project.editor_terminal_failures) or any(
            event_id not in set(worklist_ids) for event_id in failures
        ):
            _raise(EpisodeDraftAssemblyErrorCodeV1.UNRESOLVED_ITEM)
        stories = []
        included_lineage = []
        excluded_evidence = []
        for item in worklist:
            event_id = item.event_id
            material = materials.get(event_id)
            failure = failures.get(event_id)
            if item.status is EditorWorkItemStatusV1.COMPLETED:
                if failure is not None or material is None:
                    _raise(EpisodeDraftAssemblyErrorCodeV1.INVALID_MATERIAL)
                if not material.output_path or not material.payload_sha256:
                    _raise(EpisodeDraftAssemblyErrorCodeV1.INVALID_MATERIAL)
                try:
                    result = self.artifact_loader(
                        path=Path(material.output_path),
                        payload_sha256=material.payload_sha256,
                    )
                except Exception as exc:
                    raise EpisodeDraftAssemblyErrorV1(
                        EpisodeDraftAssemblyErrorCodeV1.INVALID_ARTIFACT
                    ) from exc
                if result.draft is None or len(result.draft.stories) != 1:
                    _raise(EpisodeDraftAssemblyErrorCodeV1.INVALID_ARTIFACT)
                story = result.draft.stories[0]
                if story.story_id != event_id:
                    _raise(EpisodeDraftAssemblyErrorCodeV1.STORY_IDENTITY_MISMATCH)
                stories.append(story)
                included_lineage.append(
                    EpisodeDraftIncludedMaterialV1(
                        event_id=event_id,
                        material_reference=material.reference,
                        payload_sha256=material.payload_sha256,
                    )
                )
            elif item.status is EditorWorkItemStatusV1.FAILED:
                if failure is None:
                    _raise(EpisodeDraftAssemblyErrorCodeV1.TERMINAL_EVIDENCE_MISSING)
                if material is not None:
                    _raise(EpisodeDraftAssemblyErrorCodeV1.UNRESOLVED_ITEM)
                excluded_evidence.append(failure)
            elif item.status is EditorWorkItemStatusV1.RUNNING:
                _raise(EpisodeDraftAssemblyErrorCodeV1.UNRESOLVED_ITEM)
            # Pending work is not part of this immutable publication request.
        if len(stories) < 5:
            raise EpisodeDraftAssemblyErrorV1(
                EpisodeDraftAssemblyErrorCodeV1.MINIMUM_STORIES,
                available=len(stories),
            )
        included = tuple(item.story_id for item in stories)
        excluded = tuple(item.event_id for item in excluded_evidence)
        requested = tuple(
            item.event_id
            for item in worklist
            if item.status
            in (EditorWorkItemStatusV1.COMPLETED, EditorWorkItemStatusV1.FAILED)
        )
        values = {
            "project_id": project.project_id,
            "draft_id": (
                project.current_episode_draft_revision.draft_id
                if project.current_episode_draft_revision is not None
                else f"episode-draft-v1:{project.project_id}"
            ),
            "parent_revision_id": (
                None
                if project.current_episode_draft_revision is None
                else project.current_episode_draft_revision.revision_id
            ),
            "requested_event_ids": requested,
            "included_event_ids": included,
            "excluded_failed_event_ids": excluded,
            "stories": tuple(stories),
            "included_materials": tuple(included_lineage),
            "excluded_failures": tuple(excluded_evidence),
            "scout_input_fingerprint": project.scout_input.content_fingerprint,
            "chief_editor_fingerprint": _fingerprint(
                {
                    "title": project.chief_editor_title,
                    "updated_at": project.chief_editor_updated_at,
                    "items": project.chief_editor_items,
                }
            ),
        }
        values["preparation_fingerprint"] = _fingerprint(values)
        prepared = EpisodeDraftAssemblyInputV1(**values)
        if self.store.load_runtime_state() != project:
            _raise(EpisodeDraftAssemblyErrorCodeV1.STALE_PROJECT)
        return prepared


def _fingerprint(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
        default=_json_value,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _json_value(item):
    if hasattr(item, "model_dump"):
        return item.model_dump(mode="json")
    if isinstance(item, datetime):
        return item.isoformat()
    if is_dataclass(item):
        return asdict(item)
    raise TypeError(f"unsupported fingerprint value: {type(item).__name__}")


def _raise(code: EpisodeDraftAssemblyErrorCodeV1):
    raise EpisodeDraftAssemblyErrorV1(code)


__all__ = (
    "EpisodeDraftAssemblyErrorCodeV1",
    "EpisodeDraftAssemblyErrorV1",
    "EpisodeDraftAssemblyInputV1",
    "EpisodeDraftAssemblyPreparerV1",
)
