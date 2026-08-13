from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path

import pytest
from pydantic import ValidationError
from test_active_project_v1 import _additional_event, _database

from pastila_scout.active_project_v1 import (
    ActiveProjectStoreV1,
    EditorMaterialV1,
    EditorWorkItemStatusV1,
    EditorWorkItemV1,
)
from pastila_scout.editor.generation.models import (
    CommentaryBlockResult,
    DraftStory,
    DraftTransition,
    EpisodeDraft,
    derive_assembled_text,
)
from pastila_scout.episode_draft_v1 import (
    EpisodeDraftExcludedFailureV1,
    EpisodeDraftIncludedMaterialV1,
    EpisodeDraftPersistenceError,
    EpisodeDraftRevisionRepositoryV1,
    EpisodeDraftRevisionV1,
)


def _story(event_id: int) -> DraftStory:
    return DraftStory(
        story_id=event_id,
        factual_summary=f"Rezumat {event_id}",
        commentary_blocks=(
            CommentaryBlockResult(
                block_type="commentary",
                text=f"Comentariu {event_id}",
                sequence=1,
                source_fact_ids=(f"fact:{event_id}",),
                blueprint_intent_ids=(f"intent:{event_id}",),
                voice_plan_ids=(f"voice:{event_id}",),
                satire_target_ids=(),
                protected_target_ids=(),
            ),
        ),
        ending=f"Final {event_id}",
    )


def _draft(
    event_ids: tuple[int, ...], *, episode_id: str = "episode:1"
) -> EpisodeDraft:
    stories = tuple(_story(value) for value in event_ids)
    transitions = tuple(
        DraftTransition(from_story_id=left, to_story_id=right, text=f"{left}-{right}")
        for left, right in pairwise(event_ids)
    )
    assembled = derive_assembled_text(
        opening="Deschidere",
        stories=stories,
        transitions=transitions,
        closing="Inchidere",
        cta=None,
    )
    return EpisodeDraft(
        episode_id=episode_id,
        opening="Deschidere",
        stories=stories,
        transitions=transitions,
        closing="Inchidere",
        cta=None,
        assembled_text=assembled,
        teleprompter_text=assembled,
    )


def _revision(**changes) -> EpisodeDraftRevisionV1:
    included = (1, 2, 3, 4, 5)
    values = {
        "draft_id": "draft:1",
        "revision_id": "revision:1",
        "parent_revision_id": None,
        "project_id": "project:1",
        "episode_id": "episode:1",
        "created_at": datetime(2026, 8, 14, 9, 0, tzinfo=UTC),
        "requested_event_ids": (*included, 6),
        "included_event_ids": included,
        "excluded_failed_event_ids": (6,),
        "included_materials": tuple(
            EpisodeDraftIncludedMaterialV1(
                event_id=value,
                material_reference=f"editor-material-v1:event:{value}",
                payload_sha256="sha256:" + f"{value:064x}",
            )
            for value in included
        ),
        "excluded_failures": (
            EpisodeDraftExcludedFailureV1(
                event_id=6,
                attempt_count=3,
                failure_category="provider_timeout",
                sanitized_reason="Ollama timeout after the final attempt.",
                failure_evidence_reference="attempts:event:6",
            ),
        ),
        "episode_draft": _draft(included),
        "provenance_references": tuple(f"editor:event:{value}" for value in included),
    }
    values.update(changes)
    return EpisodeDraftRevisionV1(**values)


def test_valid_first_and_child_revision_and_canonical_round_trip(
    tmp_path: Path,
) -> None:
    repository = EpisodeDraftRevisionRepositoryV1()
    first = _revision()
    first_path = tmp_path / "revision-1.json"
    reference = repository.publish(revision=first, destination=first_path)
    restored = repository.load(
        path=first_path, artifact_sha256=reference.artifact_sha256
    )

    assert restored.revision_id == "revision:1"
    assert restored.payload_sha256.startswith("sha256:")
    assert restored.episode_draft == first.episode_draft
    assert first_path.read_bytes().endswith(b"\n")
    child = _revision(
        revision_id="revision:2", parent_revision_id=reference.revision_id
    )
    child_reference = repository.publish(
        revision=child, destination=tmp_path / "revision-2.json"
    )
    assert child_reference.parent_revision_id == "revision:1"


