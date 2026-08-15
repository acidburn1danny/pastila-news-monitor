"""Provider-free publication of one prepared Episode Draft revision."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from itertools import pairwise
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.editor.generation.models import (
    DraftTransition,
    EpisodeDraft,
    derive_assembled_text,
)
from pastila_scout.episode_draft_assembly_v1 import (
    EpisodeDraftAssemblyErrorV1,
    EpisodeDraftAssemblyInputV1,
    EpisodeDraftAssemblyPreparerV1,
)
from pastila_scout.episode_draft_v1 import (
    EpisodeDraftPersistenceError,
    EpisodeDraftRevisionRefV1,
    EpisodeDraftRevisionRepositoryV1,
    EpisodeDraftRevisionV1,
)


class EpisodeDraftExecutionStageV1(StrEnum):
    PRECONDITION = "precondition"
    PUBLICATION = "publication"


class EpisodeDraftExecutionErrorCodeV1(StrEnum):
    INVALID_REQUEST = "invalid_request"
    STALE_INPUT = "stale_input"
    INVALID_PARENT = "invalid_parent"
    PUBLICATION_FAILED = "publication_failed"
    PUBLICATION_COLLISION = "publication_collision"


class EpisodeDraftExecutionErrorV1(ValueError):
    """Typed failure before a trustworthy publication result is available."""

    def __init__(
        self,
        code: EpisodeDraftExecutionErrorCodeV1,
        *,
        stage: EpisodeDraftExecutionStageV1,
    ) -> None:
        self.code = code
        self.stage = stage
        super().__init__(f"episode draft execution failed: {code.value}")


class EpisodeDraftPublicationStatusV1(StrEnum):
    PUBLISHED = "published"
    ALREADY_PUBLISHED = "already_published"


class EpisodeDraftActivationStatusV1(StrEnum):
    ACTIVATED = "activated"
    ALREADY_CURRENT = "already_current"
    FAILED = "failed"


class EpisodeDraftExecutionResultV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    project_id: str = Field(min_length=1)
    reference: EpisodeDraftRevisionRefV1
    parent_revision_id: str | None
    included_count: int = Field(ge=5)
    excluded_failure_count: int = Field(ge=0)
    publication_status: EpisodeDraftPublicationStatusV1
    activation_status: EpisodeDraftActivationStatusV1

    @model_validator(mode="after")
    def validate_result(self):
        if (
            self.project_id != self.reference.project_id
            or self.parent_revision_id != self.reference.parent_revision_id
            or self.included_count != len(self.reference.included_event_ids)
            or self.excluded_failure_count
            != len(self.reference.excluded_failed_event_ids)
        ):
            raise ValueError("invalid episode draft execution result")
        return self


class EpisodeDraftExecutorV1:
    """Publish and activate exactly one immutable prepared revision."""

    def __init__(
        self,
        *,
        store,
        revision_root: Path,
        preparer=None,
        repository=None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self.revision_root = revision_root
        self.preparer = preparer or EpisodeDraftAssemblyPreparerV1(store=store)
        self.repository = repository or EpisodeDraftRevisionRepositoryV1()
        self.clock = clock or (lambda: datetime.now(UTC))

    def execute(
        self, *, prepared: EpisodeDraftAssemblyInputV1
    ) -> EpisodeDraftExecutionResultV1:
        if (
            type(prepared) is not EpisodeDraftAssemblyInputV1
            or not isinstance(self.revision_root, Path)
            or not self.revision_root.is_absolute()
        ):
            _fail(EpisodeDraftExecutionErrorCodeV1.INVALID_REQUEST)
        revision_id = _revision_id(prepared)
        destination = self.revision_root / f"{revision_id.split(':')[-1]}.json"
        project = self.store.load_runtime_state()
        if (
            project is not None
            and project.current_episode_draft_revision is not None
            and project.current_episode_draft_revision.revision_id == revision_id
        ):
            if (
                Path(project.current_episode_draft_revision.artifact_path)
                != destination
            ):
                _fail(EpisodeDraftExecutionErrorCodeV1.STALE_INPUT)
            try:
                revision = self.store.load_episode_draft_revision()
                authoritative = self.preparer.prepare()
            except Exception as exc:
                raise EpisodeDraftExecutionErrorV1(
                    EpisodeDraftExecutionErrorCodeV1.STALE_INPUT,
                    stage=EpisodeDraftExecutionStageV1.PRECONDITION,
                ) from exc
            if (
                revision is None
                or authoritative.parent_revision_id != revision_id
                or not _same_preparation_state(authoritative, prepared)
                or not _same_revision(
                    revision, _revision(prepared, revision.created_at, revision_id)
                )
            ):
                _fail(EpisodeDraftExecutionErrorCodeV1.STALE_INPUT)
            return _result(
                prepared,
                project.current_episode_draft_revision,
                EpisodeDraftPublicationStatusV1.ALREADY_PUBLISHED,
                EpisodeDraftActivationStatusV1.ALREADY_CURRENT,
            )
        try:
            authoritative = self.preparer.prepare()
        except EpisodeDraftAssemblyErrorV1 as exc:
            raise EpisodeDraftExecutionErrorV1(
                EpisodeDraftExecutionErrorCodeV1.STALE_INPUT,
                stage=EpisodeDraftExecutionStageV1.PRECONDITION,
            ) from exc
        if authoritative != prepared:
            _fail(EpisodeDraftExecutionErrorCodeV1.STALE_INPUT)

        project = self.store.load_runtime_state()
        if project is None or project.project_id != prepared.project_id:
            _fail(EpisodeDraftExecutionErrorCodeV1.STALE_INPUT)
        current = project.current_episode_draft_revision
        if (current is None) != (prepared.parent_revision_id is None):
            _fail(EpisodeDraftExecutionErrorCodeV1.INVALID_PARENT)
        if current is not None:
            try:
                parent = self.store.load_episode_draft_revision()
            except Exception as exc:
                raise EpisodeDraftExecutionErrorV1(
                    EpisodeDraftExecutionErrorCodeV1.INVALID_PARENT,
                    stage=EpisodeDraftExecutionStageV1.PRECONDITION,
                ) from exc
            if (
                parent is None
                or parent.revision_id != prepared.parent_revision_id
                or parent.project_id != prepared.project_id
                or parent.draft_id != prepared.draft_id
            ):
                _fail(EpisodeDraftExecutionErrorCodeV1.INVALID_PARENT)

        publication_status = EpisodeDraftPublicationStatusV1.PUBLISHED
        if destination.exists():
            reference, revision = self._load_existing(destination)
            if not _same_revision(
                revision, _revision(prepared, revision.created_at, revision_id)
            ):
                raise EpisodeDraftExecutionErrorV1(
                    EpisodeDraftExecutionErrorCodeV1.PUBLICATION_COLLISION,
                    stage=EpisodeDraftExecutionStageV1.PUBLICATION,
                )
            publication_status = EpisodeDraftPublicationStatusV1.ALREADY_PUBLISHED
        else:
            created_at = self.clock()
            if created_at.tzinfo is None or created_at.utcoffset() is None:
                _fail(EpisodeDraftExecutionErrorCodeV1.INVALID_REQUEST)
            revision = _revision(prepared, created_at, revision_id)
            try:
                reference = self.repository.publish(
                    revision=revision, destination=destination
                )
            except EpisodeDraftPersistenceError as exc:
                raise EpisodeDraftExecutionErrorV1(
                    EpisodeDraftExecutionErrorCodeV1.PUBLICATION_FAILED,
                    stage=EpisodeDraftExecutionStageV1.PUBLICATION,
                ) from exc

        current = self.store.load_runtime_state()
        if current is not None and current.current_episode_draft_revision == reference:
            return _result(
                prepared,
                reference,
                publication_status,
                EpisodeDraftActivationStatusV1.ALREADY_CURRENT,
            )
        try:
            self.store.install_episode_draft_revision(reference=reference)
            restored = self.store.load_runtime_state()
            loaded = self.store.load_episode_draft_revision()
            if (
                restored is None
                or restored.current_episode_draft_revision != reference
                or loaded is None
                or not _same_revision(loaded, revision)
            ):
                raise ValueError("episode draft activation verification failed")
        except EpisodeDraftPersistenceError, OSError, TypeError, ValueError:
            return _result(
                prepared,
                reference,
                publication_status,
                EpisodeDraftActivationStatusV1.FAILED,
            )
        return _result(
            prepared,
            reference,
            publication_status,
            EpisodeDraftActivationStatusV1.ACTIVATED,
        )

    def _load_existing(self, destination: Path):
        try:
            artifact_sha256 = (
                "sha256:" + hashlib.sha256(destination.read_bytes()).hexdigest()
            )
            revision = self.repository.load(
                path=destination, artifact_sha256=artifact_sha256
            )
            reference = EpisodeDraftRevisionRefV1(
                draft_id=revision.draft_id,
                revision_id=revision.revision_id,
                parent_revision_id=revision.parent_revision_id,
                project_id=revision.project_id,
                episode_id=revision.episode_id,
                artifact_path=str(destination),
                artifact_sha256=artifact_sha256,
                requested_event_ids=revision.requested_event_ids,
                included_event_ids=revision.included_event_ids,
                excluded_failed_event_ids=revision.excluded_failed_event_ids,
                created_at=revision.created_at,
            )
            return reference, revision
        except Exception as exc:
            raise EpisodeDraftExecutionErrorV1(
                EpisodeDraftExecutionErrorCodeV1.PUBLICATION_COLLISION,
                stage=EpisodeDraftExecutionStageV1.PUBLICATION,
            ) from exc


def _revision(
    prepared: EpisodeDraftAssemblyInputV1,
    created_at: datetime,
    revision_id: str,
) -> EpisodeDraftRevisionV1:
    transitions = tuple(
        DraftTransition(from_story_id=left, to_story_id=right, text="")
        for left, right in pairwise(prepared.included_event_ids)
    )
    assembled = derive_assembled_text(
        opening="",
        stories=prepared.stories,
        transitions=transitions,
        closing="",
        cta=None,
    )
    draft = EpisodeDraft(
        episode_id=prepared.draft_id,
        opening="",
        stories=prepared.stories,
        transitions=transitions,
        closing="",
        cta=None,
        assembled_text=assembled,
        teleprompter_text=assembled,
    )
    return EpisodeDraftRevisionV1(
        draft_id=prepared.draft_id,
        revision_id=revision_id,
        parent_revision_id=prepared.parent_revision_id,
        project_id=prepared.project_id,
        episode_id=prepared.draft_id,
        created_at=created_at,
        requested_event_ids=prepared.requested_event_ids,
        included_event_ids=prepared.included_event_ids,
        excluded_failed_event_ids=prepared.excluded_failed_event_ids,
        included_materials=prepared.included_materials,
        excluded_failures=prepared.excluded_failures,
        episode_draft=draft,
        provenance_references=tuple(
            item.material_reference for item in prepared.included_materials
        ),
    )


def _revision_id(prepared: EpisodeDraftAssemblyInputV1) -> str:
    identity = hashlib.sha256(
        (
            "episode-draft-execution-v1\n"
            + prepared.preparation_fingerprint
            + "\n"
            + (prepared.parent_revision_id or "")
        ).encode("utf-8")
    ).hexdigest()
    return f"episode-draft-revision-v1:{identity}"


def _same_revision(left: EpisodeDraftRevisionV1, right: EpisodeDraftRevisionV1) -> bool:
    return left.model_dump(exclude={"payload_sha256"}) == right.model_dump(
        exclude={"payload_sha256"}
    )


def _same_preparation_state(
    left: EpisodeDraftAssemblyInputV1, right: EpisodeDraftAssemblyInputV1
) -> bool:
    excluded = {"parent_revision_id", "preparation_fingerprint"}
    return left.model_dump(exclude=excluded) == right.model_dump(exclude=excluded)


def _result(prepared, reference, publication_status, activation_status):
    return EpisodeDraftExecutionResultV1(
        project_id=prepared.project_id,
        reference=reference,
        parent_revision_id=prepared.parent_revision_id,
        included_count=len(prepared.included_event_ids),
        excluded_failure_count=len(prepared.excluded_failed_event_ids),
        publication_status=publication_status,
        activation_status=activation_status,
    )


def _fail(code: EpisodeDraftExecutionErrorCodeV1):
    raise EpisodeDraftExecutionErrorV1(
        code, stage=EpisodeDraftExecutionStageV1.PRECONDITION
    )


__all__ = (
    "EpisodeDraftActivationStatusV1",
    "EpisodeDraftExecutionErrorCodeV1",
    "EpisodeDraftExecutionErrorV1",
    "EpisodeDraftExecutionResultV1",
    "EpisodeDraftExecutionStageV1",
    "EpisodeDraftExecutorV1",
    "EpisodeDraftPublicationStatusV1",
)
