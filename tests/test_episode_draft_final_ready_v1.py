from __future__ import annotations

import inspect
import json
from dataclasses import replace
from pathlib import Path

import pytest
from test_desktop_episode_draft_export_v1 import _Writer
from test_episode_draft_approval_v1 import _published

from pastila_scout.active_project_v1 import (
    ActiveProjectStoreV1,
    EpisodeDraftApprovalPersistenceError,
    EpisodeDraftApprovalStatusV1,
)
from pastila_scout.desktop_v1.episode_draft import (
    _approve_episode_draft_v1,
    _handoff_episode_draft_for_approval_v1,
    _publish_episode_draft_v1,
    _recover_episode_draft_v1,
)
from pastila_scout.desktop_v1.episode_draft_export import (
    _export_current_episode_draft_v1,
)
from pastila_scout.desktop_v1.views import _DesktopMainWindowV1


def _pending(tmp_path: Path, monkeypatch):
    tmp_path.mkdir(parents=True, exist_ok=True)
    store = _published(tmp_path, monkeypatch)
    result = _handoff_episode_draft_for_approval_v1(store=store)
    assert result.approval_pending
    return store


def test_pending_to_approved_binds_exact_revision_and_is_restart_idempotent(
    tmp_path: Path, monkeypatch
) -> None:
    store = _pending(tmp_path, monkeypatch)
    before = store.load_runtime_state()
    reference = before.current_episode_draft_revision
    artifact = Path(reference.artifact_path).read_bytes()

    first = _approve_episode_draft_v1(store=store)
    after = store.load_runtime_state()
    second = _approve_episode_draft_v1(store=store)
    handoff_retry = _handoff_episode_draft_for_approval_v1(store=store)
    restarted = ActiveProjectStoreV1(
        database_path=store.database_path, project_path=store.project_path
    )
    recovered = _recover_episode_draft_v1(store=restarted)

    assert first.approval_approved and first.status == "Aprobat."
    assert second.approval_approved
    assert handoff_retry.approval_approved
    assert recovered.approval_approved
    approval = after.episode_draft_approval
    assert approval.project_id == before.project_id
    assert approval.revision_id == reference.revision_id
    assert approval.artifact_sha256 == reference.artifact_sha256
    assert approval.status is EpisodeDraftApprovalStatusV1.APPROVED
    assert (
        replace(after, episode_draft_approval=before.episode_draft_approval) == before
    )
    assert Path(reference.artifact_path).read_bytes() == artifact


def test_missing_pending_and_stale_revision_cannot_be_approved(
    tmp_path: Path, monkeypatch
) -> None:
    store = _published(tmp_path, monkeypatch)
    missing = _approve_episode_draft_v1(store=store)
    assert not missing.approval_approved
    assert "nu este in starea" in missing.status

    store = _pending(tmp_path / "stale", monkeypatch)
    project = store.load_runtime_state()
    store.save_chief_editor(
        title="Structura schimbata", items=project.chief_editor_items
    )
    stale = _approve_episode_draft_v1(store=store)
    assert stale.stale
    assert not stale.can_approve
    assert (
        store.load_runtime_state().episode_draft_approval.status
        is EpisodeDraftApprovalStatusV1.PENDING_APPROVAL
    )


def test_approved_revision_does_not_apply_to_new_child(
    tmp_path: Path, monkeypatch
) -> None:
    store = _pending(tmp_path, monkeypatch)
    _approve_episode_draft_v1(store=store)
    old = store.load_runtime_state().current_episode_draft_revision
    project = store.load_runtime_state()
    store.save_chief_editor(title="Structura copil", items=project.chief_editor_items)
    child = _publish_episode_draft_v1(
        store=store, revision_root=(tmp_path / "revisions").resolve()
    )

    recovered = _recover_episode_draft_v1(store=store)
    assert child.revision_id != old.revision_id
    assert recovered.approval_mismatch
    assert not recovered.approval_approved
    assert not recovered.can_approve
    assert "altei revizii" in recovered.status

    pending = _handoff_episode_draft_for_approval_v1(store=store)
    approved = _approve_episode_draft_v1(store=store)
    assert pending.approval_pending
    assert approved.approval_approved
    assert (
        store.load_runtime_state().episode_draft_approval.revision_id
        == child.revision_id
    )


