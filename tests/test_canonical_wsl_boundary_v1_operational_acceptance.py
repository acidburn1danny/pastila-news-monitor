"""Infrastructure-only acceptance contract for the canonical WSL boundary.

These tests never load a tokenizer or model. Machine-state-dependent live
observations are recorded separately from this deterministic contract.
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from pastila_scout.wsl_execution_v1 import (
    WslExecutionBoundaryV1,
    WslExecutionFailureCodeV1,
    WslExecutionProfileV1,
    canonical_receipt_bytes_v1,
    windows_path_to_wsl_v1,
)
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1


ROOT = Path(__file__).resolve().parents[1]


def _boundary(executable: str = "/usr/bin/printf") -> WslExecutionBoundaryV1:
    return WslExecutionBoundaryV1(
        WslExecutionProfileV1(
            profile_id="operational-acceptance-v1",
            distribution="Ubuntu-24.04",
            executable=executable,
        )
    )


def _invocation(boundary: WslExecutionBoundaryV1, marker: str = "case"):
    return boundary.build_invocation(
        consumer_id="wsl-operational-acceptance",
        authority_reference=f"transport-only:{marker}",
        arguments=(marker,),
    )


def test_cold_start_and_post_sleep_do_not_depend_on_cached_boundary_state(monkeypatch):
    calls: list[tuple[str, ...]] = []

    def run(command, **_kwargs):
        calls.append(tuple(command))
        return subprocess.CompletedProcess(command, 0, f"ok:{len(calls)}", "")

    monkeypatch.setattr(subprocess, "run", run)
    cold_boundary = _boundary()
    first = cold_boundary.execute(_invocation(cold_boundary, "cold"), timeout_seconds=5)
    resumed_boundary = _boundary()
    second = resumed_boundary.execute(_invocation(resumed_boundary, "resume"), timeout_seconds=5)
    assert first.succeeded and second.succeeded
    assert len(calls) == 2
    assert calls[0][-1] == "cold" and calls[1][-1] == "resume"


@pytest.mark.parametrize(
    ("stderr", "reason"),
    [
        ("Wsl/Service/E_ACCESSDENIED", WslExecutionFailureCodeV1.ACCESS_DENIED),
        (
            "W\x00s\x00l\x00/\x00S\x00e\x00r\x00v\x00i\x00c\x00e\x00/\x00"
            "E\x00_\x00A\x00C\x00C\x00E\x00S\x00S\x00D\x00E\x00N\x00I\x00E\x00D",
            WslExecutionFailureCodeV1.ACCESS_DENIED,
        ),
        ("Wsl/Service/WSL_E_DISTRO_NOT_FOUND", WslExecutionFailureCodeV1.DISTRIBUTION_UNAVAILABLE),
        ("execvpe(/missing): No such file or directory", WslExecutionFailureCodeV1.EXECUTABLE_UNAVAILABLE),
        ("transport unhealthy", WslExecutionFailureCodeV1.NONZERO_EXIT),
    ],
)
def test_unavailable_unhealthy_distribution_and_dependency_fail_closed(
    monkeypatch, stderr, reason
):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 1, "", stderr),
    )
    profile = _boundary("/missing").profile
    boundary = WslExecutionBoundaryV1_1(profile)
    result = boundary.execute(_invocation(boundary), timeout_seconds=5)
    assert not result.succeeded
    assert result.receipt.failure_code is reason
    assert result.receipt.return_code == 1


def test_v1_1_classifies_utf16_wsl_service_code_from_stdout(monkeypatch):
    diagnostic = (
        "E\x00r\x00r\x00o\x00r\x00 \x00c\x00o\x00d\x00e\x00:\x00 \x00"
        "W\x00s\x00l\x00/\x00S\x00e\x00r\x00v\x00i\x00c\x00e\x00/\x00"
        "W\x00S\x00L\x00_\x00E\x00_\x00D\x00I\x00S\x00T\x00R\x00O\x00_\x00"
        "N\x00O\x00T\x00_\x00F\x00O\x00U\x00N\x00D\x00"
    )
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 1, diagnostic, ""),
    )
    profile = _boundary().profile
    boundary = WslExecutionBoundaryV1_1(profile)
    result = boundary.execute(_invocation(boundary), timeout_seconds=5)
    assert result.receipt.failure_code is WslExecutionFailureCodeV1.DISTRIBUTION_UNAVAILABLE
    assert result.stdout == diagnostic


def test_paths_filenames_and_arguments_preserve_spaces_and_romanian_unicode():
    windows = Path(r"C:\Proiecte Știri\fișier țintă.json")
    mapped = windows_path_to_wsl_v1(windows)
    assert mapped == "/mnt/c/Proiecte Știri/fișier țintă.json"
    boundary = _boundary()
    invocation = boundary.build_invocation(
        consumer_id="wsl-operational-acceptance",
        authority_reference="transport-only:path-unicode",
        arguments=(mapped, "știre cu spații", "--literal=$()"),
    )
    assert invocation.command[-3:] == (mapped, "știre cu spații", "--literal=$()")
    assert not any(part in {"sh", "bash", "-c", "-lc"} for part in invocation.command)


def test_hidden_execution_timeout_and_no_silent_retry(monkeypatch):
    calls = []

    def timeout(*args, **kwargs):
        calls.append((args, kwargs))
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", timeout)
    boundary = _boundary("/usr/bin/sleep")
    result = boundary.execute(_invocation(boundary, "30"), timeout_seconds=0.01)
    assert result.receipt.failure_code is WslExecutionFailureCodeV1.TIMEOUT
    assert result.receipt.timed_out is True
    assert len(calls) == 1
    assert calls[0][1]["creationflags"] == getattr(subprocess, "CREATE_NO_WINDOW", 0)


def test_durable_process_has_explicit_caller_owned_cancellation(monkeypatch):
    class Process:
        stdout = object()
        stderr = object()
        terminated = False

        def terminate(self):
            self.terminated = True

    process = Process()
    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: process)
    boundary = _boundary("/usr/bin/sleep")
    spawned = boundary.spawn(_invocation(boundary, "30"))
    assert not process.terminated
    spawned.process.terminate()
    assert process.terminated
    assert not hasattr(boundary, "cancel")


def test_concurrent_consumers_have_independent_commands_and_receipts(monkeypatch):
    def run(command, **_kwargs):
        marker = command[-1]
        return subprocess.CompletedProcess(command, 0, marker, "")

    monkeypatch.setattr(subprocess, "run", run)
    boundary = _boundary()

    def execute(index: int):
        invocation = _invocation(boundary, f"concurrent-{index}")
        return invocation, boundary.execute(invocation, timeout_seconds=5)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(execute, range(8)))
    assert len({invocation.command_identity for invocation, _ in results}) == 8
    assert all(result.succeeded for _, result in results)
    assert [result.stdout for _, result in results] == [f"concurrent-{i}" for i in range(8)]


def test_diagnostics_are_deterministic_and_do_not_confer_authority(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda command, **_kwargs: subprocess.CompletedProcess(command, 1, "out", "transport unhealthy"),
    )
    boundary = _boundary()
    result = boundary.execute(_invocation(boundary, "diagnostic"), timeout_seconds=5)
    receipt = json.loads(canonical_receipt_bytes_v1(result.receipt))
    assert receipt["stdout_sha256"] == hashlib.sha256(b"out").hexdigest()
    assert receipt["stderr_sha256"] == hashlib.sha256(b"transport unhealthy").hexdigest()
    assert receipt["failure_code"] == "WSL_PROCESS_NONZERO_EXIT"
    assert not ({"eligible", "admitted", "prompt", "model"} & receipt.keys())


def test_source_and_packaged_import_surfaces_are_equivalent():
    package_init = (ROOT / "src/pastila_scout/wsl_execution_v1/__init__.py").read_text("utf-8")
    spec = (ROOT / "packaging/pyinstaller/PastilaScout.spec").read_text("utf-8")
    for module in ("pastila_scout.wsl_execution_v1", "pastila_scout.wsl_execution_v1.boundary"):
        assert f'"{module}"' in spec
    for public_name in (
        "WslExecutionBoundaryV1",
        "WslExecutionFailureCodeV1",
        "canonical_model_profile_v1",
        "windows_path_to_wsl_v1",
    ):
        assert public_name in package_init


def test_pack_does_not_change_grandfathered_launcher_allowlist():
    governance = (ROOT / "tests/test_wsl_execution_boundary_governance_v1.py").read_text("utf-8")
    assert governance.count('"semantic_admission_v2/') == 16
