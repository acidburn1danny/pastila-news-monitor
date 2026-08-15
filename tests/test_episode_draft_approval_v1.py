from __future__ import annotations

import inspect
import json
from dataclasses import replace
from pathlib import Path

import pytest
from test_desktop_episode_draft_export_v1 import _Writer
from test_desktop_episode_draft_v1 import _install_fixture_execution, _prepared

from pastila_scout.active_project_v1 import (
    ActiveProjectStoreV1,
    EpisodeDraftApprovalPersistenceError,
    EpisodeDraftApprovalStatusV1,
)
from pastila_scout.desktop_v1.episode_draft import (
    _handoff_episode_draft_for_approval_v1,
    _publish_episode_draft_v1,
    _recover_episode_draft_v1,
)
from pastila_scout.desktop_v1.episode_draft_export import (
    _export_current_episode_draft_v1,
)
from pastila_scout.desktop_v1.views import _DesktopMainWindowV1


def _published(tmp_path: Path, monkeypatch):
    store, prepared = _prepared(tmp_path)
    _install_fixture_execution(monkeypatch, prepared)
    result = _publish_episode_draft_v1(
        store=store, revision_root=(tmp_path / "revisions").resolve()
    )
    assert result.current
    return store


def test_first_handoff_binds_exact_revision_and_is_idempotent_after_restart(
    tmp_path: Path, monkeypatch
) -> None:
    store = _published(tmp_path, monkeypatch)
    before = store.load_runtime_state()
    reference = before.current_episode_draft_revision
    artifact_before = Path(reference.artifact_path).read_bytes()

    first = _handoff_episode_draft_for_approval_v1(store=store)
    after = store.load_runtime_state()
    second = _handoff_episode_draft_for_approval_v1(store=store)
    restarted = ActiveProjectStoreV1(
        database_path=store.database_path, project_path=store.project_path
    )
    recovered = _recover_episode_draft_v1(store=restarted)

    assert first.approval_pending and first.status == "Pentru aprobare."
    assert second.approval_pending
    assert recovered.approval_pending
    assert after.episode_draft_approval.project_id == before.project_id
    assert after.episode_draft_approval.revision_id == reference.revision_id
    assert after.episode_draft_approval.artifact_sha256 == reference.artifact_sha256
    assert (
        after.episode_draft_approval.status
        is EpisodeDraftApprovalStatusV1.PENDING_APPROVAL
    )
    assert Path(reference.artifact_path).read_bytes() == artifact_before
    assert replace(after, episode_draft_approval=None) == before


def test_stale_revision_cannot_be_handed_off(tmp_path: Path, monkeypatch) -> None:
    store = _published(tmp_path, monkeypatch)
    project = store.load_runtime_state()
    store.save_chief_editor(
        title="Structura schimbata", items=project.chief_editor_items
    )

    result = _handoff_episode_draft_for_approval_v1(store=store)

    assert result.stale
    assert not result.can_submit_approval
    assert store.load_runtime_state().episode_draft_approval is None


def test_old_approval_does_not_apply_to_new_child_revision(
    tmp_path: Path, monkeypatch
) -> None:
    store = _published(tmp_path, monkeypatch)
    _handoff_episode_draft_for_approval_v1(store=store)
    old = store.load_runtime_state().current_episode_draft_revision
    project = store.load_runtime_state()
    store.save_chief_editor(title="Structura noua", items=project.chief_editor_items)
    created = _publish_episode_draft_v1(
        store=store, revision_root=(tmp_path / "revisions").resolve()
    )

    recovered = _recover_episode_draft_v1(store=store)
    assert created.revision_id != old.revision_id
    assert not recovered.approval_pending
    assert recovered.can_submit_approval
    assert "altei revizii" in recovered.status

    sent = _handoff_episode_draft_for_approval_v1(store=store)
    assert sent.approval_pending
    assert (
        store.load_runtime_state().episode_draft_approval.revision_id
        == created.revision_id
    )