@pytest.mark.parametrize(
    "changes",
    (
        {"requested_event_ids": (1, 2, 3, 4, 5, 5)},
        {"requested_event_ids": (1, 2, 3, 4, 5, True)},
        {"included_event_ids": (1, 2, 3, 4, 6)},
        {"included_event_ids": (2, 1, 3, 4, 5)},
        {"included_event_ids": (1, 2, 3, 4)},
        {"excluded_failed_event_ids": ()},
        {"excluded_failed_event_ids": (5, 6)},
        {"excluded_failures": ()},
        {"episode_draft": _draft((1, 2, 3, 4, 7))},
    ),
)
def test_revision_rejects_invalid_story_partition(changes) -> None:
    with pytest.raises(ValidationError):
        _revision(**changes)


@pytest.mark.parametrize("count", range(5))
def test_ready_revision_requires_at_least_five_included_stories(count: int) -> None:
    included = tuple(range(1, count + 1))
    with pytest.raises(ValidationError):
        _revision(
            requested_event_ids=(*included, 6),
            included_event_ids=included,
            excluded_failed_event_ids=(6,),
            included_materials=tuple(
                EpisodeDraftIncludedMaterialV1(
                    event_id=value,
                    material_reference=f"material:{value}",
                    payload_sha256="sha256:" + f"{value:064x}",
                )
                for value in included
            ),
            episode_draft=_draft(included),
        )


def test_exclusion_rejects_blank_unsafe_or_excess_attempt_evidence() -> None:
    for values in (
        {"sanitized_reason": " "},
        {"sanitized_reason": "Authorization: Bearer secret"},
        {"sanitized_reason": "api key=secret"},
        {"sanitized_reason": "token=secret"},
        {"sanitized_reason": "sk-secret"},
        {"attempt_count": 4},
    ):
        with pytest.raises(ValidationError):
            EpisodeDraftExcludedFailureV1(
                event_id=6,
                attempt_count=values.get("attempt_count", 3),
                failure_category="timeout",
                sanitized_reason=values.get("sanitized_reason", "timeout"),
            )


def test_revision_rejects_blank_or_self_parent_identity() -> None:
    for changes in (
        {"draft_id": " "},
        {"project_id": " "},
        {"revision_id": " revision:1"},
        {"episode_id": "episode:e\u0301"},
        {"revision_id": "revision:1", "parent_revision_id": "revision:1"},
        {"provenance_references": (" ",)},
    ):
        with pytest.raises(ValidationError):
            _revision(**changes)


def test_material_and_failure_evidence_require_canonical_bounded_text() -> None:
    with pytest.raises(ValidationError):
        EpisodeDraftIncludedMaterialV1(
            event_id=1,
            material_reference=" material:1",
            payload_sha256="sha256:" + "1" * 64,
        )
    for values in (
        {"failure_category": " timeout"},
        {"failure_evidence_reference": " evidence:1"},
        {"sanitized_reason": "e\u0301chec"},
    ):
        with pytest.raises(ValidationError):
            EpisodeDraftExcludedFailureV1(
                event_id=6,
                attempt_count=1,
                failure_category=values.get("failure_category", "timeout"),
                sanitized_reason=values.get("sanitized_reason", "Failure."),
                failure_evidence_reference=values.get("failure_evidence_reference"),
            )


def test_revision_rejects_duplicate_material_lineage() -> None:
    materials = _revision().included_materials
    with pytest.raises(ValidationError):
        _revision(
            included_materials=(
                materials[0],
                materials[1].model_copy(
                    update={"material_reference": materials[0].material_reference}
                ),
                *materials[2:],
            )
        )
    with pytest.raises(ValidationError):
        _revision(
            included_materials=(
                materials[0],
                materials[1].model_copy(
                    update={"payload_sha256": materials[0].payload_sha256}
                ),
                *materials[2:],
            )
        )


