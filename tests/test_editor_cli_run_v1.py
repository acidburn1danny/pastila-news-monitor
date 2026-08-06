"""Focused verification for the opt-in Editor application CLI."""

from __future__ import annotations

import hashlib
import inspect
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_editor_application_contracts_v1 import request as application_request

from pastila_scout.cli import build_parser, main
from pastila_scout.editor_application_v1 import (
    EditorApplicationExitCodeV1,
    EditorApplicationStatusV1,
)
from pastila_scout.editor_cli_run_v1 import command

REQUIRED = (
    "--input",
    "input.json",
    "--selection-profile",
    "profile.json",
    "--episode-context",
    "context.json",
    "--generation-config",
    "generation.json",
    "--provider",
    "openai",
    "--model",
    "gpt-4.1-mini",
    "--timeout-seconds",
    "30",
    "--cancelled",
    "false",
    "--output",
    "output.json",
    "--overwrite-policy",
    "fail_if_exists",
)


class _Authority:
    def __init__(self, value: object) -> None:
        self.value = value

    def load(self, *, path: Path) -> object:
        assert type(path) is type(Path())
        return self.value


class _Result:
    def __init__(self, *, status, exit_code, failure=None) -> None:
        self.status = status
        self.exit_code = exit_code
        self.failure = failure


class _Coordinator:
    def __init__(self, result: object) -> None:
        self.result = result
        self.requests = []

    def execute(self, *, request: object) -> object:
        self.requests.append(request)
        return self.result


def _install_valid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, result: _Result
) -> tuple[object, _Coordinator]:
    source = application_request(tmp_path)
    coordinator = _Coordinator(result)
    monkeypatch.setattr(command, "_load_scout_input", lambda path: source.scout_input)
    monkeypatch.setattr(
        command,
        "EditorSelectionProfileAuthorityV1",
        lambda: _Authority(source.selection_profile),
    )
    monkeypatch.setattr(
        command,
        "EditorEpisodeContextAuthorityV1",
        lambda: _Authority(source.episode_context),
    )
    monkeypatch.setattr(
        command,
        "EditorApplicationGenerationConfigurationAuthorityV1",
        lambda: _Authority(source.generation_configuration),
    )
    monkeypatch.setattr(
        command, "_compose_editor_cli_application_v1", lambda: coordinator
    )
    monkeypatch.setattr(command, "EditorApplicationResultV1", _Result)
    return source, coordinator


def test_exact_package_api_and_composition_signature() -> None:
    import pastila_scout.editor_cli_run_v1 as package
    from pastila_scout.editor_cli_run_v1 import composition

    assert package.__all__ == ("run_editor_command",)
    assert tuple(inspect.signature(package.run_editor_command).parameters) == (
        "input_path",
        "selection_profile_path",
        "episode_context_path",
        "generation_config_path",
        "provider",
        "model",
        "timeout_seconds",
        "cancelled",
        "output_path",
        "overwrite_policy",
    )
    assert (
        tuple(
            inspect.signature(composition._compose_editor_cli_application_v1).parameters
        )
        == ()
    )


def test_exact_registration_and_argument_contract() -> None:
    parser = build_parser()
    choices = next(
        action for action in parser._actions if action.dest == "command"
    ).choices
    assert tuple(name for name in choices if name == "editor-run") == ("editor-run",)
    namespace = parser.parse_args(("editor-run", *REQUIRED))
    assert namespace.command == "editor-run"
    assert namespace.provider == "openai"
    assert namespace.model == "gpt-4.1-mini"
    assert namespace.timeout_seconds == 30.0
    assert namespace.cancelled == "false"
    assert namespace.overwrite_policy == "fail_if_exists"
    subparser = choices["editor-run"]
    editor_help = subparser.format_help()
    assert "--operation-reference" not in editor_help
    for forbidden in ("--temperature", "--top-p", "--seed", "--retry"):
        assert forbidden not in editor_help


@pytest.mark.parametrize(
    "arguments",
    (
        (),
        ("--unknown", "x"),
        (*REQUIRED, "extra"),
        (*REQUIRED[:-16], "invalid", *REQUIRED[-15:]),
    ),
)
def test_parse_failures_are_rejected(arguments: tuple[str, ...]) -> None:
    with pytest.raises(SystemExit) as captured:
        build_parser().parse_args(("editor-run", *arguments))
    assert captured.value.code == 2


@pytest.mark.parametrize("value", ("0", "-1", "nan", "inf", "-inf"))
def test_timeout_rejects_nonpositive_or_nonfinite(value: str) -> None:
    arguments = list(REQUIRED)
    arguments[arguments.index("30")] = value
    with pytest.raises(SystemExit) as captured:
        build_parser().parse_args(("editor-run", *arguments))
    assert captured.value.code == 2


