from __future__ import annotations

import ast
import hashlib
import inspect
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_desktop_application_v1 import scout_result
from test_editor_application_contracts_v1 import request as application_request

from pastila_scout.desktop_application_v1 import (
    DesktopOperationKindV1,
    DesktopProgressEventV1,
    DesktopProgressStageV1,
    EditorDesktopRequestV1,
    ScoutDesktopCategoryV1,
)
from pastila_scout.desktop_v1 import entrypoint
from pastila_scout.desktop_v1.errors import _DesktopShellConfigurationError
from pastila_scout.desktop_v1.models import (
    _DesktopEditorActionInputV1,
    _DesktopScoutActionInputV1,
)

ROOT = Path(__file__).resolve().parents[1]


class _Root:
    def __init__(self, events, *, fail=None):
        self.events = events
        self.fail = fail
        self.tk = self
        events.append("root")

    def call(self, *args):
        self.events.append(("scaling", args))
        if self.fail == "scaling":
            raise RuntimeError("secret")

    def withdraw(self):
        self.events.append("withdraw")
        if self.fail == "withdraw":
            raise RuntimeError("secret")

    def after(self, delay, callback):
        return (delay, callback)

    def after_cancel(self, token):
        self.events.append(("cancel", token))

    def protocol(self, name, callback):
        self.events.append(("protocol", name))

    def deiconify(self):
        self.events.append("deiconify")
        if self.fail == "deiconify":
            raise RuntimeError("secret")

    def mainloop(self):
        self.events.append("mainloop")
        if self.fail == "mainloop":
            raise RuntimeError("secret")

    def quit(self):
        self.events.append("quit")

    def destroy(self):
        self.events.append("destroy")


class _Controller:
    def __init__(self, events, *, fail=None, **kwargs):
        del kwargs
        self.events = events
        self.fail = fail
        self.closed = 0
        self.submissions = []
        events.append("controller")
        if fail == "controller":
            raise RuntimeError("secret")

    def select_page(self, *, page):
        del page

    def submit_application(self, *, task, on_completed):
        self.submissions.append((task, on_completed))

    def start(self):
        self.events.append("start")
        if self.fail == "start":
            self.close()
            raise RuntimeError("secret")

    def close(self):
        self.closed += 1
        self.events.append("close")


class _View:
    def __init__(self, events, *, fail=None, **kwargs):
        del kwargs
        self.events = events
        self.fail = fail
        self.bindings = {}
        self.published = []
        events.append("view")
        if fail == "view":
            raise RuntimeError("secret")

    def publish_snapshot(self, *, snapshot):
        del snapshot

    def _bind(self, name, callback):
        self.events.append("bind-" + name)
        if self.fail == name:
            raise RuntimeError("secret")
        self.bindings[name] = callback

    def bind_scout_action(self, *, callback):
        self._bind("scout", callback)

    def bind_editor_action(self, *, callback):
        self._bind("editor", callback)

    def bind_editor_retry_action(self, *, callback):
        self._bind("editor-retry", callback)

    def bind_report_action(self, *, callback):
        self._bind("report", callback)

    def bind_handoff_action(self, *, callback):
        self._bind("handoff", callback)

    def bind_chief_editor_actions(self, *, save_callback, export_callback):
        self._bind("chief-save", save_callback)
        self._bind("chief-export", export_callback)

    def bind_episode_draft_action(self, *, callback):
        self._bind("episode-draft", callback)

    def bind_episode_draft_export_action(self, *, callback):
        self._bind("episode-export", callback)

    def bind_episode_draft_approval_action(self, *, callback):
        self._bind("episode-approval", callback)

    def bind_episode_draft_final_action(self, *, callback):
        self._bind("episode-final", callback)

    def bind_scout_provider_actions(self, *, save_callback, test_callback):
        self._bind("provider-save", save_callback)
        self._bind("provider-test", test_callback)

    def bind_scout_source_action(self, *, callback):
        self._bind("source", callback)

    def publish_candidates(self, *, candidates):
        self.events.append(("publish-candidates", candidates))

    def publish_active_project(self, **kwargs):
        self.published.append(("active-project", kwargs))

    def publish_editor_worklist(self, **kwargs):
        self.published.append(("editor-worklist", kwargs))

    def publish_chief_editor(self, **kwargs):
        self.published.append(("chief-editor", kwargs))

    def publish_scout_result(self, **kwargs):
        self.published.append(("scout", kwargs))

    def publish_editor_result(self, **kwargs):
        self.published.append(("editor", kwargs))


