from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_episode_draft_persistence_v1 import _active_project, _story

from pastila_scout.active_project_v1 import (
    EditorMaterialV1,
    EditorWorkItemStatusV1,
    EditorWorkItemV1,
)
from pastila_scout.editor.generation.models import EpisodeDraft
from pastila_scout.episode_draft_assembly_v1 import (
    EpisodeDraftAssemblyErrorCodeV1,
    EpisodeDraftAssemblyErrorV1,
    EpisodeDraftAssemblyInputV1,
    EpisodeDraftAssemblyPreparerV1,
)
from pastila_scout.episode_draft_v1 import EpisodeDraftExcludedFailureV1


def _failure(event_id: int = 12, *, attempts: int = 3):
    return EpisodeDraftExcludedFailureV1(
        event_id=event_id,
        title_snapshot=f"Material {event_id}",
        attempt_count=attempts,
        failure_stage="timeout",
        failure_category="provider_timeout",
        sanitized_reason="Ollama timeout.",
        failure_evidence_reference=f"attempts:event:{event_id}",
    )


class Loader:
    def __init__(self, *, wrong_id: int | None = None, story_count: int = 1):
        self.wrong_id = wrong_id
        self.story_count = story_count
        self.calls = []
        self.stories = {}

    def __call__(self, *, path: Path, payload_sha256: str):
        self.calls.append((path, payload_sha256))
        event_id = int(path.stem.split("-")[-1])
        story_id = self.wrong_id if self.wrong_id is not None else event_id
        stories = tuple(_story(story_id) for _ in range(self.story_count))
        if self.story_count == 1:
            self.stories[event_id] = stories[0]
        return SimpleNamespace(
            draft=EpisodeDraft.model_construct(
                episode_id=f"one-story:{event_id}",
                opening=f"PER-STORY OPENING {event_id}",
                stories=stories,
                transitions=(),
                closing=f"PER-STORY CLOSING {event_id}",
                cta=None,
                assembled_text=f"PER-STORY ASSEMBLED {event_id}",
                teleprompter_text=f"PER-STORY TELEPROMPTER {event_id}",
            )
        )


def _ready(tmp_path: Path, *, attempts: int = 3):
    store, _project = _active_project(tmp_path)
    store.record_terminal_editor_failure(evidence=_failure(attempts=attempts))
    return store, store.load_runtime_state()


def test_five_completed_and_one_terminal_failure_prepare_in_worklist_order(
    tmp_path: Path,
) -> None:
    store, project = _ready(tmp_path)
    shuffled = replace(
        project,
        editor_materials=tuple(reversed(project.editor_materials)),
    )
    store._write(shuffled)
    loader = Loader()

    prepared = EpisodeDraftAssemblyPreparerV1(
        store=store, artifact_loader=loader
    ).prepare()

    assert prepared.requested_event_ids == (7, 8, 9, 10, 11, 12)
    assert prepared.included_event_ids == (7, 8, 9, 10, 11)
    assert prepared.excluded_failed_event_ids == (12,)
    assert prepared.excluded_failures[0].attempt_count == 3
    assert all(
        story is loader.stories[event_id]
        for story, event_id in zip(
            prepared.stories, prepared.included_event_ids, strict=True
        )
    )
    assert "PER-STORY" not in repr(prepared)
    assert prepared.excluded_failures[0].sanitized_reason not in tuple(
        story.factual_summary for story in prepared.stories
    )
    assert (
        prepared
        == EpisodeDraftAssemblyPreparerV1(store=store, artifact_loader=loader).prepare()
    )
    assert store.load_runtime_state() == shuffled


def test_fail_fast_terminal_failure_is_valid(tmp_path: Path) -> None:
    store, _ = _ready(tmp_path, attempts=1)
    prepared = EpisodeDraftAssemblyPreparerV1(
        store=store, artifact_loader=Loader()
    ).prepare()
    assert prepared.excluded_failures[0].attempt_count == 1


def test_preparation_model_rejects_boolean_or_nonpositive_lineage(
    tmp_path: Path,
) -> None:
    store, _ = _ready(tmp_path)
    prepared = EpisodeDraftAssemblyPreparerV1(
        store=store, artifact_loader=Loader()
    ).prepare()
    values = prepared.model_dump(mode="python")
    for field, replacement in (
        ("requested_event_ids", (True, *prepared.requested_event_ids[1:])),
        ("included_event_ids", (0, *prepared.included_event_ids[1:])),
        ("excluded_failed_event_ids", (True,)),
    ):
        changed = dict(values)
        changed[field] = replacement
        with pytest.raises(ValueError):
            EpisodeDraftAssemblyInputV1.model_validate(changed)