def test_success_maps_exactly_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = _Result(
        status=EditorApplicationStatusV1.COMPLETED,
        exit_code=EditorApplicationExitCodeV1.COMPLETED,
    )
    source, coordinator = _install_valid(monkeypatch, tmp_path, result)
    assert main(("editor-run", *REQUIRED)) == 0
    assert len(coordinator.requests) == 1
    received = coordinator.requests[0]
    assert received.scout_input == source.scout_input
    assert received.selection_profile == source.selection_profile
    assert received.episode_context == source.episode_context
    assert received.generation_configuration == source.generation_configuration
    assert received.operation_reference == "editor-run-v1"
    assert received.cancellation.cancellation_requested is False
    output = capsys.readouterr()
    assert output.out == "Editor application completed.\n"
    assert output.err == ""


@pytest.mark.parametrize(
    "exit_code",
    tuple(item for item in EditorApplicationExitCodeV1 if item.value != 0),
)
def test_returned_failure_uses_public_message_and_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    exit_code: EditorApplicationExitCodeV1,
) -> None:
    result = _Result(
        status=EditorApplicationStatusV1.FAILED,
        exit_code=exit_code,
        failure=SimpleNamespace(safe_message="Editor application execution failed."),
    )
    _, coordinator = _install_valid(monkeypatch, tmp_path, result)
    assert main(("editor-run", *REQUIRED)) == exit_code.value
    assert len(coordinator.requests) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Editor application execution failed.\n"


def test_configuration_mismatch_prevents_composition(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = _Result(
        status=EditorApplicationStatusV1.COMPLETED,
        exit_code=EditorApplicationExitCodeV1.COMPLETED,
    )
    _, coordinator = _install_valid(monkeypatch, tmp_path, result)
    called = []
    monkeypatch.setattr(
        command, "_compose_editor_cli_application_v1", lambda: called.append(1)
    )
    arguments = list(REQUIRED)
    arguments[arguments.index("gpt-4.1-mini")] = "different-model"
    assert main(("editor-run", *arguments)) == 2
    assert called == []
    assert coordinator.requests == []
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Editor application configuration is invalid.\n"


def test_help_is_passive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        command,
        "_compose_editor_cli_application_v1",
        lambda: pytest.fail("composition during help"),
    )
    with pytest.raises(SystemExit) as captured:
        main(("editor-run", "--help"))
    assert captured.value.code == 0


def test_fresh_import_and_help_are_socket_passive() -> None:
    root = Path(__file__).resolve().parents[1]
    probe = (
        "import socket;"
        "socket.create_connection=lambda *a,**k:(_ for _ in ()).throw(AssertionError('network'));"
        "import pastila_scout.editor_cli_run_v1;"
        "from pastila_scout.cli import build_parser;"
        "build_parser().parse_args(['editor-run','--help'])"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "usage: pastila-scout editor-run" in completed.stdout
    assert completed.stderr == ""


def test_exact_revision_scope_and_frozen_specification() -> None:
    root = Path(__file__).resolve().parents[1]
    expected = {
        "src/pastila_scout/editor_cli_run_v1/__init__.py",
        "src/pastila_scout/editor_cli_run_v1/command.py",
        "src/pastila_scout/editor_cli_run_v1/composition.py",
        "src/pastila_scout/cli.py",
        "tests/test_editor_cli_run_v1.py",
        "tests/test_editor_application_runtime_composition_v1.py",
        "tests/test_editor_application_v1.py",
        "tests/test_editor_application_contracts_v1.py",
    }
    correction_digest = (
        "F08978E8A35EDC14A9F36D1207CDD44D7ECEB8961E23D98F2F8EEA9868FECCBF"
    )

    def names(*arguments: str) -> set[str]:
        return set(
            subprocess.run(
                ["git", *arguments],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
        )

    assert (
        subprocess.run(
            [
                "git",
                "rev-parse",
                "phase-4.3-editor-command-time-runtime-composition-r1-verified^{}",
            ],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        == "5c80d4edc402f661040035db11ad7d9785de1362"
    )
    assert names("diff", "--cached", "--name-only") == set()
    assert (
        names("diff", "--name-only")
        | names("ls-files", "--others", "--exclude-standard")
        == expected
    )
    test_bytes = (root / "tests/test_editor_cli_run_v1.py").read_bytes()
    normalized = test_bytes.replace(correction_digest.encode(), b"0" * 64)
    assert normalized != test_bytes
    assert hashlib.sha256(normalized).hexdigest().upper() == correction_digest
    specification = (
        root
        / "docs/editorial-application/EditorApplicationCompositionSpecificationV1.md"
    )
    assert hashlib.sha256(specification.read_bytes()).hexdigest().upper() == (
        "1742A84289B07A8D6CBD7D7A96F9E58F34A05EA090A6EEE6A1F212FB96068473"
    )