class _Facade:
    def __init__(self, events):
        self.events = events
        self.calls = []

    def run_scout(self, *, request, progress_sink):
        self.calls.append(("scout", request, progress_sink))
        return object()

    def run_editor(self, *, request, progress_sink):
        self.calls.append(("editor", request, progress_sink))
        return object()

    def open_report(self, *, reference):
        self.calls.append(("report", reference))


def _startup(monkeypatch, *, failure=None, active_project=None):
    events = []
    root = _Root(events, fail=failure)
    facade = _Facade(events)
    captured = {}

    def compose(**kwargs):
        assert set(kwargs) == {
            "frozen",
            "environment",
            "development_root",
            "migration_consent",
        }
        events.append("compose")
        if failure == "composition":
            raise RuntimeError("secret-composition")
        return SimpleNamespace(
            facade=facade,
            settings=object(),
            database_path=ROOT / ".startup-integration-never-created.db",
            active_project_path=ROOT / ".startup-integration-never-created.json",
            settings_path=ROOT / ".startup-integration-settings-never-created.json",
        )

    def controller(**kwargs):
        value = _Controller(events, fail=failure, **kwargs)
        captured["controller"] = value
        return value

    def view(**kwargs):
        value = _View(events, fail=failure, **kwargs)
        captured["view"] = value
        return value

    class Store:
        def __init__(self, **kwargs):
            del kwargs

        def load(self):
            return active_project

        def load_runtime_state(self):
            return active_project

        def list_useful_candidates_v1_2(self):
            return ()

        def list_candidates(self, *, category=None):
            del category
            return ()

    messages = []
    monkeypatch.setattr(entrypoint.sys, "platform", "test")
    monkeypatch.setattr(entrypoint.tkinter, "Tk", lambda: root)
    monkeypatch.setattr(
        entrypoint, "_compose_state_bound_desktop_application_v1", compose
    )
    monkeypatch.setattr(entrypoint, "_DesktopTaskControllerV1", controller)
    monkeypatch.setattr(entrypoint, "_DesktopMainWindowV1", view)
    monkeypatch.setattr(entrypoint, "ActiveProjectStoreV1", Store)
    monkeypatch.setattr(
        entrypoint.messagebox,
        "showerror",
        lambda **kwargs: messages.append(kwargs),
    )
    return entrypoint.main(), events, facade, captured, messages


def test_exact_success_order_and_one_shared_facade(monkeypatch) -> None:
    code, events, facade, captured, messages = _startup(monkeypatch)
    assert code == 0
    assert messages == []
    assert events == [
        "root",
        ("scaling", ("tk", "scaling", 2.0)),
        "withdraw",
        "compose",
        "controller",
        "view",
        "bind-scout",
        "bind-editor",
        "bind-editor-retry",
        "bind-report",
        "bind-handoff",
        "bind-chief-save",
        "bind-chief-export",
        "bind-episode-draft",
        "bind-episode-export",
        "bind-episode-approval",
        "bind-episode-final",
        "bind-provider-save",
        "bind-provider-test",
        "bind-source",
        ("publish-candidates", ()),
        ("protocol", "WM_DELETE_WINDOW"),
        "start",
        "deiconify",
        "mainloop",
        "close",
        "destroy",
    ]
    view = captured["view"]
    for name in ("scout", "editor", "report"):
        assert facade in inspect.getclosurevars(view.bindings[name]).nonlocals.values()