def test_export_bytes_are_unchanged_by_approval_handoff(
    tmp_path: Path, monkeypatch
) -> None:
    store = _published(tmp_path, monkeypatch)
    before = (tmp_path / "before.md").resolve()
    after = (tmp_path / "after.md").resolve()
    assert _export_current_episode_draft_v1(
        store=store, destination=before, exporter=_Writer()
    ).succeeded
    _handoff_episode_draft_for_approval_v1(store=store)
    assert _export_current_episode_draft_v1(
        store=store, destination=after, exporter=_Writer()
    ).succeeded
    assert before.read_bytes() == after.read_bytes()


def test_no_revision_and_invalid_reference_fail_closed(
    tmp_path: Path, monkeypatch
) -> None:
    store, _prepared_value = _prepared(tmp_path)
    missing = _handoff_episode_draft_for_approval_v1(store=store)
    assert not missing.approval_pending

    invalid_root = tmp_path / "invalid"
    invalid_root.mkdir()
    store = _published(invalid_root, monkeypatch)
    payload = json.loads(store.project_path.read_text(encoding="utf-8"))
    payload["current_episode_draft_revision"]["artifact_sha256"] = "sha256:" + "0" * 64
    store.project_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    invalid = _handoff_episode_draft_for_approval_v1(store=store)
    assert not invalid.approval_pending
    assert "recuperat" in invalid.status


def test_write_failure_preserves_prior_state(tmp_path: Path, monkeypatch) -> None:
    store = _published(tmp_path, monkeypatch)
    before = store.load_runtime_state()

    def fail_write(self, project):
        del self, project
        raise OSError

    monkeypatch.setattr(ActiveProjectStoreV1, "_write", fail_write)
    result = _handoff_episode_draft_for_approval_v1(store=store)
    assert not result.approval_pending
    assert "scrisa" in result.status
    assert store.load_runtime_state() == before


def test_optimistic_boundary_rejects_concurrent_project_change(
    tmp_path: Path, monkeypatch
) -> None:
    store = _published(tmp_path, monkeypatch)
    expected = store.load_runtime_state()
    store.save_chief_editor(
        title="Schimbare concurenta", items=expected.chief_editor_items
    )
    with pytest.raises(ValueError, match="schimbat"):
        store.mark_episode_draft_pending_approval(expected_project=expected)
    assert store.load_runtime_state().episode_draft_approval is None


def test_readback_failure_rolls_back_prior_state(tmp_path: Path, monkeypatch) -> None:
    store = _published(tmp_path, monkeypatch)
    before = store.load_runtime_state()
    original = ActiveProjectStoreV1._required
    calls = 0

    def unreliable(self):
        nonlocal calls
        calls += 1
        value = original(self)
        if calls == 4:
            return replace(value, title="citire corupta")
        return value

    monkeypatch.setattr(ActiveProjectStoreV1, "_required", unreliable)
    try:
        store.mark_episode_draft_pending_approval(expected_project=before)
    except EpisodeDraftApprovalPersistenceError as exc:
        assert exc.code == "verification_failed"
    else:
        raise AssertionError("read-back failure was not reported")
    assert store.load_runtime_state() == before


def test_old_project_without_approval_metadata_remains_compatible(
    tmp_path: Path, monkeypatch
) -> None:
    store = _published(tmp_path, monkeypatch)
    payload = json.loads(store.project_path.read_text(encoding="utf-8"))
    payload.pop("episode_draft_approval")
    store.project_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    restored = store.load()
    assert restored.current_episode_draft_revision is not None
    assert restored.episode_draft_approval is None


def test_desktop_has_exactly_one_guarded_approval_action() -> None:
    inspection = inspect.getsource(_DesktopMainWindowV1._episode_draft_inspect)
    action = inspect.getsource(_DesktopMainWindowV1._episode_draft_approval_action)
    assert inspection.count('key="episode_draft.approval"') == 1
    assert "_episode_draft_can_submit_approval" in inspection
    assert '"episode_draft_approval" in self._bindings' in inspection
    assert "_editor_idle" in inspection
    assert "if self._episode_draft_approval_running" in action


def test_approval_path_has_no_provider_or_revision_editing_dependency() -> None:
    from pastila_scout.desktop_v1 import episode_draft

    source = inspect.getsource(episode_draft._handoff_episode_draft_for_approval_v1)
    assert "openai" not in source.lower()
    assert "ollama" not in source.lower()
    assert "publish_episode_draft" not in source
