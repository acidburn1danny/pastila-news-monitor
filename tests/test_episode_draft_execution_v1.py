from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_episode_draft_assembly_v1 import Loader, _ready

from pastila_scout.active_project_v1 import (
    ActiveProjectStoreV1,
    ChiefEditorItemV1,
)
from pastila_scout.episode_draft_assembly_v1 import EpisodeDraftAssemblyPreparerV1
from pastila_scout.episode_draft_execution_v1 import (
    EpisodeDraftActivationStatusV1,
    EpisodeDraftExecutionErrorCodeV1,
    EpisodeDraftExecutionErrorV1,
    EpisodeDraftExecutorV1,
    EpisodeDraftPublicationStatusV1,
)
from pastila_scout.episode_draft_v1 import (
    EpisodeDraftPersistenceError,
    EpisodeDraftRevisionRepositoryV1,
)

NOW = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)


def _fixture(tmp_path: Path):
    store, project = _ready(tmp_path)
    loader = Loader()
    preparer = EpisodeDraftAssemblyPreparerV1(store=store, artifact_loader=loader)
    prepared = preparer.prepare()
    executor = EpisodeDraftExecutorV1(
        store=store,
        revision_root=(tmp_path / "drafts").resolve(),
        preparer=preparer,
        clock=lambda: NOW,
    )
    return store, project, prepared, preparer, executor


def test_first_publication_installs_exact_revision_and_preserves_project(
    tmp_path: Path,
) -> None:
    store, before, prepared, _preparer, executor = _fixture(tmp_path)

    result = executor.execute(prepared=prepared)
    after = store.load_runtime_state()
    revision = store.load_episode_draft_revision()

    assert result.publication_status is EpisodeDraftPublicationStatusV1.PUBLISHED
    assert result.activation_status is EpisodeDraftActivationStatusV1.ACTIVATED
    assert after.current_episode_draft_revision == result.reference
    assert revision.requested_event_ids == prepared.requested_event_ids
    assert revision.included_event_ids == prepared.included_event_ids
    assert revision.episode_draft.stories == prepared.stories
    assert tuple(item.text for item in revision.episode_draft.transitions) == (
        "",
        "",
        "",
        "",
    )
    assert revision.episode_draft.opening == revision.episode_draft.closing == ""
    assert revision.excluded_failures == prepared.excluded_failures
    assert revision.payload_sha256.startswith("sha256:")
    assert replace(after, current_episode_draft_revision=None) == before


def test_restart_resolves_exact_reference_and_artifact(tmp_path: Path) -> None:
    store, _before, prepared, _preparer, executor = _fixture(tmp_path)
    result = executor.execute(prepared=prepared)
    restarted = ActiveProjectStoreV1(
        database_path=store.database_path, project_path=store.project_path
    )

    assert restarted.load().current_episode_draft_revision == result.reference
    assert restarted.load_episode_draft_revision().revision_id == (
        result.reference.revision_id
    )


def test_exact_retry_is_already_published_and_current(tmp_path: Path) -> None:
    _store, _before, prepared, _preparer, executor = _fixture(tmp_path)
    first = executor.execute(prepared=prepared)
    second = executor.execute(prepared=prepared)

    assert second.reference == first.reference
    assert (
        second.publication_status is EpisodeDraftPublicationStatusV1.ALREADY_PUBLISHED
    )
    assert second.activation_status is EpisodeDraftActivationStatusV1.ALREADY_CURRENT
    assert len(tuple((tmp_path / "drafts").glob("*.json"))) == 1


def test_already_current_retry_rejects_changed_material_state(tmp_path: Path) -> None:
    store, _before, prepared, _preparer, executor = _fixture(tmp_path)
    executor.execute(prepared=prepared)
    project = store.load_runtime_state()
    store._write(
        replace(
            project,
            editor_materials=(
                replace(
                    project.editor_materials[0],
                    payload_sha256="sha256:" + "e" * 64,
                ),
                *project.editor_materials[1:],
            ),
        )
    )

    with pytest.raises(EpisodeDraftExecutionErrorV1) as captured:
        executor.execute(prepared=prepared)
    assert captured.value.code is EpisodeDraftExecutionErrorCodeV1.STALE_INPUT


@pytest.mark.parametrize("mutation", ("project", "material", "chief"))
def test_stale_prepared_input_fails_before_publication(
    tmp_path: Path, mutation: str
) -> None:
    store, project, prepared, _preparer, executor = _fixture(tmp_path)
    if mutation == "project":
        changed = replace(project, project_id="different-project")
    elif mutation == "material":
        changed = replace(
            project,
            editor_materials=(
                replace(
                    project.editor_materials[0],
                    payload_sha256="sha256:" + "f" * 64,
                ),
                *project.editor_materials[1:],
            ),
        )
    else:
        changed = replace(
            project,
            chief_editor_items=(
                ChiefEditorItemV1(project.editor_materials[0].reference),
            ),
        )
    store._write(changed)

    with pytest.raises(EpisodeDraftExecutionErrorV1) as captured:
        executor.execute(prepared=prepared)

    assert captured.value.code is EpisodeDraftExecutionErrorCodeV1.STALE_INPUT
    assert not (tmp_path / "drafts").exists()


def test_invalid_request_and_relative_repository_root_fail_closed(
    tmp_path: Path,
) -> None:
    store, _before, prepared, preparer, _executor = _fixture(tmp_path)
    executor = EpisodeDraftExecutorV1(
        store=store, revision_root=Path("relative"), preparer=preparer
    )
    with pytest.raises(EpisodeDraftExecutionErrorV1) as captured:
        executor.execute(prepared=prepared)
    assert captured.value.code is EpisodeDraftExecutionErrorCodeV1.INVALID_REQUEST


