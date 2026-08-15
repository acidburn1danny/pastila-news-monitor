from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_episode_draft_assembly_v1 import Loader, _ready

from pastila_scout.desktop_v1 import entrypoint
from pastila_scout.desktop_v1 import episode_draft as desktop_episode
from pastila_scout.desktop_v1.episode_draft import (
    _publish_episode_draft_v1,
    _recover_episode_draft_v1,
)
from pastila_scout.desktop_v1.views import _DesktopMainWindowV1
from pastila_scout.episode_draft_assembly_v1 import (
    EpisodeDraftAssemblyErrorCodeV1,
    EpisodeDraftAssemblyErrorV1,
    EpisodeDraftAssemblyPreparerV1,
    _fingerprint,
)
from pastila_scout.episode_draft_execution_v1 import (
    EpisodeDraftActivationStatusV1,
    EpisodeDraftExecutionErrorCodeV1,
    EpisodeDraftExecutionErrorV1,
    EpisodeDraftExecutionStageV1,
    EpisodeDraftExecutorV1,
)


def _prepared(tmp_path: Path):
    store, _project = _ready(tmp_path)
    prepared = EpisodeDraftAssemblyPreparerV1(
        store=store, artifact_loader=Loader()
    ).prepare()
    return store, prepared


class _Prepared:
    value = None

    def __init__(self, *, store):
        self.store = store

    def prepare(self):
        project = self.store.load_runtime_state()
        current = project.current_episode_draft_revision
        values = self.value.model_dump(mode="python")
        values["parent_revision_id"] = None if current is None else current.revision_id
        values["chief_editor_fingerprint"] = _fingerprint(
            {
                "title": project.chief_editor_title,
                "updated_at": project.chief_editor_updated_at,
                "items": project.chief_editor_items,
            }
        )
        values["preparation_fingerprint"] = _fingerprint(
            {
                name: value
                for name, value in values.items()
                if name != "preparation_fingerprint"
            }
        )
        return type(self.value).model_validate(values)


class _FixtureExecutor:
    def __init__(self, *, store, revision_root):
        self.executor = EpisodeDraftExecutorV1(
            store=store,
            revision_root=revision_root,
            preparer=_Prepared(store=store),
        )

    def execute(self, *, prepared):
        return self.executor.execute(prepared=prepared)


def _install_fixture_execution(monkeypatch, prepared) -> None:
    _Prepared.value = prepared
    monkeypatch.setattr(desktop_episode, "EpisodeDraftAssemblyPreparerV1", _Prepared)
    monkeypatch.setattr(desktop_episode, "EpisodeDraftExecutorV1", _FixtureExecutor)


def test_desktop_publication_projects_counts_order_and_restart(
    tmp_path: Path, monkeypatch
) -> None:
    store, prepared = _prepared(tmp_path)
    _install_fixture_execution(monkeypatch, prepared)

    before = store.load_runtime_state()
    published = _publish_episode_draft_v1(
        store=store, revision_root=(tmp_path / "drafts").resolve()
    )
    recovered = _recover_episode_draft_v1(store=store)

    assert published.current is recovered.current is True
    assert "5 stiri incluse, 1 excluse" in published.status
    assert tuple(item[0] for item in published.included) == (7, 8, 9, 10, 11)
    assert tuple(item[1] for item in published.included) == tuple(
        f"Material {value}" for value in (7, 8, 9, 10, 11)
    )
    assert published.excluded == ((12, "Material 12", "Ollama timeout."),)
    assert recovered.revision_id == published.revision_id
    assert recovered.included == published.included
    assert len(tuple((tmp_path / "drafts").glob("*.json"))) == 1
    after = store.load_runtime_state()
    assert after.scout_input == before.scout_input
    assert after.editor_worklist == before.editor_worklist
    assert after.editor_materials == before.editor_materials
    assert after.chief_editor_items == before.chief_editor_items


def test_already_current_publication_is_informational(
    tmp_path: Path, monkeypatch
) -> None:
    store, prepared = _prepared(tmp_path)
    _install_fixture_execution(monkeypatch, prepared)
    first = _publish_episode_draft_v1(
        store=store, revision_root=(tmp_path / "drafts").resolve()
    )
    second = _publish_episode_draft_v1(
        store=store, revision_root=(tmp_path / "drafts").resolve()
    )

    assert second.current is True
    assert "deja curent" in second.status
    assert second.revision_id == first.revision_id
    assert len(tuple((tmp_path / "drafts").glob("*.json"))) == 1


