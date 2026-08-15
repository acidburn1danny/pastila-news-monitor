from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

from test_desktop_episode_draft_v1 import _install_fixture_execution, _prepared

from pastila_scout.desktop_v1.episode_draft import _publish_episode_draft_v1
from pastila_scout.desktop_v1.episode_draft_export import (
    _episode_draft_default_filename_v1,
    _export_current_episode_draft_v1,
)
from pastila_scout.desktop_v1.views import _DesktopMainWindowV1


class _Writer:
    def publish(self, *, payload, destination):
        destination.path.write_bytes(payload)
        return destination.path


def _published(tmp_path: Path, monkeypatch):
    store, prepared = _prepared(tmp_path)
    _install_fixture_execution(monkeypatch, prepared)
    result = _publish_episode_draft_v1(
        store=store, revision_root=(tmp_path / "revisions").resolve()
    )
    assert result.current
    return store


def test_export_resolves_active_revision_and_preserves_content_order(
    tmp_path: Path, monkeypatch
) -> None:
    store = _published(tmp_path, monkeypatch)
    before = store.load_runtime_state()
    revision = store.load_episode_draft_revision()
    destination = (tmp_path / "draft.md").resolve()

    result = _export_current_episode_draft_v1(
        store=store, destination=destination, exporter=_Writer()
    )

    assert result.succeeded is True
    content = destination.read_text(encoding="utf-8")
    assert f"- Revizie: {revision.revision_id}" in content
    assert f"- Revizie parinte: {revision.parent_revision_id or '-'}" in content
    positions = [content.index(story.text) for story in revision.episode_draft.stories]
    assert positions == sorted(positions)
    assert revision.episode_draft.assembled_text in content
    assert "Ollama timeout." in content
    assert revision.included_materials[0].material_reference not in content
    assert revision.model_dump(mode="python")["payload_sha256"] not in content
    assert store.load_runtime_state() == before
    assert store.load_episode_draft_revision() == revision


def test_repeated_export_is_byte_identical_after_restart(
    tmp_path: Path, monkeypatch
) -> None:
    store = _published(tmp_path, monkeypatch)
    first = (tmp_path / "first.md").resolve()
    second = (tmp_path / "second.md").resolve()

    one = _export_current_episode_draft_v1(
        store=store, destination=first, exporter=_Writer()
    )
    restarted = type(store)(
        database_path=store.database_path, project_path=store.project_path
    )
    two = _export_current_episode_draft_v1(
        store=restarted, destination=second, exporter=_Writer()
    )

    assert one.succeeded and two.succeeded
    assert first.read_bytes() == second.read_bytes()


def test_default_filename_is_stable_and_windows_safe() -> None:
    first = _episode_draft_default_filename_v1("revision:alpha/one")
    assert first == _episode_draft_default_filename_v1("revision:alpha/one")
    assert first.endswith(".md")
    assert not any(character in first for character in '<>:"/\\|?*')


def test_no_revision_or_invalid_repository_writes_nothing(tmp_path: Path) -> None:
    destination = (tmp_path / "draft.md").resolve()
    no_revision = SimpleNamespace(load_runtime_state=lambda: None)
    result = _export_current_episode_draft_v1(
        store=no_revision, destination=destination, exporter=_Writer()
    )
    assert not result.succeeded
    assert not destination.exists()

    invalid = SimpleNamespace(
        load_runtime_state=lambda: SimpleNamespace(
            current_episode_draft_revision=object()
        ),
        load_episode_draft_revision=lambda: (_ for _ in ()).throw(ValueError()),
    )
    result = _export_current_episode_draft_v1(
        store=invalid, destination=destination, exporter=_Writer()
    )
    assert not result.succeeded
    assert not destination.exists()


def test_existing_target_is_never_silently_replaced(
    tmp_path: Path, monkeypatch
) -> None:
    store = _published(tmp_path, monkeypatch)
    destination = (tmp_path / "draft.md").resolve()
    destination.write_text("original", encoding="utf-8")
    result = _export_current_episode_draft_v1(
        store=store, destination=destination, exporter=_Writer()
    )
    assert not result.succeeded
    assert destination.read_text(encoding="utf-8") == "original"


def test_write_and_readback_failures_are_truthful(tmp_path: Path, monkeypatch) -> None:
    store = _published(tmp_path, monkeypatch)
    destination = (tmp_path / "draft.md").resolve()

    class BrokenWriter:
        def publish(self, **_kwargs):
            raise OSError

    failed = _export_current_episode_draft_v1(
        store=store, destination=destination, exporter=BrokenWriter()
    )
    assert not failed.succeeded
    assert not destination.exists()

    failed = _export_current_episode_draft_v1(
        store=store,
        destination=destination,
        exporter=_Writer(),
        read_bytes=lambda _path: b"corrupt\n",
    )
    assert not failed.succeeded
    assert "verificat" in failed.status


def test_stale_revision_remains_exact_export_authority(
    tmp_path: Path, monkeypatch
) -> None:
    store = _published(tmp_path, monkeypatch)
    revision = store.load_episode_draft_revision()
    project = store.load_runtime_state()
    store.save_chief_editor(
        title="Structura schimbata", items=project.chief_editor_items
    )
    destination = (tmp_path / "stale.md").resolve()
    result = _export_current_episode_draft_v1(
        store=store, destination=destination, exporter=_Writer()
    )
    assert result.succeeded
    assert revision.revision_id in destination.read_text(encoding="utf-8")


def test_real_atomic_writer_exports_complete_payload(
    tmp_path: Path, monkeypatch
) -> None:
    store = _published(tmp_path, monkeypatch)
    destination = (tmp_path / "atomic.md").resolve()
    result = _export_current_episode_draft_v1(store=store, destination=destination)
    assert result.succeeded
    assert destination.read_bytes().endswith(b"\n")
    assert not tuple(tmp_path.glob(".pastila-editor-*.tmp"))


def test_inspection_has_one_guarded_export_action() -> None:
    source = inspect.getsource(_DesktopMainWindowV1._episode_draft_inspect)
    action = inspect.getsource(_DesktopMainWindowV1._episode_draft_export_action)
    assert source.count('key="episode_draft.export"') == 1
    assert '"episode_draft_export" in self._bindings' in source
    assert "if self._episode_draft_export_running" in action


def test_save_dialog_cancellation_is_explicit_and_has_no_provider_path() -> None:
    from pastila_scout.desktop_v1 import entrypoint, episode_draft_export

    source = inspect.getsource(entrypoint.main)
    assert "if not selected:" in source
    assert 'status="Export anulat."' in source
    assert "confirmoverwrite=False" in source
    export_source = inspect.getsource(episode_draft_export)
    assert "openai" not in export_source.lower()
    assert "ollama" not in export_source.lower()
