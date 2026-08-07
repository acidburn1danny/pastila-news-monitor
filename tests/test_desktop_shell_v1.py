from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import pickle
import subprocess
import threading
from pathlib import Path

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
    monkeypatch.setattr(entrypoint, "_compose_desktop_application_facade_v1", Facade)
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

    from pastila_scout.desktop_v1.views import _DesktopMainWindowV1

    try:
        root = tkinter.Tk()
    except tkinter.TclError:
        pytest.skip("Tk is unavailable")
    try:
        root.withdraw()

        def select(*, page):
            assert type(page) is _DesktopPageV1

        view = _DesktopMainWindowV1(
            root=root, on_select_page=select, on_close=lambda: None
        )
        assert root.title() == "Pastila Scout"
        assert tuple(root.minsize()) == (900, 600)
        assert view._navigation.get_children("") == ("scout", "editor")
        assert str(view._scout_button.cget("state")) == "disabled"
        assert str(view._editor_button.cget("state")) == "disabled"
        assert str(view._report_button.cget("state")) == "disabled"
    finally:
        root.destroy()


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


def test_resources_are_exact_unique_nfc_and_unknown_is_safe():
    import unicodedata

    assert len(dict(_TEXT_V1)) == len(_TEXT_V1)
    assert all(unicodedata.normalize("NFC", value) == value for _, value in _TEXT_V1)
    assert _text_v1(key="scout.run") == "CAUTĂ"
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
        if path.name == "entrypoint.py":
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
        "docs/windows-application/WindowsDesktopProductizationSpecificationV1.md": "A156A3963253ADEE7A2540B337FD358C33328219DABC0FF4803E9EF318882A3E",
        "docs/windows-update/WindowsUpdateProtocolSpecificationV1.md": "9E4615576785062A5C902CA8BBA663EE1F9BF1112F98ED881F7620B0CAD568ED",
        "docs/windows-update/WindowsUpdatePersistenceFormatSpecificationV1.md": "05CF922678BD9DCD4C6837B00B8896CA7A014D839C84290A7B5D70F54158DFF6",
    }
    for path, digest in expected.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest().upper() == digest
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

    def assert_historical_scope(
        historical_delta: set[str], current_paths: set[str]
    ) -> None:
        assert historical_delta == allowed
        shell_prefix = "src/pastila_scout/desktop_v1/"
        assert not {
            path for path in current_paths - allowed if path.startswith(shell_prefix)
        }

    def assert_historical_dependency(
        historical_blob: bytes, expected_digest: str, current_blob: bytes
    ) -> None:
        del current_blob
        assert hashlib.sha256(historical_blob).hexdigest().upper() == expected_digest

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
    current_paths = {
        line[3:].replace("\\", "/")
        for line in subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=all"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    }
    assert_historical_scope(historical_delta, current_paths)
    assert git_lines("diff", "--cached", "--name-only") == set()

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
                "src/pastila_scout/desktop_v1/resources.py",
            }:
                assert (ROOT / path).read_bytes() == committed

    unrelated_future_paths = {
        "docs/future-neutral.md",
        "src/pastila_scout/future_neutral/__init__.py",
        "tests/test_future_neutral.py",
    }
    assert_historical_scope(historical_delta, current_paths | unrelated_future_paths)
    with pytest.raises(AssertionError):
        assert_historical_scope(
            historical_delta,
            current_paths
            | {"src/pastila_scout/desktop_v1/unexpected_future_module.py"},
        )
    with pytest.raises(AssertionError):
        assert_historical_scope(
            historical_delta | {"src/pastila_scout/desktop_v1/unauthorized.py"},
            current_paths,
        )
    with pytest.raises(AssertionError):
        assert_historical_scope(historical_delta - {"pyproject.toml"}, current_paths)