@pytest.mark.parametrize(
    ("code", "expected"),
    (
        (EpisodeDraftAssemblyErrorCodeV1.MINIMUM_STORIES, "cel putin 5"),
        (EpisodeDraftAssemblyErrorCodeV1.STALE_PROJECT, "s-a schimbat"),
        (EpisodeDraftAssemblyErrorCodeV1.INVALID_PROJECT, "nu este pregatita"),
    ),
)
def test_preparation_failures_are_safe_romanian_statuses(
    tmp_path: Path, monkeypatch, code, expected: str
) -> None:
    store, _prepared_value = _prepared(tmp_path)

    class Failing:
        def __init__(self, *, store):
            del store

        def prepare(self):
            raise EpisodeDraftAssemblyErrorV1(code, available=3)

    monkeypatch.setattr(desktop_episode, "EpisodeDraftAssemblyPreparerV1", Failing)
    projection = _publish_episode_draft_v1(
        store=store, revision_root=(tmp_path / "drafts").resolve()
    )
    assert projection.current is False
    assert expected in projection.status
    assert not (tmp_path / "drafts").exists()


@pytest.mark.parametrize(
    ("code", "expected"),
    (
        (EpisodeDraftExecutionErrorCodeV1.STALE_INPUT, "s-a schimbat"),
        (EpisodeDraftExecutionErrorCodeV1.INVALID_PARENT, "parintele"),
        (EpisodeDraftExecutionErrorCodeV1.PUBLICATION_FAILED, "publicat"),
        (EpisodeDraftExecutionErrorCodeV1.PUBLICATION_COLLISION, "conflict"),
    ),
)
def test_execution_failures_are_mapped_without_raw_errors(
    tmp_path: Path, monkeypatch, code, expected: str
) -> None:
    store, prepared = _prepared(tmp_path)
    _Prepared.value = prepared
    monkeypatch.setattr(desktop_episode, "EpisodeDraftAssemblyPreparerV1", _Prepared)

    class FailingExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def execute(self, *, prepared):
            del prepared
            raise EpisodeDraftExecutionErrorV1(
                code, stage=EpisodeDraftExecutionStageV1.PUBLICATION
            )

    monkeypatch.setattr(desktop_episode, "EpisodeDraftExecutorV1", FailingExecutor)
    projection = _publish_episode_draft_v1(
        store=store, revision_root=(tmp_path / "drafts").resolve()
    )
    assert projection.current is False
    assert expected in projection.status
    assert "episode draft execution failed" not in projection.status


def test_activation_failure_is_truthful(monkeypatch, tmp_path: Path) -> None:
    store, prepared = _prepared(tmp_path)
    _Prepared.value = prepared
    monkeypatch.setattr(desktop_episode, "EpisodeDraftAssemblyPreparerV1", _Prepared)

    class SplitExecutor:
        def __init__(self, **kwargs):
            del kwargs

        def execute(self, *, prepared):
            del prepared
            return SimpleNamespace(
                activation_status=EpisodeDraftActivationStatusV1.FAILED
            )

    monkeypatch.setattr(desktop_episode, "EpisodeDraftExecutorV1", SplitExecutor)
    projection = _publish_episode_draft_v1(
        store=store, revision_root=(tmp_path / "drafts").resolve()
    )
    assert projection.current is False
    assert "publicat" in projection.status and "activat" in projection.status


def test_recovery_failure_is_read_only_and_visible(tmp_path: Path) -> None:
    class BrokenStore:
        def load_runtime_state(self):
            return SimpleNamespace(current_episode_draft_revision=object())

        def load_episode_draft_revision(self):
            raise ValueError("private detail")

    projection = _recover_episode_draft_v1(store=BrokenStore())
    assert projection.current is False
    assert projection.status == "Draftul episodului salvat nu a putut fi recuperat."


