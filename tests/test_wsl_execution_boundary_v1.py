import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from pastila_scout.wsl_execution_v1 import (
    CANONICAL_DISTRIBUTION,
    WslExecutionBoundaryV1,
    WslExecutionFailureCodeV1,
    WslExecutionProfileV1,
    canonical_model_profile_v1,
    canonical_receipt_bytes_v1,
    windows_path_to_wsl_v1,
)


def test_path_mapping_is_pure_case_normalized_and_space_safe():
    assert windows_path_to_wsl_v1(Path(r"C:\Projects\Pastila Scout\x.json")) == (
        "/mnt/c/Projects/Pastila Scout/x.json"
    )
    assert windows_path_to_wsl_v1(Path(r"d:\Data\x")) == "/mnt/d/Data/x"
    with pytest.raises(ValueError, match="ABSOLUTE_WINDOWS_DRIVE"):
        windows_path_to_wsl_v1(Path("relative.json"))


def test_profile_and_command_identity_are_deterministic_and_no_shell_is_used():
    profile = canonical_model_profile_v1(with_pydantic_bridge=True)
    boundary = WslExecutionBoundaryV1(profile)
    left = boundary.build_invocation(
        consumer_id="editor-core-v1.2",
        authority_reference="request-envelope:abc",
        arguments=("/mnt/c/runner.py", "/mnt/c/request.json"),
    )
    right = boundary.build_invocation(
        consumer_id="editor-core-v1.2",
        authority_reference="request-envelope:abc",
        arguments=("/mnt/c/runner.py", "/mnt/c/request.json"),
    )
    assert left == right
    assert left.command[:5] == ("wsl.exe", "-d", CANONICAL_DISTRIBUTION, "--", "env")
    assert "PYTHONPATH=" in left.command[5]
    assert not any(item in {"bash", "sh", "-c", "-lc"} for item in left.command)


def test_environment_is_sorted_and_rejects_invalid_names_or_nul():
    boundary = WslExecutionBoundaryV1(canonical_model_profile_v1())
    invocation = boundary.build_invocation(
        consumer_id="diagnostic",
        authority_reference="audit:v1",
        arguments=("/runner.py",),
        environment_overrides={"ZED": "2", "ALPHA": "1"},
    )
    assert invocation.command[5:7] == ("ALPHA=1", "ZED=2")
    with pytest.raises(ValueError, match="ENVIRONMENT_OVERRIDE"):
        boundary.build_invocation(
            consumer_id="diagnostic", authority_reference="audit:v1",
            arguments=("/runner.py",), environment_overrides={"bad-name": "x"},
        )
    with pytest.raises(ValueError, match="ARGUMENT"):
        boundary.build_invocation(
            consumer_id="diagnostic", authority_reference="audit:v1",
            arguments=("bad\x00argument",),
        )


def test_success_receipt_hashes_outputs_and_preserves_opaque_authority(monkeypatch):
    completed = subprocess.CompletedProcess(("ignored",), 0, stdout="ok", stderr="")
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)) or completed)
    boundary = WslExecutionBoundaryV1(canonical_model_profile_v1())
    invocation = boundary.build_invocation(
        consumer_id="scout-local-model", authority_reference="governed-request:42",
        arguments=("/runner.py",),
    )
    result = boundary.execute(invocation, timeout_seconds=30)
    assert result.succeeded
    assert result.receipt.authority_reference == "governed-request:42"
    assert result.receipt.stdout_sha256 == hashlib.sha256(b"ok").hexdigest()
    assert calls[0][0][0] == invocation.command
    assert calls[0][1]["encoding"] == "utf-8"
    assert calls[0][1]["errors"] == "replace"
    assert calls[0][1]["creationflags"] == getattr(subprocess, "CREATE_NO_WINDOW", 0)
    value = json.loads(canonical_receipt_bytes_v1(result.receipt))
    assert value["failure_code"] is None


@pytest.mark.parametrize(
    ("stderr", "expected"),
    [
        ("WSL_E_DISTRO_NOT_FOUND", WslExecutionFailureCodeV1.DISTRIBUTION_UNAVAILABLE),
        ("Wsl/Service/E_ACCESSDENIED", WslExecutionFailureCodeV1.ACCESS_DENIED),
        ("No such file or directory", WslExecutionFailureCodeV1.EXECUTABLE_UNAVAILABLE),
        ("runner failed", WslExecutionFailureCodeV1.NONZERO_EXIT),
    ],
)
def test_nonzero_failures_are_typed_without_retry(monkeypatch, stderr, expected):
    calls = []
    monkeypatch.setattr(
        subprocess, "run",
        lambda *args, **kwargs: calls.append(1) or subprocess.CompletedProcess(
            ("ignored",), 1, stdout="", stderr=stderr),
    )
    boundary = WslExecutionBoundaryV1(canonical_model_profile_v1())
    invocation = boundary.build_invocation(
        consumer_id="chief-editor-eval", authority_reference="case:01",
        arguments=("/runner.py",),
    )
    result = boundary.execute(invocation, timeout_seconds=30)
    assert result.receipt.failure_code is expected
    assert len(calls) == 1


def test_timeout_is_typed_and_never_retried(monkeypatch):
    calls = []
    def timeout(*args, **kwargs):
        calls.append(1)
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], output=b"partial")
    monkeypatch.setattr(subprocess, "run", timeout)
    boundary = WslExecutionBoundaryV1(canonical_model_profile_v1())
    invocation = boundary.build_invocation(
        consumer_id="semantic-admission", authority_reference="run:4",
        arguments=("/runner.py",),
    )
    result = boundary.execute(invocation, timeout_seconds=30)
    assert result.receipt.failure_code is WslExecutionFailureCodeV1.TIMEOUT
    assert result.stdout == "partial"
    assert len(calls) == 1


def test_durable_spawn_keeps_lifecycle_policy_with_caller(monkeypatch):
    sentinel = object()
    calls = []
    monkeypatch.setattr(
        subprocess, "Popen",
        lambda *args, **kwargs: calls.append((args, kwargs)) or sentinel,
    )
    boundary = WslExecutionBoundaryV1(canonical_model_profile_v1())
    invocation = boundary.build_invocation(
        consumer_id="governed-probe", authority_reference="probe-binding:v1",
        arguments=("/runner.py",),
    )
    spawned = boundary.spawn(invocation)
    assert spawned.process is sentinel
    assert spawned.invocation is invocation
    assert calls[0][1]["stdout"] is subprocess.PIPE
    assert calls[0][1]["stderr"] is subprocess.PIPE
    assert not hasattr(boundary, "retry")


def test_boundary_has_no_semantic_model_prompt_or_retry_configuration():
    fields = set(WslExecutionProfileV1.__dataclass_fields__)
    assert fields == {"profile_id", "distribution", "executable", "environment"}
    source = (Path(__file__).resolve().parents[1] / "src" / "pastila_scout" /
              "wsl_execution_v1" / "boundary.py").read_text("utf-8")
    for forbidden in ("system_prompt", "adapter_path", "temperature", "top_p", "retry("):
        assert forbidden not in source.lower()