class _FailingRepository:
    def publish(self, **_kwargs):
        raise EpisodeDraftPersistenceError("injected publication failure")


def test_repository_failure_leaves_both_surfaces_unchanged(tmp_path: Path) -> None:
    store, before, prepared, preparer, _executor = _fixture(tmp_path)
    executor = EpisodeDraftExecutorV1(
        store=store,
        revision_root=(tmp_path / "drafts").resolve(),
        preparer=preparer,
        repository=_FailingRepository(),
    )
    with pytest.raises(EpisodeDraftExecutionErrorV1) as captured:
        executor.execute(prepared=prepared)
    assert captured.value.code is EpisodeDraftExecutionErrorCodeV1.PUBLICATION_FAILED
    assert store.load_runtime_state() == before


class _StoreFailure:
    def __init__(self, store, *, write_then_fail: bool = False):
        self.store = store
        self.write_then_fail = write_then_fail
        self.failed = False

    def __getattr__(self, name):
        return getattr(self.store, name)

    def install_episode_draft_revision(self, *, reference):
        if self.write_then_fail:
            self.store.install_episode_draft_revision(reference=reference)
        self.failed = True
        raise OSError("injected active-project write failure")


@pytest.mark.parametrize("write_then_fail", (False, True))
def test_activation_failure_is_truthful_and_retry_converges(
    tmp_path: Path, write_then_fail: bool
) -> None:
    store, before, prepared, preparer, _executor = _fixture(tmp_path)
    failing_store = _StoreFailure(store, write_then_fail=write_then_fail)
    first = EpisodeDraftExecutorV1(
        store=failing_store,
        revision_root=(tmp_path / "drafts").resolve(),
        preparer=preparer,
        clock=lambda: NOW,
    ).execute(prepared=prepared)

    assert first.publication_status is EpisodeDraftPublicationStatusV1.PUBLISHED
    assert first.activation_status is EpisodeDraftActivationStatusV1.FAILED
    assert Path(first.reference.artifact_path).is_file()
    if not write_then_fail:
        assert store.load_runtime_state() == before

    retry = EpisodeDraftExecutorV1(
        store=store,
        revision_root=(tmp_path / "drafts").resolve(),
        preparer=preparer,
    ).execute(prepared=prepared)
    assert retry.reference == first.reference
    assert retry.publication_status is EpisodeDraftPublicationStatusV1.ALREADY_PUBLISHED
    assert retry.activation_status in (
        EpisodeDraftActivationStatusV1.ACTIVATED,
        EpisodeDraftActivationStatusV1.ALREADY_CURRENT,
    )


def test_existing_path_collision_is_not_overwritten(tmp_path: Path) -> None:
    _store, _before, prepared, _preparer, executor = _fixture(tmp_path)
    revision_id = (
        "episode-draft-revision-v1:"
        + __import__("hashlib")
        .sha256(
            (
                "episode-draft-execution-v1\n" + prepared.preparation_fingerprint + "\n"
            ).encode()
        )
        .hexdigest()
    )
    path = tmp_path / "drafts" / f"{revision_id.split(':')[-1]}.json"
    path.parent.mkdir()
    path.write_text("not a revision", encoding="utf-8")

    with pytest.raises(EpisodeDraftExecutionErrorV1) as captured:
        executor.execute(prepared=prepared)
    assert captured.value.code is EpisodeDraftExecutionErrorCodeV1.PUBLICATION_COLLISION
    assert path.read_text(encoding="utf-8") == "not a revision"


def test_child_revision_has_valid_parent_and_distinct_identity(tmp_path: Path) -> None:
    store, _before, prepared, _preparer, executor = _fixture(tmp_path)
    first = executor.execute(prepared=prepared)
    child_preparer = EpisodeDraftAssemblyPreparerV1(
        store=store, artifact_loader=Loader()
    )
    child_input = child_preparer.prepare()
    child = EpisodeDraftExecutorV1(
        store=store,
        revision_root=(tmp_path / "drafts").resolve(),
        preparer=child_preparer,
        clock=lambda: NOW.replace(minute=1),
    ).execute(prepared=child_input)

    assert child.reference.parent_revision_id == first.reference.revision_id
    assert child.reference.draft_id == first.reference.draft_id
    assert child.reference.revision_id != first.reference.revision_id
    assert len(tuple((tmp_path / "drafts").glob("*.json"))) == 2


def test_minimum_story_rule_cannot_be_bypassed_at_model_boundary(
    tmp_path: Path,
) -> None:
    _store, _before, prepared, _preparer, _executor = _fixture(tmp_path)
    values = prepared.model_dump(mode="python")
    values["included_event_ids"] = prepared.included_event_ids[:4]
    values["stories"] = prepared.stories[:4]
    values["included_materials"] = prepared.included_materials[:4]
    with pytest.raises(ValueError):
        type(prepared).model_validate(values)


def test_repository_readback_checksum_matches_reference(tmp_path: Path) -> None:
    _store, _before, prepared, _preparer, executor = _fixture(tmp_path)
    result = executor.execute(prepared=prepared)
    loaded = EpisodeDraftRevisionRepositoryV1().load(
        path=Path(result.reference.artifact_path),
        artifact_sha256=result.reference.artifact_sha256,
    )
    assert loaded.payload_sha256.startswith("sha256:")
    assert loaded.revision_id == result.reference.revision_id