def test_no_revision_explains_disabled_minimum_story_gate() -> None:
    store = SimpleNamespace(
        load_runtime_state=lambda: SimpleNamespace(
            current_episode_draft_revision=None,
            editor_worklist=tuple(
                SimpleNamespace(status=SimpleNamespace(value="completed"))
                for _ in range(4)
            ),
        )
    )
    projection = _recover_episode_draft_v1(store=store)
    assert projection.current is False
    assert projection.status.endswith("disponibile: 4.")


def test_recovery_marks_changed_chief_state_stale_but_inspectable(
    tmp_path: Path, monkeypatch
) -> None:
    store, prepared = _prepared(tmp_path)
    _install_fixture_execution(monkeypatch, prepared)
    _publish_episode_draft_v1(
        store=store, revision_root=(tmp_path / "drafts").resolve()
    )
    project = store.load_runtime_state()
    store.save_chief_editor(
        title="Structura schimbata", items=project.chief_editor_items
    )

    projection = _recover_episode_draft_v1(store=store)

    assert projection.current is True
    assert "inspectabil" in projection.status
    assert "nu mai corespunde" in projection.status
    assert projection.included


def test_queue_uses_application_lane_and_projects_completion(
    tmp_path: Path, monkeypatch
) -> None:
    store, _prepared_value = _prepared(tmp_path)
    project = store.load_runtime_state()
    payload = {
        "title": "Episod",
        "items": tuple((item.reference, "", "") for item in project.editor_materials),
    }
    projected = desktop_episode._EpisodeDraftDesktopProjectionV1(
        status="Draft curent", current=True, revision_id="revision:1"
    )
    monkeypatch.setattr(entrypoint, "_publish_episode_draft_v1", lambda **_: projected)

    class View:
        def __init__(self):
            self.chief = []
            self.drafts = []

        def publish_chief_editor(self, **kwargs):
            self.chief.append(kwargs)

        def publish_episode_draft(self, **kwargs):
            self.drafts.append(kwargs)

    class Controller:
        def submit_application(self, *, task, on_completed):
            self.task = task
            self.on_completed = on_completed

    view, controller, cells = View(), Controller(), {"project": project}
    entrypoint._queue_episode_draft_publication_v1(
        store=store,
        view=view,
        controller=controller,
        cells=cells,
        input=payload,
        revision_root=(tmp_path / "drafts").resolve(),
    )
    assert not view.drafts
    controller.on_completed(result=controller.task())
    assert view.drafts[-1]["revision_id"] == "revision:1"
    assert view.drafts[-1]["current"] is True


def test_view_projection_preserves_order_and_has_no_editing_control() -> None:
    class Variable:
        def set(self, value):
            self.value = value

    view = SimpleNamespace(
        _check=lambda: None,
        _episode_draft_status=Variable(),
        _sync_episode_draft_actions=lambda: None,
    )
    _DesktopMainWindowV1.publish_episode_draft(
        view,
        status="Curent",
        current=True,
        revision_id="revision:1",
        parent_revision_id="",
        included=((3, "Trei", "m:3"), (1, "Unu", "m:1")),
        excluded=((2, "Doi", "motiv"),),
        assembled_text="Text",
    )
    assert view._episode_draft_details[2] == (
        (3, "Trei", "m:3"),
        (1, "Unu", "m:1"),
    )
    source = inspect.getsource(_DesktopMainWindowV1._episode_draft_inspect)
    assert "Entry(" not in source
    assert 'configure(state="disabled")' in source


def test_shared_application_lane_state_disables_publication_action() -> None:
    class Button:
        def configure(self, **kwargs):
            self.state = kwargs["state"]

    view = SimpleNamespace(
        _editor_idle=False,
        _episode_publish_available=True,
        _episode_draft_current=False,
        _bindings={"episode_draft_publish": object()},
        _episode_draft_button=Button(),
        _episode_inspect_button=Button(),
    )
    _DesktopMainWindowV1._sync_episode_draft_actions(view)
    assert view._episode_draft_button.state == "disabled"
    view._editor_idle = True
    _DesktopMainWindowV1._sync_episode_draft_actions(view)
    assert view._episode_draft_button.state == "normal"


def test_episode_draft_desktop_module_has_no_provider_dependency() -> None:
    source = inspect.getsource(desktop_episode)
    assert "openai" not in source.casefold()
    assert "ollama" not in source.casefold()
    assert "provider" not in source.casefold()