def test_export_is_byte_identical_before_and_after_final_approval(
    tmp_path: Path, monkeypatch
) -> None:
    store = _pending(tmp_path, monkeypatch)
    before = (tmp_path / "pending.md").resolve()
    after = (tmp_path / "approved.md").resolve()
    assert _export_current_episode_draft_v1(
        store=store, destination=before, exporter=_Writer()
    ).succeeded
    _approve_episode_draft_v1(store=store)
    assert _export_current_episode_draft_v1(
        store=store, destination=after, exporter=_Writer()
    ).succeeded
    assert before.read_bytes() == after.read_bytes()


def test_write_failure_leaves_pending_state_intact(tmp_path: Path, monkeypatch) -> None:
    store = _pending(tmp_path, monkeypatch)
    before = store.load_runtime_state()

    def fail_write(self, project):
        del self, project
        raise OSError

    monkeypatch.setattr(ActiveProjectStoreV1, "_write", fail_write)
    result = _approve_episode_draft_v1(store=store)
    assert not result.approval_approved
    assert "scrisa" in result.status
    assert store.load_runtime_state() == before


def test_readback_failure_rolls_back_to_pending(tmp_path: Path, monkeypatch) -> None:
    store = _pending(tmp_path, monkeypatch)
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
    with pytest.raises(EpisodeDraftApprovalPersistenceError) as captured:
        store.approve_episode_draft(expected_project=before)
    assert captured.value.code == "verification_failed"
    assert store.load_runtime_state() == before


def test_invalid_reference_and_old_revision_binding_fail_closed(
    tmp_path: Path, monkeypatch
) -> None:
    store = _pending(tmp_path, monkeypatch)
    payload = json.loads(store.project_path.read_text(encoding="utf-8"))
    payload["current_episode_draft_revision"]["artifact_sha256"] = "sha256:" + "0" * 64
    store.project_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    invalid = _approve_episode_draft_v1(store=store)
    assert not invalid.approval_approved

    old_root = tmp_path / "old"
    old_root.mkdir()
    old = _pending(old_root, monkeypatch)
    project = old.load_runtime_state()
    old.save_chief_editor(title="Copil", items=project.chief_editor_items)
    _publish_episode_draft_v1(
        store=old, revision_root=(old_root / "revisions").resolve()
    )
    mismatch = _approve_episode_draft_v1(store=old)
    assert mismatch.approval_mismatch
    assert "altei revizii" in mismatch.status


def test_approved_state_loads_and_absent_metadata_remains_compatible(
    tmp_path: Path, monkeypatch
) -> None:
    store = _pending(tmp_path, monkeypatch)
    _approve_episode_draft_v1(store=store)
    assert (
        store.load().episode_draft_approval.status
        is EpisodeDraftApprovalStatusV1.APPROVED
    )

    payload = json.loads(store.project_path.read_text(encoding="utf-8"))
    payload.pop("episode_draft_approval")
    store.project_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    assert store.load().episode_draft_approval is None


def test_desktop_has_one_guarded_final_approval_action() -> None:
    inspection = inspect.getsource(_DesktopMainWindowV1._episode_draft_inspect)
    action = inspect.getsource(_DesktopMainWindowV1._episode_draft_final_action)
    assert inspection.count('key="episode_draft.final_approve"') == 1
    assert "_episode_draft_can_approve" in inspection
    assert '"episode_draft_final" in self._bindings' in inspection
    assert "_editor_idle" in inspection
    assert "if self._episode_draft_final_running" in action


def test_final_approval_has_no_provider_reviewer_or_editing_path() -> None:
    from pastila_scout.desktop_v1 import episode_draft

    source = inspect.getsource(episode_draft._approve_episode_draft_v1).lower()
    assert "openai" not in source
    assert "ollama" not in source
    assert "reviewer" not in source
    assert "comment" not in source
    assert "publish_episode_draft" not in source