def test_running_item_is_unresolved(tmp_path: Path) -> None:
    store, project = _ready(tmp_path)
    store._write(
        replace(
            project,
            editor_worklist=(
                EditorWorkItemV1(7, EditorWorkItemStatusV1.RUNNING),
                *project.editor_worklist[1:],
            ),
        )
    )
    with pytest.raises(EpisodeDraftAssemblyErrorV1) as captured:
        EpisodeDraftAssemblyPreparerV1(store=store, artifact_loader=Loader()).prepare()
    assert captured.value.code is EpisodeDraftAssemblyErrorCodeV1.UNRESOLVED_ITEM


def test_pending_item_is_excluded_from_publication_request(tmp_path: Path) -> None:
    store, project = _ready(tmp_path)
    store._write(
        replace(
            project,
            editor_worklist=(
                *project.editor_worklist[:5],
                EditorWorkItemV1(12, EditorWorkItemStatusV1.PENDING),
            ),
            editor_terminal_failures=(),
        )
    )

    prepared = EpisodeDraftAssemblyPreparerV1(
        store=store, artifact_loader=Loader()
    ).prepare()

    assert prepared.requested_event_ids == (7, 8, 9, 10, 11)
    assert prepared.included_event_ids == (7, 8, 9, 10, 11)
    assert prepared.excluded_failed_event_ids == ()


def test_failed_without_terminal_evidence_is_unresolved(tmp_path: Path) -> None:
    store, _ = _active_project(tmp_path)
    with pytest.raises(EpisodeDraftAssemblyErrorV1) as captured:
        EpisodeDraftAssemblyPreparerV1(store=store, artifact_loader=Loader()).prepare()
    assert (
        captured.value.code is EpisodeDraftAssemblyErrorCodeV1.TERMINAL_EVIDENCE_MISSING
    )


@pytest.mark.parametrize("completed_count", range(5))
def test_fewer_than_five_completed_stories_reports_available_count(
    tmp_path: Path, completed_count: int
) -> None:
    store, project = _ready(tmp_path)
    included_ids = tuple(
        item.event_id for item in project.editor_worklist[:completed_count]
    )
    failed_ids = tuple(
        item.event_id for item in project.editor_worklist[completed_count:]
    )
    changed = replace(
        project,
        editor_worklist=tuple(
            EditorWorkItemV1(item.event_id, EditorWorkItemStatusV1.FAILED)
            if item.event_id in failed_ids
            else EditorWorkItemV1(item.event_id, EditorWorkItemStatusV1.COMPLETED)
            for item in project.editor_worklist
        ),
        editor_materials=tuple(
            item for item in project.editor_materials if item.event_id in included_ids
        ),
        editor_terminal_failures=tuple(_failure(event_id) for event_id in failed_ids),
    )
    store._write(changed)
    with pytest.raises(EpisodeDraftAssemblyErrorV1) as captured:
        EpisodeDraftAssemblyPreparerV1(store=store, artifact_loader=Loader()).prepare()
    assert captured.value.code is EpisodeDraftAssemblyErrorCodeV1.MINIMUM_STORIES
    assert captured.value.available == completed_count
    assert captured.value.minimum == 5


def test_more_than_five_completed_stories_are_all_included(tmp_path: Path) -> None:
    store, project = _ready(tmp_path)
    material = EditorMaterialV1(
        "editor-material-v1:event:12",
        12,
        "Material 12",
        "Rezumat 12",
        str(tmp_path / "editor-12.json"),
        "sha256:" + f"{12:064x}",
    )
    store._write(
        replace(
            project,
            editor_materials=(*project.editor_materials, material),
            editor_worklist=tuple(
                EditorWorkItemV1(item.event_id, EditorWorkItemStatusV1.COMPLETED)
                for item in project.editor_worklist
            ),
            editor_terminal_failures=(),
        )
    )
    prepared = EpisodeDraftAssemblyPreparerV1(
        store=store, artifact_loader=Loader()
    ).prepare()
    assert prepared.included_event_ids == (7, 8, 9, 10, 11, 12)
    assert prepared.excluded_failed_event_ids == ()


def test_terminal_failure_with_material_is_rejected(tmp_path: Path) -> None:
    store, project = _ready(tmp_path)
    store._write(
        replace(
            project,
            editor_materials=(
                *project.editor_materials,
                EditorMaterialV1(
                    "editor-material-v1:event:12",
                    12,
                    "Material 12",
                    "Rezumat 12",
                    str(tmp_path / "editor-12.json"),
                    "sha256:" + f"{12:064x}",
                ),
            ),
        )
    )
    with pytest.raises(EpisodeDraftAssemblyErrorV1) as captured:
        EpisodeDraftAssemblyPreparerV1(store=store, artifact_loader=Loader()).prepare()
    assert captured.value.code is EpisodeDraftAssemblyErrorCodeV1.UNRESOLVED_ITEM


