"""V1.1 candidate: classify UTF-16/NUL-interleaved WSL service errors.

Command construction, successful execution, captured output, receipt schema,
and caller-owned durable lifecycle are inherited unchanged from frozen V1.
This candidate is not an active-application binding.
"""
from __future__ import annotations

import subprocess
import time

from pastila_scout.wsl_execution_v1.boundary import (
    WslExecutionBoundaryV1,
    WslExecutionFailureCodeV1,
    WslExecutionResultV1,
    WslInvocationV1,
    _coerce_output,
    _result,
)


class WslExecutionBoundaryV1_1(WslExecutionBoundaryV1):
    """Frozen V1 transport with diagnostic-only service-error normalization."""

    def execute(
        self, invocation: WslInvocationV1, *, timeout_seconds: float
    ) -> WslExecutionResultV1:
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
            failure = (
                None
                if completed.returncode == 0
                else _classify_failure_v1_1(stdout, stderr)
            )
            return _result(
                invocation,
                completed.returncode,
                stdout,
                stderr,
                False,
                (time.perf_counter() - started) * 1000,
                failure,
            )
        except subprocess.TimeoutExpired as exc:
            return _result(
                invocation,
                None,
                _coerce_output(exc.stdout),
                _coerce_output(exc.stderr),
                True,
                (time.perf_counter() - started) * 1000,
                WslExecutionFailureCodeV1.TIMEOUT,
            )
        except OSError as exc:
            return _result(
                invocation,
                None,
                "",
                str(exc),
                False,
                (time.perf_counter() - started) * 1000,
                WslExecutionFailureCodeV1.LAUNCH_FAILURE,
            )


def _classify_failure_v1_1(stdout: str, stderr: str) -> WslExecutionFailureCodeV1:
    # WSL service failures are Windows diagnostics and can arrive UTF-16/NUL
    # interleaved on either captured stream. Raw streams remain untouched in
    # the result and receipt; normalization is classification-only.
    lowered = f"{stdout}\n{stderr}".replace("\x00", "").lower()
    if "wsl_e_distro_not_found" in lowered or "no distribution" in lowered:
        return WslExecutionFailureCodeV1.DISTRIBUTION_UNAVAILABLE
    if "e_accessdenied" in lowered or "access is denied" in lowered:
        return WslExecutionFailureCodeV1.ACCESS_DENIED
    if "no such file or directory" in lowered:
        return WslExecutionFailureCodeV1.EXECUTABLE_UNAVAILABLE
    return WslExecutionFailureCodeV1.NONZERO_EXIT
