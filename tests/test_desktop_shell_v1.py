from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import pickle
import subprocess
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from pastila_scout.desktop_v1.controller import _DesktopTaskControllerV1
from pastila_scout.desktop_v1.errors import (
    _DesktopShellConfigurationError,
    _DesktopShellExecutionError,
)
from pastila_scout.desktop_v1.models import (
    _DesktopEditorActionInputV1,
    _DesktopLaneV1,
    _DesktopPageV1,
    _DesktopQueueEventV1,
    _DesktopScoutActionInputV1,
    _DesktopShellSnapshotV1,
    _DesktopTaskCompletionV1,
    _DesktopTaskStateV1,
    _reconstruct_desktop_queue_event_v1,
    _reconstruct_desktop_shell_snapshot_v1,
)
from pastila_scout.desktop_v1.resources import _TEXT_V1, _text_v1
from pastila_scout.desktop_v1.views import (
    _EDITOR_REQUIRED_CONFIGURATION,
    _OPENAI_MODEL_CHOICES,
    _SCOUT_CATEGORY_CHOICES,
    _SCOUT_PERIOD_CHOICES,
    _editor_action_enabled,
    _editor_configuration_ready,
    _editor_selection_supported,
    _handoff_label,
    _restored_candidate_summary,
)

ROOT = Path(__file__).resolve().parents[1]


class _Future:
    def cancel(self):
        return False


class _ImmediateExecutor:
    def __init__(self):
        self.calls = []
        self.shutdown_calls = []

    def submit(self, fn):
        self.calls.append(fn)
        fn()
        return _Future()

    def shutdown(self, *, wait, cancel_futures):
        self.shutdown_calls.append((wait, cancel_futures))


class _Harness:
    def __init__(self):
        self.tokens = []
        self.cancelled = []
        self.snapshots = []

    def after(self, delay, callback):
        token = (delay, callback, len(self.tokens))
        self.tokens.append(token)
        return token

    def cancel(self, token):
        self.cancelled.append(token)

    def publish(self, *, snapshot):
        self.snapshots.append(snapshot)

    def drain(self):
        self.tokens[-1][1]()


def _controller():
    harness = _Harness()
    application = _ImmediateExecutor()
    update = _ImmediateExecutor()
    controller = _DesktopTaskControllerV1(
        schedule_after=harness.after,
        cancel_after=harness.cancel,
        publish_snapshot=harness.publish,
        application_executor=application,
        update_executor=update,
    )
    return controller, harness, application, update


def test_package_is_private_and_entrypoint_is_exact():
    package = importlib.import_module("pastila_scout.desktop_v1")
    assert package.__all__ == ()
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'pastila-scout-gui = "pastila_scout.desktop_v1.entrypoint:main"' in text
    assert text.count("pastila-scout-gui") == 1