@pytest.mark.parametrize("mutation", ("missing", "duplicate", "unknown", "checksum"))
def test_material_ambiguity_or_invalid_lineage_is_rejected(
    tmp_path: Path, mutation: str
) -> None:
    store, project = _ready(tmp_path)
    materials = project.editor_materials
    if mutation == "missing":
        changed = materials[1:]
    elif mutation == "duplicate":
        changed = (*materials, materials[0])
    elif mutation == "unknown":
        changed = (*materials, replace(materials[0], event_id=999, reference="m:999"))
    else:
        changed = (
            materials[0],
            replace(materials[1], payload_sha256=materials[0].payload_sha256),
            *materials[2:],
        )
    store._write(replace(project, editor_materials=changed))
    with pytest.raises(EpisodeDraftAssemblyErrorV1):
        EpisodeDraftAssemblyPreparerV1(store=store, artifact_loader=Loader()).prepare()


def test_artifact_failure_and_story_identity_mismatch_are_bounded(
    tmp_path: Path,
) -> None:
    store, _ = _ready(tmp_path)

    def corrupt(**kwargs):
        del kwargs
        raise ValueError("private artifact detail")

    with pytest.raises(EpisodeDraftAssemblyErrorV1) as corrupt_error:
        EpisodeDraftAssemblyPreparerV1(store=store, artifact_loader=corrupt).prepare()
    assert corrupt_error.value.code is EpisodeDraftAssemblyErrorCodeV1.INVALID_ARTIFACT
    with pytest.raises(EpisodeDraftAssemblyErrorV1) as identity_error:
        EpisodeDraftAssemblyPreparerV1(
            store=store, artifact_loader=Loader(wrong_id=999)
        ).prepare()
    assert (
        identity_error.value.code
        is EpisodeDraftAssemblyErrorCodeV1.STORY_IDENTITY_MISMATCH
    )
    with pytest.raises(EpisodeDraftAssemblyErrorV1) as multiple_error:
        EpisodeDraftAssemblyPreparerV1(
            store=store, artifact_loader=Loader(story_count=2)
        ).prepare()
    assert multiple_error.value.code is EpisodeDraftAssemblyErrorCodeV1.INVALID_ARTIFACT


def test_changed_project_during_artifact_loading_is_rejected_as_stale(
    tmp_path: Path,
) -> None:
    store, project = _ready(tmp_path)
    loader = Loader()
    calls = 0

    def changing_loader(**kwargs):
        nonlocal calls
        calls += 1
        result = loader(**kwargs)
        if calls == 1:
            store._write(replace(project, chief_editor_title="Concurrent change"))
        return result

    with pytest.raises(EpisodeDraftAssemblyErrorV1) as captured:
        EpisodeDraftAssemblyPreparerV1(
            store=store, artifact_loader=changing_loader
        ).prepare()
    assert captured.value.code is EpisodeDraftAssemblyErrorCodeV1.STALE_PROJECT


def test_terminal_failure_evidence_persists_and_rejects_conflicts(
    tmp_path: Path,
) -> None:
    store, project = _active_project(tmp_path)
    updated = store.record_terminal_editor_failure(evidence=_failure())
    assert store.load().editor_terminal_failures == updated.editor_terminal_failures
    with pytest.raises(ValueError):
        store.record_terminal_editor_failure(evidence=_failure())
    conflicting = replace(
        project,
        editor_materials=(
            *project.editor_materials,
            EditorMaterialV1(
                "material:12", 12, "Titlu", "Rezumat", "x", "sha256:" + "f" * 64
            ),
        ),
    )
    store._write(conflicting)
    with pytest.raises(ValueError):
        store.record_terminal_editor_failure(evidence=_failure())


def test_terminal_failure_requires_authoritative_title_snapshot(tmp_path: Path) -> None:
    store, _ = _active_project(tmp_path)
    with pytest.raises(ValueError):
        store.record_terminal_editor_failure(
            evidence=_failure().model_copy(update={"title_snapshot": "Wrong title"})
        )


def test_diagnostic_change_changes_preparation_fingerprint(tmp_path: Path) -> None:
    store, project = _ready(tmp_path)
    first = EpisodeDraftAssemblyPreparerV1(
        store=store, artifact_loader=Loader()
    ).prepare()
    changed_failure = project.editor_terminal_failures[0].model_copy(
        update={"sanitized_reason": "Provider timed out before returning content."}
    )
    store._write(replace(project, editor_terminal_failures=(changed_failure,)))
    second = EpisodeDraftAssemblyPreparerV1(
        store=store, artifact_loader=Loader()
    ).prepare()
    assert second.preparation_fingerprint != first.preparation_fingerprint
