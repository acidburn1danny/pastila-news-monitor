"""Canonical transport-only WSL execution boundary for Pastila Scout.

The boundary owns Windows/WSL transport mechanics.  It intentionally does not
own prompts, model or adapter selection, request schemas, semantic decisions,
retry policy, output selection, or application authority.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path, PureWindowsPath
from typing import Mapping, Sequence


CANONICAL_DISTRIBUTION = "Ubuntu-24.04"
CANONICAL_MODEL_PYTHON = (
    "/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/.venv/bin/python"
)
CANONICAL_PYDANTIC_BRIDGE = (
    "/mnt/c/Projects/pastila-news-monitor/.zero-inference-dependency-bridge/"
    "pydantic-2.13.4-linux:/mnt/c/Projects/pastila-news-monitor/src"
)
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
_SAFE_ENV = re.compile(r"^[A-Z_][A-Z0-9_]{0,63}$")


class WslExecutionFailureCodeV1(StrEnum):
    DISTRIBUTION_UNAVAILABLE = "WSL_DISTRIBUTION_UNAVAILABLE"
    EXECUTABLE_UNAVAILABLE = "WSL_EXECUTABLE_UNAVAILABLE"
    ACCESS_DENIED = "WSL_ACCESS_DENIED"
    TIMEOUT = "WSL_EXECUTION_TIMEOUT"
    LAUNCH_FAILURE = "WSL_PROCESS_LAUNCH_FAILURE"
    NONZERO_EXIT = "WSL_PROCESS_NONZERO_EXIT"


@dataclass(frozen=True, slots=True)
class WslExecutionProfileV1:
    profile_id: str
    distribution: str
    executable: str
    environment: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not _SAFE_ID.fullmatch(self.profile_id):
            raise ValueError("WSL_PROFILE_ID_INVALID")
        if not _SAFE_ID.fullmatch(self.distribution):
            raise ValueError("WSL_DISTRIBUTION_INVALID")
        if not self.executable.startswith("/") or "\x00" in self.executable:
            raise ValueError("WSL_EXECUTABLE_INVALID")
        names = [name for name, _ in self.environment]
        if len(names) != len(set(names)) or any(
            not _SAFE_ENV.fullmatch(name) or "\x00" in value
            for name, value in self.environment
        ):
            raise ValueError("WSL_ENVIRONMENT_INVALID")

    @property
    def identity(self) -> str:
        material = [
            "PASTILA_CANONICAL_WSL_EXECUTION_PROFILE_V1",
            self.profile_id,
            self.distribution,
            self.executable,
            *(f"{name}={value}" for name, value in self.environment),
        ]
        return hashlib.sha256("\n".join(material).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class WslInvocationV1:
    consumer_id: str
    authority_reference: str
    profile_identity: str
    command: tuple[str, ...]
    command_identity: str


@dataclass(frozen=True, slots=True)
class WslExecutionReceiptV1:
    schema_name: str
    schema_version: str
    consumer_id: str
    authority_reference: str
    profile_identity: str
    command_identity: str
    launch_attempted: bool
    return_code: int | None
    timed_out: bool
    elapsed_ms: float
    stdout_sha256: str
    stderr_sha256: str
    failure_code: WslExecutionFailureCodeV1 | None


@dataclass(frozen=True, slots=True)
class WslExecutionResultV1:
    return_code: int | None
    stdout: str
    stderr: str
    receipt: WslExecutionReceiptV1

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0 and self.receipt.failure_code is None


@dataclass(frozen=True, slots=True)
class WslSpawnedProcessV1:
    """A launched process whose lifecycle remains explicitly caller-owned."""
    invocation: WslInvocationV1
    process: subprocess.Popen[str]
    started_monotonic: float


class WslExecutionBoundaryV1:
    """Build and execute exactly one no-shell WSL process; never retry."""

    def __init__(self, profile: WslExecutionProfileV1) -> None:
        self.profile = profile

    def build_invocation(
        self,
        *,
        consumer_id: str,
        authority_reference: str,
        arguments: Sequence[str],
        environment_overrides: Mapping[str, str] | None = None,
    ) -> WslInvocationV1:
        if not _SAFE_ID.fullmatch(consumer_id):
            raise ValueError("WSL_CONSUMER_ID_INVALID")
        if not authority_reference or len(authority_reference) > 500 or "\x00" in authority_reference:
            raise ValueError("WSL_AUTHORITY_REFERENCE_INVALID")
        if any(type(item) is not str or "\x00" in item for item in arguments):
            raise ValueError("WSL_ARGUMENT_INVALID")
        environment = dict(self.profile.environment)
        for name, value in (environment_overrides or {}).items():
            if not _SAFE_ENV.fullmatch(name) or type(value) is not str or "\x00" in value:
                raise ValueError("WSL_ENVIRONMENT_OVERRIDE_INVALID")
            environment[name] = value
        command = ["wsl.exe", "-d", self.profile.distribution, "--"]
        if environment:
            command.append("env")
            command.extend(f"{name}={environment[name]}" for name in sorted(environment))
        command.append(self.profile.executable)
        command.extend(arguments)
        command_tuple = tuple(command)
        command_identity = hashlib.sha256(
            json.dumps(command_tuple, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest()
        return WslInvocationV1(
            consumer_id=consumer_id,
            authority_reference=authority_reference,
            profile_identity=self.profile.identity,
            command=command_tuple,
            command_identity=command_identity,
        )

    def execute(self, invocation: WslInvocationV1, *, timeout_seconds: float) -> WslExecutionResultV1:
        if invocation.profile_identity != self.profile.identity:
            raise ValueError("WSL_INVOCATION_PROFILE_DRIFT")
        if type(timeout_seconds) not in {int, float} or not 0 < timeout_seconds <= 3600:
            raise ValueError("WSL_TIMEOUT_INVALID")
        started = time.perf_counter()
        try:
            completed = subprocess.run(
                invocation.command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            stdout, stderr = completed.stdout or "", completed.stderr or ""
            failure = None if completed.returncode == 0 else _classify_failure(stderr)
            return _result(
                invocation, completed.returncode, stdout, stderr, False,
                (time.perf_counter() - started) * 1000, failure,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = _coerce_output(exc.stdout)
            stderr = _coerce_output(exc.stderr)
            return _result(
                invocation, None, stdout, stderr, True,
                (time.perf_counter() - started) * 1000,
                WslExecutionFailureCodeV1.TIMEOUT,
            )
        except OSError as exc:
            return _result(
                invocation, None, "", str(exc), False,
                (time.perf_counter() - started) * 1000,
                WslExecutionFailureCodeV1.LAUNCH_FAILURE,
            )

    def spawn(self, invocation: WslInvocationV1) -> WslSpawnedProcessV1:
        """Launch once for durable caller-owned lifecycle/heartbeat handling."""
        if invocation.profile_identity != self.profile.identity:
            raise ValueError("WSL_INVOCATION_PROFILE_DRIFT")
        process = subprocess.Popen(
            invocation.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return WslSpawnedProcessV1(invocation, process, time.perf_counter())


def windows_path_to_wsl_v1(path: Path | str) -> str:
    """Convert an absolute drive path without launching WSL or consulting state."""
    windows_path = PureWindowsPath(path)
    drive = windows_path.drive
    if not windows_path.is_absolute() or len(drive) != 2 or drive[1] != ":":
        raise ValueError("WSL_PATH_REQUIRES_ABSOLUTE_WINDOWS_DRIVE")
    if any(part in {".", ".."} for part in windows_path.parts[1:]):
        raise ValueError("WSL_PATH_TRAVERSAL_FORBIDDEN")
    return f"/mnt/{drive[0].lower()}/" + "/".join(windows_path.parts[1:])


def canonical_model_profile_v1(*, with_pydantic_bridge: bool = False) -> WslExecutionProfileV1:
    environment = (("PYTHONPATH", CANONICAL_PYDANTIC_BRIDGE),) if with_pydantic_bridge else ()
    suffix = "-pydantic-bridge" if with_pydantic_bridge else ""
    return WslExecutionProfileV1(
        profile_id=f"pastila-model-python-v1{suffix}",
        distribution=CANONICAL_DISTRIBUTION,
        executable=CANONICAL_MODEL_PYTHON,
        environment=environment,
    )


def canonical_receipt_bytes_v1(receipt: WslExecutionReceiptV1) -> bytes:
    value = {
        "schema_name": receipt.schema_name,
        "schema_version": receipt.schema_version,
        "consumer_id": receipt.consumer_id,
        "authority_reference": receipt.authority_reference,
        "profile_identity": receipt.profile_identity,
        "command_identity": receipt.command_identity,
        "launch_attempted": receipt.launch_attempted,
        "return_code": receipt.return_code,
        "timed_out": receipt.timed_out,
        "elapsed_ms": receipt.elapsed_ms,
        "stdout_sha256": receipt.stdout_sha256,
        "stderr_sha256": receipt.stderr_sha256,
        "failure_code": receipt.failure_code.value if receipt.failure_code else None,
    }
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def _result(invocation, return_code, stdout, stderr, timed_out, elapsed_ms, failure):
    receipt = WslExecutionReceiptV1(
        schema_name="pastila-canonical-wsl-execution-receipt",
        schema_version="1.0.0",
        consumer_id=invocation.consumer_id,
        authority_reference=invocation.authority_reference,
        profile_identity=invocation.profile_identity,
        command_identity=invocation.command_identity,
        launch_attempted=True,
        return_code=return_code,
        timed_out=timed_out,
        elapsed_ms=elapsed_ms,
        stdout_sha256=hashlib.sha256(stdout.encode()).hexdigest(),
        stderr_sha256=hashlib.sha256(stderr.encode()).hexdigest(),
        failure_code=failure,
    )
    return WslExecutionResultV1(return_code, stdout, stderr, receipt)


def _classify_failure(stderr: str) -> WslExecutionFailureCodeV1:
    lowered = stderr.lower()
    if "wsl_e_distro_not_found" in lowered or "no distribution" in lowered:
        return WslExecutionFailureCodeV1.DISTRIBUTION_UNAVAILABLE
    if "e_accessdenied" in lowered or "access is denied" in lowered:
        return WslExecutionFailureCodeV1.ACCESS_DENIED
    if "no such file or directory" in lowered:
        return WslExecutionFailureCodeV1.EXECUTABLE_UNAVAILABLE
    return WslExecutionFailureCodeV1.NONZERO_EXIT


def _coerce_output(value) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)


__all__ = (
    "CANONICAL_DISTRIBUTION", "CANONICAL_MODEL_PYTHON", "CANONICAL_PYDANTIC_BRIDGE",
    "WslExecutionBoundaryV1", "WslExecutionFailureCodeV1", "WslExecutionProfileV1",
    "WslExecutionReceiptV1", "WslExecutionResultV1", "WslInvocationV1",
    "WslSpawnedProcessV1",
    "canonical_model_profile_v1", "canonical_receipt_bytes_v1", "windows_path_to_wsl_v1",
)