@pytest.mark.parametrize(
    "failure,presented,mainloop",
    [
        ("composition", True, False),
        ("controller", True, False),
        ("view", True, False),
        ("scout", True, False),
        ("editor", True, False),
        ("report", True, False),
        ("start", True, False),
        ("deiconify", True, False),
        ("mainloop", False, True),
    ],
)
def test_failure_atomicity_matrix(monkeypatch, failure, presented, mainloop) -> None:
    code, events, _, captured, messages = _startup(monkeypatch, failure=failure)
    assert code == 1
    assert bool(messages) is presented
    assert ("mainloop" in events) is mainloop
    assert events.count("compose") == 1
    assert events.count("destroy") == 1
    if failure in {"editor", "report", "start", "deiconify"}:
        assert events.index("withdraw") < events.index("bind-scout")
        assert "deiconify" not in events or failure in {"deiconify", "mainloop"}
    if "controller" in captured:
        assert captured["controller"].closed >= 1


@pytest.mark.parametrize("failure", ["scaling", "withdraw"])
def test_precomposition_failure_never_composes_or_presents(
    monkeypatch, failure
) -> None:
    code, events, _, _, messages = _startup(monkeypatch, failure=failure)
    assert code == 1
    assert "compose" not in events
    assert messages == []
    assert events.count("destroy") == 1


def test_root_construction_failure_returns_one_without_presentation(
    monkeypatch,
) -> None:
    messages = []
    monkeypatch.setattr(entrypoint.sys, "platform", "test")
    monkeypatch.setattr(
        entrypoint.tkinter, "Tk", lambda: (_ for _ in ()).throw(RuntimeError("secret"))
    )
    monkeypatch.setattr(
        entrypoint.messagebox,
        "showerror",
        lambda **kwargs: messages.append(kwargs),
    )
    assert entrypoint.main() == 1
    assert messages == []


@pytest.mark.parametrize(
    "failure", [KeyboardInterrupt(), SystemExit(9), GeneratorExit()]
)
def test_outer_process_control_policy_is_preserved(monkeypatch, failure) -> None:
    code, events, _, _, messages = _startup(monkeypatch)
    del code, events, messages
    monkeypatch.setattr(
        entrypoint,
        "_compose_state_bound_desktop_application_v1",
        lambda **kwargs: (_ for _ in ()).throw(failure),
    )
    with pytest.raises(type(failure)):
        entrypoint.main()


def test_startup_failure_resource_is_exact_and_finite() -> None:
    assert entrypoint._text_v1(key="startup.error") == (
        "Aplicatia nu a putut fi configurata."
    )


def test_frozen_canonical_sources_use_local_appdata_install_root(
    tmp_path, monkeypatch
) -> None:
    local_app_data = tmp_path / "Local"
    unrelated_working_directory = tmp_path / "Desktop"
    unrelated_working_directory.mkdir()
    monkeypatch.chdir(unrelated_working_directory)
    assert entrypoint._canonical_scout_sources_path_v1(
        frozen=True,
        development_root=None,
        environment={"LOCALAPPDATA": str(local_app_data)},
    ) == (
        local_app_data / "Programs" / "PastilaScout" / "app" / "config" / "sources.yaml"
    )


def test_scout_request_is_exact_and_rejects_equivalent_text(monkeypatch) -> None:
    monkeypatch.setattr(
        entrypoint.uuid, "uuid4", lambda: type("U", (), {"hex": "a" * 32})()
    )
    value = _DesktopScoutActionInputV1("7", "Politica")
    request = entrypoint._scout_request(value)
    assert request.operation_reference == "scout-desktop-v1:" + "a" * 32
    assert request.period_days == 7
    assert request.category is ScoutDesktopCategoryV1.POLITICA
    for period in ("07", "+7", "7 ", "7.0", "2"):
        with pytest.raises(_DesktopShellConfigurationError):
            entrypoint._scout_request(_DesktopScoutActionInputV1(period, "Politica"))