def test_revision_artifact_is_immutable_and_tampering_fails(tmp_path: Path) -> None:
    repository = EpisodeDraftRevisionRepositoryV1()
    path = tmp_path / "revision.json"
    reference = repository.publish(revision=_revision(), destination=path)
    original = path.read_bytes()

    with pytest.raises(EpisodeDraftPersistenceError):
        repository.publish(revision=_revision(), destination=path)
    path.write_bytes(original.replace(b"Comentariu 1", b"Comentariu X"))
    with pytest.raises(EpisodeDraftPersistenceError):
        repository.load(path=path, artifact_sha256=reference.artifact_sha256)
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(EpisodeDraftPersistenceError):
        repository.load(path=path, artifact_sha256=reference.artifact_sha256)


def test_revision_publication_rejects_relative_destination() -> None:
    with pytest.raises(EpisodeDraftPersistenceError):
        EpisodeDraftRevisionRepositoryV1().publish(
            revision=_revision(), destination=Path("relative-revision.json")
        )


def _active_project(tmp_path: Path):
    database = tmp_path / "scout.db"
    project_path = tmp_path / "active-project-v1.json"
    _database(database)
    for event_id in range(8, 13):
        _additional_event(database, event_id, f"Material {event_id}")
    store = ActiveProjectStoreV1(database_path=database, project_path=project_path)
    project, _ = store.handoff_many(event_ids=(7, 8, 9, 10, 11, 12))
    materials = tuple(
        EditorMaterialV1(
            f"editor-material-v1:event:{event_id}",
            event_id,
            f"Material {event_id}",
            f"Rezumat {event_id}",
            str(tmp_path / f"editor-{event_id}.json"),
            "sha256:" + f"{event_id:064x}",
        )
        for event_id in (7, 8, 9, 10, 11)
    )
    worklist = tuple(
        EditorWorkItemV1(
            event_id,
            (
                EditorWorkItemStatusV1.FAILED
                if event_id == 12
                else EditorWorkItemStatusV1.COMPLETED
            ),
        )
        for event_id in (7, 8, 9, 10, 11, 12)
    )
    project = replace(project, editor_materials=materials, editor_worklist=worklist)
    store._write(project)
    return store, project


def _active_revision(project) -> EpisodeDraftRevisionV1:
    included = (7, 8, 9, 10, 11)
    return _revision(
        project_id=project.project_id,
        episode_id="episode:active",
        requested_event_ids=(*included, 12),
        included_event_ids=included,
        excluded_failed_event_ids=(12,),
        included_materials=tuple(
            EpisodeDraftIncludedMaterialV1(
                event_id=item.event_id,
                material_reference=item.reference,
                payload_sha256=item.payload_sha256,
            )
            for item in project.editor_materials
        ),
        excluded_failures=(
            EpisodeDraftExcludedFailureV1(
                event_id=12,
                attempt_count=3,
                failure_category="validation",
                sanitized_reason="Model output failed validation.",
            ),
        ),
        episode_draft=_draft(included, episode_id="episode:active"),
    )


def test_active_project_installs_and_restores_ready_reference(tmp_path: Path) -> None:
    store, project = _active_project(tmp_path)
    path = tmp_path / "drafts" / "revision.json"
    reference = EpisodeDraftRevisionRepositoryV1().publish(
        revision=_active_revision(project), destination=path
    )

    installed = store.install_episode_draft_revision(reference=reference)
    restored = ActiveProjectStoreV1(
        database_path=store.database_path, project_path=store.project_path
    ).load()

    assert installed.current_episode_draft_revision == reference
    assert restored.current_episode_draft_revision == reference
    assert restored.editor_materials == project.editor_materials
    assert restored.editor_worklist == project.editor_worklist
    assert store.load_episode_draft_revision().revision_id == reference.revision_id


def test_legacy_project_without_revision_loads_unchanged(tmp_path: Path) -> None:
    store, project = _active_project(tmp_path)
    payload = json.loads(store.project_path.read_text(encoding="utf-8"))
    payload.pop("current_episode_draft_revision")
    store.project_path.write_text(json.dumps(payload), encoding="utf-8")

    restored = store.load()

    assert restored.current_episode_draft_revision is None
    assert restored.editor_materials == project.editor_materials


