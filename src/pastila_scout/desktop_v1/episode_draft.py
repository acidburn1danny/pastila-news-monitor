"""Thin desktop projection for deterministic Episode Draft publication."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from pastila_scout.episode_draft_assembly_v1 import (
    EpisodeDraftAssemblyErrorCodeV1,
    EpisodeDraftAssemblyErrorV1,
    EpisodeDraftAssemblyPreparerV1,
)
from pastila_scout.episode_draft_execution_v1 import (
    EpisodeDraftActivationStatusV1,
    EpisodeDraftExecutionErrorCodeV1,
    EpisodeDraftExecutionErrorV1,
    EpisodeDraftExecutorV1,
    _state_reference,
)
from pastila_scout.episode_draft_v1 import EpisodeDraftPersistenceError


@dataclass(frozen=True, slots=True)
class _EpisodeDraftDesktopProjectionV1:
    status: str
    current: bool = False
    revision_id: str = ""
    parent_revision_id: str = ""
    included: tuple[tuple[int, str, str], ...] = ()
    excluded: tuple[tuple[int, str, str], ...] = ()
    assembled_text: str = ""


def _publish_episode_draft_v1(
    *, store, revision_root: Path
) -> _EpisodeDraftDesktopProjectionV1:
    try:
        prepared = EpisodeDraftAssemblyPreparerV1(store=store).prepare()
        result = EpisodeDraftExecutorV1(
            store=store, revision_root=revision_root
        ).execute(prepared=prepared)
        if result.activation_status is EpisodeDraftActivationStatusV1.FAILED:
            return _error("Draftul a fost publicat, dar nu a putut fi activat.")
        return _project_current(
            store,
            status=(
                "Draftul episodului este deja curent."
                if result.activation_status
                is EpisodeDraftActivationStatusV1.ALREADY_CURRENT
                else "Draftul episodului a fost creat si activat."
            ),
        )
    except EpisodeDraftAssemblyErrorV1 as exc:
        if exc.code is EpisodeDraftAssemblyErrorCodeV1.MINIMUM_STORIES:
            return _error(
                f"Sunt necesare cel putin 5 stiri generate; disponibile: "
                f"{exc.available}."
            )
        if exc.code is EpisodeDraftAssemblyErrorCodeV1.STALE_PROJECT:
            return _error("Starea Chief Editor s-a schimbat. Incercati din nou.")
        return _error("Starea Chief Editor nu este pregatita pentru draft.")
    except EpisodeDraftExecutionErrorV1 as exc:
        messages = {
            EpisodeDraftExecutionErrorCodeV1.STALE_INPUT: (
                "Starea Chief Editor s-a schimbat. Incercati din nou."
            ),
            EpisodeDraftExecutionErrorCodeV1.INVALID_PARENT: (
                "Revizia curenta sau parintele ei nu este valid."
            ),
            EpisodeDraftExecutionErrorCodeV1.PUBLICATION_FAILED: (
                "Draftul episodului nu a putut fi publicat."
            ),
            EpisodeDraftExecutionErrorCodeV1.PUBLICATION_COLLISION: (
                "Exista un conflict cu revizia draftului episodului."
            ),
            EpisodeDraftExecutionErrorCodeV1.INVALID_REQUEST: (
                "Cererea pentru draftul episodului nu este valida."
            ),
        }
        return _error(messages[exc.code])
    except EpisodeDraftPersistenceError, OSError, TypeError, ValueError:
        return _error("Draftul episodului nu a putut fi verificat.")


def _recover_episode_draft_v1(*, store) -> _EpisodeDraftDesktopProjectionV1:
    try:
        project = store.load_runtime_state()
        if project is None:
            return _EpisodeDraftDesktopProjectionV1(
                status="Nu exista un draft de episod publicat."
            )
        if project.current_episode_draft_revision is None:
            available = sum(
                item.status.value == "completed" for item in project.editor_worklist
            )
            return _EpisodeDraftDesktopProjectionV1(
                status=(
                    "Nu exista un draft de episod publicat."
                    if available >= 5
                    else (
                        "Sunt necesare cel putin 5 stiri generate; "
                        f"disponibile: {available}."
                    )
                )
            )
        projection = _project_current(store, status="Draftul episodului este curent.")
    except EpisodeDraftPersistenceError, OSError, TypeError, ValueError:
        return _error("Draftul episodului salvat nu a putut fi recuperat.")
    try:
        prepared = EpisodeDraftAssemblyPreparerV1(store=store).prepare()
        revision = store.load_episode_draft_revision()
        if revision is not None and _state_reference(prepared) in (
            revision.provenance_references
        ):
            return projection
    except EpisodeDraftAssemblyErrorV1:
        pass
    return replace(
        projection,
        status=(
            "Draftul publicat este inspectabil, dar nu mai corespunde "
            "structurii curente."
        ),
    )


def _project_current(store, *, status: str) -> _EpisodeDraftDesktopProjectionV1:
    project = store.load_runtime_state()
    revision = store.load_episode_draft_revision()
    if project is None or revision is None:
        raise EpisodeDraftPersistenceError("current revision is unavailable")
    materials = {item.event_id: item for item in project.editor_materials}
    included_values = []
    for event_id, lineage in zip(
        revision.included_event_ids, revision.included_materials, strict=True
    ):
        material = materials.get(event_id)
        if material is None:
            raise EpisodeDraftPersistenceError("included material title is unavailable")
        included_values.append((event_id, material.title, lineage.material_reference))
    included = tuple(included_values)
    return _EpisodeDraftDesktopProjectionV1(
        status=(
            f"{status} {len(included)} stiri incluse, "
            f"{len(revision.excluded_failures)} excluse."
        ),
        current=True,
        revision_id=revision.revision_id,
        parent_revision_id=revision.parent_revision_id or "",
        included=included,
        excluded=tuple(
            (item.event_id, item.title_snapshot, item.sanitized_reason)
            for item in revision.excluded_failures
        ),
        assembled_text=revision.episode_draft.assembled_text,
    )


def _error(status: str) -> _EpisodeDraftDesktopProjectionV1:
    return _EpisodeDraftDesktopProjectionV1(status=status)


__all__: tuple[str, ...] = ()