def test_editor_values_and_nested_request_are_exact(tmp_path, monkeypatch) -> None:
    source = application_request(tmp_path, operation_reference="source")
    raw = _DesktopEditorActionInputV1(
        event_ids=(44,),
        scout_input_path="scout.json",
        selection_profile_path="profile.json",
        episode_context_path="context.json",
        generation_config_path="generation.json",
        provider=source.generation_configuration.provider.value,
        model=source.generation_configuration.model_identifier,
        timeout_seconds=str(source.generation_configuration.timeout_seconds),
        output_path="output.json",
        no_replace=True,
    )
    monkeypatch.setattr(
        entrypoint.uuid, "uuid4", lambda: type("U", (), {"hex": "b" * 32})()
    )
    values = entrypoint._editor_values(raw)
    assert values[-2] == Path.cwd() / "output.json"
    assert values[-1] == "editor-desktop-v1:" + "b" * 32

    monkeypatch.setattr(entrypoint, "load_contract", lambda path: source.scout_input)
    monkeypatch.setattr(
        entrypoint,
        "EditorSelectionProfileAuthorityV1",
        lambda: type(
            "A", (), {"load": lambda self, *, path: source.selection_profile}
        )(),
    )
    monkeypatch.setattr(
        entrypoint,
        "EditorEpisodeContextAuthorityV1",
        lambda: type("A", (), {"load": lambda self, *, path: source.episode_context})(),
    )
    monkeypatch.setattr(
        entrypoint,
        "EditorApplicationGenerationConfigurationAuthorityV1",
        lambda: type(
            "A",
            (),
            {"load": lambda self, *, path: source.generation_configuration},
        )(),
    )
    captured = []

    class Facade:
        def run_editor(self, *, request, progress_sink):
            captured.append((request, progress_sink))
            return object()

    assert entrypoint._run_editor(Facade(), values) is not None
    request, sink = captured[0]
    assert type(request) is EditorDesktopRequestV1
    nested = request.application_request
    assert nested.operation_reference == "editor-desktop-v1:" + "b" * 32
    assert nested.cancellation.cancellation_requested is False
    assert nested.generation_configuration == source.generation_configuration
    assert type(sink) is entrypoint._DesktopStartupProgressSinkV1


def test_progress_sink_is_validated_stateless_and_final() -> None:
    sink = entrypoint._DesktopStartupProgressSinkV1()
    event = DesktopProgressEventV1(
        operation_reference="operation",
        operation=DesktopOperationKindV1.SCOUT,
        stage=DesktopProgressStageV1.ACCEPTED,
    )
    assert sink.publish(event=event) is None
    assert sink.__slots__ == ()
    with pytest.raises(TypeError):

        class Invalid(entrypoint._DesktopStartupProgressSinkV1):
            pass


def test_report_binding_calls_same_facade_directly(monkeypatch) -> None:
    _, _, facade, captured, _ = _startup(monkeypatch)
    captured["view"].bindings["report"](reference="opaque-report")
    assert facade.calls == [("report", "opaque-report")]


def test_scout_binding_submits_through_controller_and_projects_result(
    monkeypatch,
) -> None:
    _, _, facade, captured, _ = _startup(monkeypatch)
    view = captured["view"]
    view.bindings["scout"](
        input=_DesktopScoutActionInputV1(period="7", category="Politica")
    )
    assert len(captured["controller"].submissions) == 1
    task, on_completed = captured["controller"].submissions[0]
    expected = scout_result()
    facade.run_scout = lambda *, request, progress_sink: (
        facade.calls.append(("scout", request, progress_sink)) or expected
    )
    result = task()
    on_completed(result=result)
    _, request, sink = facade.calls[0]
    assert request.period_days == 7
    assert request.category is ScoutDesktopCategoryV1.POLITICA
    assert type(sink) is entrypoint._DesktopStartupProgressSinkV1
    assert view.published == [
        (
            "scout",
            {
                "summary": "5 articole - 3 noi - duplicate: 2",
                "sources_available": 2,
                "failed_sources": (),
                "footer": "completed",
                "report_reference": "report-1",
            },
        )
    ]