def test_all_shell_imports_are_passive_under_denied_construction():
    script = r"""
import concurrent.futures
import tkinter
def denied(*args, **kwargs):
    raise AssertionError("construction during import")
tkinter.Tk = denied
concurrent.futures.ThreadPoolExecutor = denied
import pastila_scout.desktop_v1.models
import pastila_scout.desktop_v1.errors
import pastila_scout.desktop_v1.resources
import pastila_scout.desktop_v1.controller
import pastila_scout.desktop_v1.views
import pastila_scout.desktop_v1.entrypoint
"""
    subprocess.run(
        [str(ROOT / ".venv/Scripts/python.exe"), "-c", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_structural_entrypoint_creates_one_root_controller_and_view(monkeypatch):
    from pastila_scout.desktop_v1 import entrypoint

    calls = []

    class TkBridge:
        def call(self, *args):
            calls.append(("tk-call", args))

    class Root:
        tk = TkBridge()

        def __init__(self):
            calls.append("root")

        def after(self, delay, callback):
            return (delay, callback)

        def after_cancel(self, token):
            calls.append(("cancel", token))

        def protocol(self, name, callback):
            calls.append(("protocol", name, callback))

        def withdraw(self):
            calls.append("withdraw")

        def deiconify(self):
            calls.append("deiconify")

        def mainloop(self):
            calls.append("mainloop")

        def quit(self):
            calls.append("quit")

        def destroy(self):
            calls.append("destroy")

    class Controller:
        def __init__(self, **kwargs):
            calls.append(("controller", kwargs))

        def start(self):
            calls.append("start")

        def close(self):
            calls.append("close")

        def select_page(self, *, page):
            calls.append(("page", page))

        def submit_application(self, *, task, on_completed):
            calls.append(("submit", task, on_completed))

    class View:
        def __init__(self, **kwargs):
            calls.append(("view", kwargs))

        def publish_snapshot(self, *, snapshot):
            calls.append(("snapshot", snapshot))

        def bind_scout_action(self, *, callback):
            calls.append(("bind-scout", callback))

        def bind_editor_action(self, *, callback):
            calls.append(("bind-editor", callback))

        def bind_report_action(self, *, callback):
            calls.append(("bind-report", callback))

        def bind_handoff_action(self, *, callback):
            calls.append(("bind-handoff", callback))

        def bind_chief_editor_actions(self, *, save_callback, export_callback):
            calls.append(("bind-chief-editor", save_callback, export_callback))

        def bind_scout_provider_actions(self, *, save_callback, test_callback):
            calls.append(("bind-scout-provider", save_callback, test_callback))

        def publish_candidates(self, *, candidates):
            calls.append(("candidates", candidates))

    class Facade:
        def run_scout(self, *, request, progress_sink):
            del request, progress_sink

        def run_editor(self, *, request, progress_sink):
            del request, progress_sink

        def open_report(self, *, reference):
            del reference

    monkeypatch.setattr(entrypoint.tkinter, "Tk", Root)
    monkeypatch.setattr(entrypoint.sys, "platform", "test")
    monkeypatch.setattr(entrypoint, "_DesktopTaskControllerV1", Controller)
    monkeypatch.setattr(entrypoint, "_DesktopMainWindowV1", View)
    monkeypatch.setattr(
        entrypoint,
        "_compose_state_bound_desktop_application_v1",
        lambda **kwargs: SimpleNamespace(
            facade=Facade(),
            settings=object(),
            database_path=ROOT / "missing.db",
            active_project_path=ROOT / "missing-active-project.json",
            settings_path=ROOT / "config" / "settings.json",
        ),
    )
    assert entrypoint.main() == 0
    assert calls.count("root") == 1
    assert (
        sum(isinstance(item, tuple) and item[0] == "controller" for item in calls) == 1
    )
    assert sum(isinstance(item, tuple) and item[0] == "view" for item in calls) == 1
    assert (
        calls.count("withdraw")
        == calls.count("start")
        == calls.count("deiconify")
        == calls.count("mainloop")
        == calls.count("destroy")
        == 1
    )


def test_withdrawn_tk_window_has_exact_structural_root_and_initial_state():
    import tkinter

    from pastila_scout.desktop_v1.settings import _project_desktop_settings_v1
    from pastila_scout.desktop_v1.views import _DesktopMainWindowV1
    from pastila_scout.windows_state_v1.settings import _default_windows_settings_v1

    try:
        root = tkinter.Tk()
    except tkinter.TclError:
        pytest.skip("Tk is unavailable")
    try:
        root.withdraw()

        def select(*, page):
            assert type(page) is _DesktopPageV1

        view = _DesktopMainWindowV1(
            root=root,
            on_select_page=select,
            on_close=lambda: None,
            settings=_project_desktop_settings_v1(
                settings=_default_windows_settings_v1(
                    defaults_path=ROOT
                    / "src/pastila_scout/desktop_v1/default-settings-v1.json"
                )
            ),
        )
        assert root.title() == "Pastila Scout"
        assert tuple(root.minsize()) == (900, 600)
        assert view._navigation.get_children("") == ("scout", "editor", "chief_editor")
        assert str(view._scout_button.cget("state")) == "disabled"
        assert view._scout_button.cget("text") == "Cauta"
        assert view._scout_button.cget("foreground") == "#e31919"
        assert view._scout_button.cget("font") == "TkDefaultFont 11 bold"
        assert int(view._scout_button.cget("width")) == 16
        assert int(view._scout_button.cget("height")) == 1
        assert view._scout_button.master.cget("background") == "#e31919"
        assert str(view._editor_button.cget("state")) == "disabled"
        assert str(view._editor_worklist.cget("selectmode")) == "extended"
        assert view._editor_button.cget("text") == "Genereaza"
        assert view._editor_button.cget("foreground") == "#e31919"
        assert view._editor_button.cget("font") == "TkDefaultFont 11 bold"
        assert view._editor_button.master.cget("background") == "#e31919"
        assert view._chief_save_button.cget("text") == "Salveaza"
        assert view._chief_save_button.cget("foreground") == "#e31919"
        assert view._chief_save_button.cget("font") == "TkDefaultFont 11 bold"
        assert view._chief_save_button.master.cget("background") == "#e31919"
        assert view._chief_export_button.cget("text") == "Exporta structura"
        assert view._chief_export_button.cget("foreground") == "#e31919"
        assert view._chief_export_button.cget("font") == "TkDefaultFont 11 bold"
        assert view._chief_export_button.master.cget("background") == "#e31919"
        assert view._chief_save_button.cget("width") == view._chief_export_button.cget(
            "width"
        )
        assert view._chief_save_button.cget("height") == view._chief_export_button.cget(
            "height"
        )
        assert str(view._report_button.cget("state")) == "disabled"
        editor_actions = []
        view.bind_editor_action(callback=lambda **kwargs: editor_actions.append(kwargs))
        view.publish_editor_worklist(
            items=(
                (7, "Prima stire", "pending"),
                (8, "A doua stire", "pending"),
                (9, "A treia stire", "completed"),
            ),
        )
        assert view._editor_worklist.get_children("") == ("7", "8", "9")
        assert view._editor_worklist.item("7", "values") == (
            "Prima stire",
            "In asteptare",
        )
        assert view._editor_worklist.item("8", "values")[1] == "In asteptare"
        assert view._editor_worklist.item("9", "values")[1] == "Generata"
        view._editor_worklist.selection_set("7")
        view._editor_worklist.focus("7")
        view._editor_worklist_changed(None)
        assert view._active_project.get() == "Prima stire"
        assert str(view._editor_button.cget("state")) == "normal"
        view._editor_idle = False
        view._editor_worklist_changed(None)
        assert str(view._editor_button.cget("state")) == "disabled"
        view.publish_editor_worklist(
            items=(
                (7, "Prima stire", "pending"),
                (8, "A doua stire", "pending"),
                (9, "A treia stire", "completed"),
            ),
        )
        assert view._editor_worklist.selection() == ("7",)
        assert str(view._editor_button.cget("state")) == "disabled"
        view._editor_idle = True
        view._editor_worklist_changed(None)
        assert str(view._editor_button.cget("state")) == "normal"
        view._editor_worklist.selection_set(("7", "8"))
        view._editor_worklist.focus("8")
        view._editor_worklist_changed(None)
        assert view._active_project.get() == "A doua stire"
        assert str(view._editor_button.cget("state")) == "disabled"
        view._editor_worklist.selection_set("8")
        view._editor_worklist_changed(None)
        assert str(view._editor_button.cget("state")) == "normal"
        view._editor()
        assert editor_actions[-1]["input"].event_id == 8
        view.publish_editor_worklist(
            items=((7, "Prima stire", "running"), (8, "A doua stire", "failed")),
        )
        assert view._editor_worklist.item("7", "values")[1] == "In procesare"
        assert view._editor_worklist.item("8", "values")[1] == "Eroare"
        assert str(view._editor_button.cget("state")) == "disabled"
        view.publish_editor_worklist(items=())
        assert view._editor_worklist.get_children("") == ()
        assert view._active_project.get() == ""
        assert str(view._editor_button.cget("state")) == "disabled"
    finally:
        root.destroy()


def test_editor_slice2_generation_selection_is_safely_bounded():
    assert tuple(
        _text_v1(key=f"editor.worklist.{status}")
        for status in ("pending", "running", "completed", "failed")
    ) == ("In asteptare", "In procesare", "Generata", "Eroare")
    eligible = frozenset({7, 8})
    assert _editor_selection_supported(
        selected_event_ids=(7,), eligible_event_ids=eligible
    )
    assert _editor_selection_supported(
        selected_event_ids=(8,), eligible_event_ids=eligible
    )
    assert not _editor_selection_supported(
        selected_event_ids=(), eligible_event_ids=eligible
    )
    assert not _editor_selection_supported(
        selected_event_ids=(7, 8), eligible_event_ids=eligible
    )
    assert not _editor_selection_supported(
        selected_event_ids=(9,), eligible_event_ids=eligible
    )
    assert not _editor_selection_supported(
        selected_event_ids=(7,), eligible_event_ids=frozenset()
    )
    baseline = {
        "idle": True,
        "callback_bound": True,
        "configuration_ready": True,
        "selected_event_ids": (7,),
        "eligible_event_ids": eligible,
    }
    assert _editor_action_enabled(**baseline)
    for changed in (
        {"idle": False},
        {"callback_bound": False},
        {"configuration_ready": False},
        {"selected_event_ids": ()},
        {"selected_event_ids": (7, 8)},
        {"selected_event_ids": (9,)},
    ):
        assert not _editor_action_enabled(**(baseline | changed))


def test_about_projects_exact_package_version_without_redesign() -> None:
    import inspect

    from pastila_scout import __version__
    from pastila_scout.desktop_v1.resources import _text_v1
    from pastila_scout.desktop_v1.views import _DesktopMainWindowV1

    assert _text_v1(key="about.body") == "Pastila Scout"
    assert _text_v1(key="about.version") == __version__
    source = inspect.getsource(_DesktopMainWindowV1._show_about)
    assert '_text_v1(key="about.body")' in source
    assert '_text_v1(key="about.version")' in source


def test_models_are_closed_safe_and_reconstructable():
    snapshot = _DesktopShellSnapshotV1(
        _DesktopPageV1.SCOUT,
        _DesktopTaskStateV1.IDLE,
        _DesktopTaskStateV1.IDLE,
        False,
    )
    assert _reconstruct_desktop_shell_snapshot_v1(snapshot) == snapshot
    assert copy.copy(snapshot) == snapshot
    completion = _DesktopTaskCompletionV1(object())
    event = _DesktopQueueEventV1(
        _DesktopLaneV1.APPLICATION, _DesktopTaskStateV1.COMPLETED, completion
    )
    assert _reconstruct_desktop_queue_event_v1(event) == event
    assert "opaque" in repr(completion)
    with pytest.raises(_DesktopShellConfigurationError):
        _DesktopQueueEventV1(_DesktopLaneV1.APPLICATION, _DesktopTaskStateV1.COMPLETED)
    with pytest.raises(_DesktopShellConfigurationError):
        _DesktopShellSnapshotV1(
            _DesktopPageV1.SCOUT,
            _DesktopTaskStateV1.CLOSED,
            _DesktopTaskStateV1.CLOSED,
            False,
        )
    with pytest.raises(TypeError):
        pickle.dumps(snapshot)


def test_action_inputs_are_redacted_and_exact():
    scout = _DesktopScoutActionInputV1("7", "all")
    assert "7" not in repr(scout)
    editor = _DesktopEditorActionInputV1(
        event_id=7,
        scout_input_path="a",
        selection_profile_path="b",
        episode_context_path="c",
        generation_config_path="d",
        provider="openai",
        model="m",
        timeout_seconds="10",
        output_path="o",
        no_replace=True,
    )
    assert "openai" not in repr(editor)
    with pytest.raises(_DesktopShellConfigurationError):
        _DesktopScoutActionInputV1(7, "all")


def test_daily_scout_choices_and_restored_candidate_summary_are_truthful():
    assert _OPENAI_MODEL_CHOICES == ("gpt-4.1-mini",)
    assert _SCOUT_PERIOD_CHOICES == ("1", "3", "7", "14", "30")
    assert _SCOUT_CATEGORY_CHOICES == (
        "all",
        "Politica",
        "Social",
        "Conspiratii",
        "Economie",
        "CanCan",
        "Externe",
        "Diverse",
    )
    assert _restored_candidate_summary(current="0", count=3) == "3 candidati restaurati"
    assert _restored_candidate_summary(current="Surse: 14", count=3) == "Surse: 14"
    assert _handoff_label(0) == _handoff_label(1) == "Trimite in Editor"
    assert _handoff_label(3) == "Trimite in Editor (3)"


def test_integrated_editor_uses_runtime_configuration_not_legacy_paths():
    class Value:
        def __init__(self, value):
            self.value = value

        def get(self):
            return self.value

    missing = {name: Value("") for name in _EDITOR_REQUIRED_CONFIGURATION}
    configured = {name: Value(name) for name in _EDITOR_REQUIRED_CONFIGURATION}
    configured.update(
        selection_profile_path=Value(""),
        episode_context_path=Value(""),
        generation_config_path=Value(""),
    )
    assert not _editor_configuration_ready(missing, provider="ollama")
    assert not _editor_configuration_ready(configured, provider="")
    assert _editor_configuration_ready(configured, provider="ollama")


def test_resources_are_exact_unique_nfc_and_unknown_is_safe():
    import unicodedata

    assert len(dict(_TEXT_V1)) == len(_TEXT_V1)
    assert all(unicodedata.normalize("NFC", value) == value for _, value in _TEXT_V1)
    assert _text_v1(key="scout.period") == "Perioada"
    assert _text_v1(key="scout.category") == "Categorie"
    assert _text_v1(key="scout.run") == "Cauta"
    assert _text_v1(key="editor.active_project") == "Stire selectata"
    forbidden = set("ăâîșşțţĂÂÎȘŞȚŢ")
    assert not any(forbidden.intersection(value) for _, value in _TEXT_V1)
    assert _text_v1(key="scout.provider") == "AI Engine"
    assert _text_v1(key="editor.provider") == "AI Engine"
    assert not any("Furnizor" in value for _, value in _TEXT_V1)
    with pytest.raises(_DesktopShellConfigurationError):
        _text_v1(key="missing")


def test_controller_delivers_one_result_on_controller_thread_and_returns_idle():
    controller, harness, application, update = _controller()
    thread = threading.get_ident()
    delivered = []

    def completed(*, result):
        delivered.append((result, threading.get_ident()))

    controller.start()
    controller.submit_application(task=lambda: "result", on_completed=completed)
    harness.drain()
    assert delivered == [("result", thread)]
    assert harness.snapshots[-1].application_state is _DesktopTaskStateV1.COMPLETED
    harness.drain()
    assert harness.snapshots[-1].application_state is _DesktopTaskStateV1.IDLE
    assert len(application.calls) == 1
    assert update.calls == []
    controller.close()
    assert application.shutdown_calls == [(False, True)]
    assert update.shutdown_calls == [(False, True)]


def test_two_lanes_are_independent_and_close_is_idempotent():
    controller, harness, application, update = _controller()
    controller.start()
    controller.submit_application(task=lambda: 1, on_completed=lambda *, result: None)
    controller.submit_update(task=lambda: 2, on_completed=lambda *, result: None)
    harness.drain()
    assert len(application.calls) == len(update.calls) == 1
    controller.close()
    controller.close()
    assert application.shutdown_calls == update.shutdown_calls == [(False, True)]
    assert controller.snapshot().is_closed


def test_duplicate_failure_and_handler_failure_are_safe():
    controller, harness, _, _ = _controller()
    controller.start()
    controller.submit_application(task=lambda: 1, on_completed=lambda *, result: 1 / 0)
    with pytest.raises(_DesktopShellExecutionError):
        controller.submit_application(
            task=lambda: 2, on_completed=lambda *, result: None
        )
    harness.drain()
    assert harness.snapshots[-1].application_state is _DesktopTaskStateV1.FAILED
    controller.close()


def test_wrong_thread_access_is_rejected():
    controller, _, _, _ = _controller()
    errors = []

    def access():
        try:
            controller.snapshot()
        except _DesktopShellConfigurationError as error:
            errors.append(error)

    thread = threading.Thread(target=access)
    thread.start()
    thread.join()
    assert len(errors) == 1
    assert type(errors[0]) is _DesktopShellConfigurationError
    controller.close()


def test_values_controller_and_errors_are_final():
    for base in (
        _DesktopShellSnapshotV1,
        _DesktopTaskControllerV1,
        _DesktopShellConfigurationError,
    ):
        with pytest.raises(TypeError):
            type("ForbiddenSubclass", (base,), {})


def test_executor_validation_does_not_execute_property():
    touched = []

    class DynamicExecutor:
        @property
        def submit(self):
            touched.append("submit")
            return lambda fn: None

        def shutdown(self, *, wait, cancel_futures):
            del wait, cancel_futures

    harness = _Harness()
    with pytest.raises(_DesktopShellConfigurationError):
        _DesktopTaskControllerV1(
            schedule_after=harness.after,
            cancel_after=harness.cancel,
            publish_snapshot=harness.publish,
            application_executor=DynamicExecutor(),
        )
    assert touched == []


def test_schedule_after_accepts_real_tk_compatible_variadic_shape():
    calls = []

    def after(ms, func=None, *args):
        calls.append((ms, func, args))
        return object()

    harness = _Harness()
    controller = _DesktopTaskControllerV1(
        schedule_after=after,
        cancel_after=harness.cancel,
        publish_snapshot=harness.publish,
        application_executor=_ImmediateExecutor(),
        update_executor=_ImmediateExecutor(),
    )
    controller.start()
    assert calls[0][0] == 50
    controller.close()


def test_import_graph_has_no_backend_or_composition_ownership(monkeypatch):
    forbidden = {
        "pastila_scout.desktop_application_v1",
        "pastila_scout.desktop_editor_v1",
        "pastila_scout.desktop_scout_v1",
        "pastila_scout.editor_cli_run_v1",
        "pastila_scout.provider_v2",
        "sqlite3",
        "subprocess",
    }
    for path in (ROOT / "src/pastila_scout/desktop_v1").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        violations = {
            name
            for name in imported
            if any(name == item or name.startswith(item + ".") for item in forbidden)
        }
        if path.name in {"entrypoint.py", "state_composition.py"}:
            violations = {
                name
                for name in violations
                if not name.startswith(
                    (
                        "pastila_scout.desktop_application_v1",
                        "pastila_scout.desktop_editor_v1",
                    )
                )
            }
        assert violations == set()
    del monkeypatch


def test_frozen_authority_hashes_and_phase_scope():
    expected = {
        "docs/windows-application/DesktopShellSpecificationV1.md": "5B565CAC42AFDEB0E426B078FBC2A5C7F2836C73A4D64F723AA029787FF9AAFB",
        "docs/windows-update/WindowsUpdateProtocolSpecificationV1.md": "9E4615576785062A5C902CA8BBA663EE1F9BF1112F98ED881F7620B0CAD568ED",
        "docs/windows-update/WindowsUpdatePersistenceFormatSpecificationV1.md": "05CF922678BD9DCD4C6837B00B8896CA7A014D839C84290A7B5D70F54158DFF6",
    }
    for path, digest in expected.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest().upper() == digest
    productization = (
        "docs/windows-application/WindowsDesktopProductizationSpecificationV1.md"
    )
    historical_blob = subprocess.check_output(
        ["git", "show", f"phase-5.1d-desktop-shell-r1-verified:{productization}"],
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
    allowed = {
        "pyproject.toml",
        "tests/test_desktop_shell_v1.py",
        *{
            f"src/pastila_scout/desktop_v1/{name}"
            for name in (
                "__init__.py",
                "entrypoint.py",
                "controller.py",
                "models.py",
                "views.py",
                "resources.py",
                "errors.py",
            )
        },
    }
    assert len(allowed) == 9
    baseline = "phase-5.1c-desktop-shell-spec-v1-ready"
    verified = "phase-5.1d-desktop-shell-r1-verified"
    facade_spec = "phase-5.1a-desktop-application-facade-spec-v1-ready"
    facade_verified = "phase-5.1b-desktop-application-facade-r1-verified"
    facade_dependencies = {
        "docs/windows-application/DesktopApplicationFacadeSpecificationV1.md": (
            facade_spec,
            "DB992030BA19FD2C80F6DA7627D3CEC8F4FC2DB9634A5F9892527C4E37FBCD7E",
        ),
        "src/pastila_scout/desktop_application_v1/__init__.py": (
            facade_verified,
            "E497311162A5F00FE9141805E8FD48F2829483D206EE104D2FF1872B8D6692E5",
        ),
        "src/pastila_scout/desktop_application_v1/errors.py": (
            facade_verified,
            "191E87DFFF5CAE4BB980E376EC56139DF1D4AB0E72A127689F2DD0AFE43D7A6D",
        ),
        "src/pastila_scout/desktop_application_v1/models.py": (
            facade_verified,
            "4DEDC9462E85D56383BCFCD15CE1B05D67C5E5A6D10E76F57F88A5E445C48BBD",
        ),
        "src/pastila_scout/desktop_application_v1/services.py": (
            facade_verified,
            "0D789E87433F21E12C85FCBDACF55A722D7C23B8F13F0A3A81326E6EB2B410E7",
        ),
        "tests/test_desktop_application_v1.py": (
            facade_verified,
            "D94F1B6012C97DD2CA182E04E44B6FB0B9E0763FD23B57AFA217D34632484782",
        ),
    }

    def git_lines(*arguments: str) -> set[str]:
        return {
            line.replace("\\", "/")
            for line in subprocess.run(
                ["git", *arguments],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
        }

    def assert_historical_scope(historical_delta: set[str]) -> None:
        assert historical_delta == allowed

    def assert_historical_dependency(
        historical_blob: bytes, expected_digest: str, current_blob: bytes
    ) -> None:
        del current_blob
        assert hashlib.sha256(historical_blob).hexdigest().upper() == expected_digest

    def assert_staging(paths: set[str]) -> None:
        assert paths == set()

    def assert_tag_target(actual: str, expected: str) -> None:
        assert actual == expected

    assert (
        subprocess.run(
            ["git", "rev-list", "-n", "1", baseline],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == "0c516dcfe8be32addb3a03a6b5bc543289cb540f"
    )
    assert (
        subprocess.run(
            ["git", "rev-list", "-n", "1", verified],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == "1f85157ad447796ada576d48fc1687e42e09c728"
    )
    assert (
        subprocess.run(
            ["git", "rev-list", "-n", "1", facade_spec],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == "73823596b0131deb0234c610e5f73daf18422f7e"
    )
    assert (
        subprocess.run(
            ["git", "rev-list", "-n", "1", facade_verified],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == "64ae9c9ddf26797e3fe887b28d86c1352bd411f6"
    )
    historical_productization_tag = (
        "phase-5-windows-desktop-productization-spec-v11-"
        "gui-command-time-composition-roadmap-ready"
    )
    assert git_lines("cat-file", "-t", historical_productization_tag) == {"tag"}
    historical_productization_target = subprocess.check_output(
        ["git", "rev-parse", f"{historical_productization_tag}^{{}}"],
        cwd=ROOT,
        text=True,
    ).strip()
    assert_tag_target(
        historical_productization_target,
        "4727a480ad95da82dd6a982bfdde53ae0e73d0a6",
    )
    with pytest.raises(AssertionError):
        assert_tag_target("synthetic-wrong-target", historical_productization_target)
    tagged_productization_blob = subprocess.check_output(
        ["git", "show", f"{historical_productization_tag}:{productization}"],
        cwd=ROOT,
    )
    assert tagged_productization_blob == historical_blob

    for path, (authority, digest) in facade_dependencies.items():
        historical_blob = subprocess.run(
            ["git", "show", f"{authority}:{path}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        assert_historical_dependency(
            historical_blob, digest, (ROOT / path).read_bytes()
        )
        assert_historical_dependency(
            historical_blob, digest, b"neutral future descendant bytes"
        )
        with pytest.raises(AssertionError):
            assert_historical_dependency(
                historical_blob + b"mutation", digest, historical_blob
            )

    historical_delta = git_lines("diff", "--name-only", baseline, verified)
    assert_historical_scope(historical_delta)
    assert_staging(git_lines("diff", "--cached", "--name-only"))
    with pytest.raises(AssertionError):
        assert_staging({"synthetic-staged-mutation.py"})

    for path in allowed:
        if path.startswith("src/pastila_scout/desktop_v1/"):
            committed = subprocess.run(
                ["git", "show", f"{verified}:{path}"],
                cwd=ROOT,
                check=True,
                capture_output=True,
            ).stdout
            if path not in {
                "src/pastila_scout/desktop_v1/entrypoint.py",
                "src/pastila_scout/desktop_v1/models.py",
                "src/pastila_scout/desktop_v1/resources.py",
                "src/pastila_scout/desktop_v1/views.py",
            }:
                assert (ROOT / path).read_bytes() == committed

    unrelated_future_paths = {
        "docs/future-neutral.md",
        "src/pastila_scout/future_neutral/__init__.py",
        "tests/test_future_neutral.py",
        "src/pastila_scout/desktop_v1/future_descendant.py",
    }
    assert unrelated_future_paths.isdisjoint(historical_delta)
    assert_historical_scope(historical_delta)
    with pytest.raises(AssertionError):
        assert_historical_scope(historical_delta | {"historical-expansion.py"})
    with pytest.raises(AssertionError):
        assert_historical_scope(historical_delta - {"pyproject.toml"})