def test_install_rejects_stale_lineage_and_keeps_orphan_unreferenced(
    tmp_path: Path,
) -> None:
    store, project = _active_project(tmp_path)
    path = tmp_path / "drafts" / "orphan.json"
    reference = EpisodeDraftRevisionRepositoryV1().publish(
        revision=_active_revision(project), destination=path
    )
    changed = replace(
        project,
        editor_materials=(
            replace(project.editor_materials[0], payload_sha256="sha256:" + "f" * 64),
            *project.editor_materials[1:],
        ),
    )
    store._write(changed)

    with pytest.raises(ValueError):
        store.install_episode_draft_revision(reference=reference)

    assert path.exists()
    assert store.load().current_episode_draft_revision is None


def test_install_rejects_duplicate_active_material_identity(tmp_path: Path) -> None:
    store, project = _active_project(tmp_path)
    reference = EpisodeDraftRevisionRepositoryV1().publish(
        revision=_active_revision(project), destination=tmp_path / "revision.json"
    )
    store._write(
        replace(
            project,
            editor_materials=(*project.editor_materials, project.editor_materials[0]),
        )
    )

    with pytest.raises(ValueError):
        store.install_episode_draft_revision(reference=reference)
    assert store.load().current_episode_draft_revision is None


def test_missing_or_corrupt_referenced_artifact_is_not_silently_cleared(
    tmp_path: Path,
) -> None:
    store, project = _active_project(tmp_path)
    path = tmp_path / "drafts" / "revision.json"
    reference = EpisodeDraftRevisionRepositoryV1().publish(
        revision=_active_revision(project), destination=path
    )
    store.install_episode_draft_revision(reference=reference)
    path.unlink()

    with pytest.raises(EpisodeDraftPersistenceError):
        store.load_episode_draft_revision()
    assert store.load().current_episode_draft_revision == reference


def test_tampered_current_reference_lineage_is_rejected_without_clearing(
    tmp_path: Path,
) -> None:
    store, project = _active_project(tmp_path)
    path = tmp_path / "drafts" / "revision.json"
    reference = EpisodeDraftRevisionRepositoryV1().publish(
        revision=_active_revision(project), destination=path
    )
    store.install_episode_draft_revision(reference=reference)
    payload = json.loads(store.project_path.read_text(encoding="utf-8"))
    payload["current_episode_draft_revision"]["included_event_ids"] = [
        7,
        8,
        9,
        10,
        99,
    ]
    store.project_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(EpisodeDraftPersistenceError):
        store.load_episode_draft_revision()
    assert store.load().current_episode_draft_revision.included_event_ids[-1] == 99


def test_child_install_requires_current_parent_and_stable_project_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, project = _active_project(tmp_path)
    repository = EpisodeDraftRevisionRepositoryV1()
    first = repository.publish(
        revision=_active_revision(project), destination=tmp_path / "first.json"
    )
    store.install_episode_draft_revision(reference=first)
    unrelated = repository.publish(
        revision=_active_revision(project).model_copy(
            update={"revision_id": "revision:unrelated", "parent_revision_id": None}
        ),
        destination=tmp_path / "unrelated.json",
    )
    with pytest.raises(ValueError):
        store.install_episode_draft_revision(reference=unrelated)

    child_revision = _active_revision(project).model_copy(
        update={"revision_id": "revision:2", "parent_revision_id": first.revision_id}
    )
    child = repository.publish(
        revision=child_revision, destination=tmp_path / "child.json"
    )
    original_required = store._required
    calls = 0

    def changed_during_install():
        nonlocal calls
        calls += 1
        value = original_required()
        return value if calls == 1 else replace(value, title="Concurrent change")

    monkeypatch.setattr(store, "_required", changed_during_install)
    with pytest.raises(ValueError):
        store.install_episode_draft_revision(reference=child)
    assert original_required().current_episode_draft_revision == first