def test_editor_binding_submits_through_controller_and_projects_result(
    monkeypatch,
) -> None:
    active_project = SimpleNamespace(
        title="Proiect activ",
        scout_input=SimpleNamespace(
            ranked_events=(
                SimpleNamespace(event_id=44, canonical_title="Stire activa"),
            )
        ),
        editor_worklist=(
            SimpleNamespace(event_id=44, status=SimpleNamespace(value="pending")),
        ),
        editor_materials=(),
        chief_editor_items=(),
        chief_editor_title="",
    )
    _, _, _, captured, _ = _startup(monkeypatch, active_project=active_project)
    view = captured["view"]
    view.published.clear()
    raw = _DesktopEditorActionInputV1(
        event_ids=(44,),
        scout_input_path="scout.json",
        selection_profile_path="profile.json",
        episode_context_path="context.json",
        generation_config_path="generation.json",
        provider="openai",
        model="model",
        timeout_seconds="30",
        output_path="output.json",
        no_replace=True,
    )
    captured_batch = []
    expected = SimpleNamespace(
        attempted_event_ids=(44,), completed_event_ids=(), failed_event_ids=(44,)
    )
    monkeypatch.setattr(
        entrypoint,
        "_run_editor_batch_v1",
        lambda *, store, event_ids, execute: (
            captured_batch.append((store, event_ids, execute)) or expected
        ),
    )
    view.bindings["editor"](input=raw)
    assert len(captured["controller"].submissions) == 1
    task, on_completed = captured["controller"].submissions[0]
    result = task()
    on_completed(result=result)
    assert captured_batch[0][1] == (44,)
    assert callable(captured_batch[0][2])
    assert view.published[-1] == (
        "editor",
        {"status": "1 procesate: 0 generate, 1 erori"},
    )


