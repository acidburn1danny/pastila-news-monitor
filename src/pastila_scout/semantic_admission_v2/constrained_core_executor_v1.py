"""Evaluation-only executor boundary for the separate constrained Gate-F runner."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from pastila_scout.experimental_core_v1_2 import (
    _PROMPT_RELATIVE,
    VENV_PYTHON,
    ExperimentalCoreV12Executor,
    _wsl_path,
)

RUNNER_RELATIVE = Path(
    "src/pastila_scout/experimental_core_v1_2_gate_f_constrained_runner.py"
)
RUNNER_SHA256 = "17a1669d5ec145bfc2ef746890e4d6534670e94b069a3a7d6307bb8127bd2ac9"


class ConstrainedGateFCoreV12ExecutorV1(ExperimentalCoreV12Executor):
    """Not imported by production; one call and no fallback are caller-governed."""

    def __init__(self, *, project_root: Path, max_output_tokens: int) -> None:
        super().__init__(project_root=project_root, max_output_tokens=max_output_tokens)
        runner = self._project_root / RUNNER_RELATIVE
        if (
            not runner.is_file()
            or hashlib.sha256(runner.read_bytes()).hexdigest() != RUNNER_SHA256
        ):
            raise RuntimeError("constrained Gate-F runner identity drift")

    def _invoke(
        self, authority, trace_path: Path, trace: dict[str, object]
    ) -> dict[str, object]:
        if len(authority.request_envelope.request_units) != 1:
            raise ValueError("constrained Core V1.2 requires exactly one request unit")
        unit = authority.request_envelope.request_units[0]
        payload = {
            "prompt": "\n\n".join(message.content for message in unit.messages),
            "max_new_tokens": self._max_output_tokens,
        }
        runner = self._project_root / RUNNER_RELATIVE
        with tempfile.TemporaryDirectory(
            prefix="pastila-core-v1-2-gate-f-constrained-"
        ) as directory:
            root = Path(directory)
            request_path, response_path, runner_trace_path = (
                root / "request.json",
                root / "response.json",
                root / "runner-lifecycle.json",
            )
            request_path.write_text(
                json.dumps(payload, ensure_ascii=False), encoding="utf-8"
            )
            trace.update(
                runner_path=_wsl_path(runner),
                runner_launch_attempted=True,
                constraint_active=True,
            )
            self._write_trace(trace_path, trace)
            completed = subprocess.run(
                [
                    "wsl.exe",
                    "-d",
                    "Ubuntu-24.04",
                    "--",
                    VENV_PYTHON,
                    _wsl_path(runner),
                    _wsl_path(request_path),
                    _wsl_path(response_path),
                    _wsl_path(self._project_root / _PROMPT_RELATIVE),
                    _wsl_path(runner_trace_path),
                ],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=authority.timeout_policy.timeout_seconds,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if runner_trace_path.is_file():
                trace.update(json.loads(runner_trace_path.read_text(encoding="utf-8")))
            trace.update(
                stderr_tail=(completed.stderr or "")[-4000:],
                stdout_tail=(completed.stdout or "")[-4000:],
                response_received=response_path.is_file(),
            )
            self._write_trace(trace_path, trace)
            if completed.returncode != 0 or not response_path.is_file():
                raise RuntimeError("constrained Core V1.2 local runner failed")
            result = json.loads(response_path.read_text(encoding="utf-8"))
            if (
                set(result) != {"output", "terminal_eos", "constraint_active"}
                or result["constraint_active"] is not True
                or not result["output"]
            ):
                raise ValueError("constrained Core V1.2 returned an invalid response")
            trace["response_validation_passed"] = True
            self._write_trace(trace_path, trace)
            return {"output": result["output"], "terminal_eos": result["terminal_eos"]}


__all__ = ("RUNNER_SHA256", "ConstrainedGateFCoreV12ExecutorV1")