def test_import_is_passive_and_ownership_exclusions_are_static() -> None:
    script = "import pastila_scout.desktop_v1.entrypoint"
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert completed.stdout == completed.stderr == ""
    tree = ast.parse(
        (ROOT / "src/pastila_scout/desktop_v1/entrypoint.py").read_text(
            encoding="utf-8"
        )
    )
    names = {
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert not any(
        token in name
        for name in names
        for token in (
            "editor_cli",
            "provider_selection",
            "runtime_composition",
            "poller",
            "desktop_report",
        )
    )


def test_phase_scope_and_frozen_authorities() -> None:
    expected = {
        "docs/windows-application/DesktopStartupIntegrationSpecificationV1.md": "F32D701E3397D2DE8EFA13D1A69D543FA76A826672008A7267060F45DE2E45F9",
    }
    for path, digest in expected.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest().upper() == digest
    productization = (
        "docs/windows-application/WindowsDesktopProductizationSpecificationV1.md"
    )
    historical_blob = subprocess.check_output(
        [
            "git",
            "show",
            f"phase-5.3d-desktop-startup-integration-r1-verified:{productization}",
        ],
        cwd=ROOT,
    )
    assert hashlib.sha256(historical_blob).hexdigest().upper() == (
        "A156A3963253ADEE7A2540B337FD358C33328219DABC0FF4803E9EF318882A3E"
    )
    v12_tag = "phase-5-windows-desktop-productization-spec-v12-windows-state-consumption-roadmap-ready"
    assert (
        subprocess.check_output(
            ["git", "cat-file", "-t", v12_tag], cwd=ROOT, text=True
        ).strip()
        == "tag"
    )
    assert (
        subprocess.check_output(
            ["git", "rev-parse", f"{v12_tag}^{{}}"], cwd=ROOT, text=True
        ).strip()
        == "dbda63533033aa25fe2ea2e970f6943851056078"
    )
    v12_blob = subprocess.check_output(
        ["git", "show", f"{v12_tag}:{productization}"], cwd=ROOT
    )
    assert hashlib.sha256(v12_blob).hexdigest().upper() == (
        "556ECE4D3D64C163CC42B17BD0431A424FB06CFA89011BBCF89EC151EE0D593C"
    )
    maintenance_tag = (
        "phase-5-productization-single-owner-trust-policy-maintenance-r1-verified"
    )
    assert (
        subprocess.check_output(
            ["git", "cat-file", "-t", maintenance_tag], cwd=ROOT, text=True
        ).strip()
        == "tag"
    )
    assert (
        subprocess.check_output(
            ["git", "rev-parse", f"{maintenance_tag}^{{}}"], cwd=ROOT, text=True
        ).strip()
        == "1b8ef121b4ff5d147b069d91a68c33156c51f3a6"
    )
    assert (
        subprocess.check_output(
            ["git", "rev-parse", f"{maintenance_tag}^{{}}^"], cwd=ROOT, text=True
        ).strip()
        == "556ee1a3269329dd78745e2f6bbf8e96dfc5ac07"
    )
    maintained_blob = subprocess.check_output(
        ["git", "show", f"{maintenance_tag}:{productization}"], cwd=ROOT
    )
    assert hashlib.sha256(maintained_blob).hexdigest().upper() == (
        "D73BC2B477CE0BAE00376420CB24F7393D44A251FFA9B4E204B1C5D8DEEF9B70"
    )
    compatibility_tag = (
        "phase-5-productization-historical-integrity-test-compatibility-"
        "maintenance-r1-verified"
    )
    assert (
        subprocess.check_output(
            ["git", "cat-file", "-t", compatibility_tag], cwd=ROOT, text=True
        ).strip()
        == "tag"
    )
    assert (
        subprocess.check_output(
            ["git", "rev-parse", f"{compatibility_tag}^{{}}"],
            cwd=ROOT,
            text=True,
        ).strip()
        == "915750916ee7e71b93047bb53065b94f8f772f50"
    )
    current_productization = (ROOT / productization).read_bytes()
    assert hashlib.sha256(current_productization).hexdigest().upper() == (
        "09D44DD63B8064B0C6887FC2D8AA4C46773F95518B9243DA33B1AB7523F0A064"
    )
    assert maintained_blob != current_productization
    assert historical_blob != v12_blob
    assert v12_blob != maintained_blob
    with pytest.raises(AssertionError):
        assert hashlib.sha256(historical_blob + b"mutation").hexdigest().upper() == (
            "A156A3963253ADEE7A2540B337FD358C33328219DABC0FF4803E9EF318882A3E"
        )
    assert (
        subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"], cwd=ROOT, text=True
        ).strip()
        == ""
    )
    baseline = subprocess.check_output(
        [
            "git",
            "ls-tree",
            "-r",
            "--name-only",
            "phase-5.3c-desktop-startup-integration-spec-v1-ready",
        ],
        cwd=ROOT,
        text=True,
    ).splitlines()
    assert "tests/test_desktop_startup_integration_v1.py" not in baseline
    expected_delta = {
        "src/pastila_scout/desktop_v1/entrypoint.py",
        "src/pastila_scout/desktop_v1/resources.py",
        "tests/test_desktop_shell_v1.py",
        "tests/test_desktop_startup_integration_v1.py",
    }
    phase_tag = "phase-5.3d-desktop-startup-integration-r1-verified"
    tag_exists = (
        subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", phase_tag],
            cwd=ROOT,
            check=False,
            capture_output=True,
        ).returncode
        == 0
    )
    if tag_exists:
        changed = subprocess.check_output(
            [
                "git",
                "diff",
                "--name-only",
                "phase-5.3c-desktop-startup-integration-spec-v1-ready",
                phase_tag,
            ],
            cwd=ROOT,
            text=True,
        ).splitlines()
    else:
        porcelain = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT,
            text=True,
        ).splitlines()
        changed = [line[3:] for line in porcelain]
    assert set(changed) == expected_delta
