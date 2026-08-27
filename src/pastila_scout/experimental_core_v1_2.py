"""Frozen identity and local execution boundary for Core V1.2 Experimental."""

from __future__ import annotations

import hashlib
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.provider_execution_v2 import (
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)
from pastila_scout.provider_v2 import (
    ProviderFinishReasonV2,
    ProviderOutputInputV2,
    ProviderResultProjectionV2,
    ProviderResultStatusV2,
)
from pastila_scout.wsl_execution_v1 import (
    canonical_model_profile_v1,
    windows_path_to_wsl_v1,
)
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

DISPLAY_NAME = "PastilaAcida Editor Core V1.2 Experimental"
MODEL_ID = "pastila-editor-core-v1.2-experimental"
SYSTEM_PROMPT_ID = "PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2"
SYSTEM_PROMPT_SHA256 = "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17"
BASE_PATH = "/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142"
ADAPTER_PATH = "/home/pastila/PastilaAcida-Model-Lab/experimental-0.3/runs/pastila-editor-core-v1-2-deontology-20260820-003/checkpoint-final/adapter"
VENV_PYTHON = "/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/.venv/bin/python"
_PROMPT_RELATIVE = Path(".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence") / "PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt"


def is_experimental_core_v1_2(model_identifier: str) -> bool:
    return model_identifier == MODEL_ID


def load_frozen_system_prompt(*, project_root: Path) -> str:
    prompt = (project_root / _PROMPT_RELATIVE).read_bytes()
    if hashlib.sha256(prompt).hexdigest() != SYSTEM_PROMPT_SHA256:
        raise RuntimeError("Core V1.2 system prompt authority mismatch")
    return prompt.decode("utf-8", errors="strict")


class ExperimentalCoreV12Executor:
    def __init__(self, *, project_root: Path, max_output_tokens: int,
                 wsl_boundary: WslExecutionBoundaryV1_1 | None = None) -> None:
        if type(max_output_tokens) is not int or max_output_tokens <= 0:
            raise ValueError("Core V1.2 max output tokens are invalid")
        self._project_root = project_root.resolve(strict=True)
        self._max_output_tokens = max_output_tokens
        self._wsl_boundary = wsl_boundary or WslExecutionBoundaryV1_1(
            canonical_model_profile_v1())
        load_frozen_system_prompt(project_root=self._project_root)

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        authority = ProviderExecutionRequestV2.model_validate(request.model_dump(mode="python", warnings=False), strict=True)
        trace_path = self._trace_path(authority.context.request_id)
        trace = {
            "executor_invoked": True,
            "executor_type": type(self).__name__,
            "inference_started": False,
            "inference_succeeded": False,
            "model_load_started": False,
            "model_load_succeeded": False,
            "response_received": False,
            "response_validation_passed": False,
            "runner_launch_attempted": False,
            "stderr_tail": "",
            "stdout_tail": "",
        }
        self._write_trace(trace_path, trace)
        if authority.context.cancellation.cancellation_requested:
            return _failure(authority, ExecutionOutcomeV2.CANCELLED, "cancelled")
        try:
            output = self._invoke(authority, trace_path, trace)
            projection = ProviderResultProjectionV2(
                status=ProviderResultStatusV2.SUCCESS if output["terminal_eos"] else ProviderResultStatusV2.PARTIAL,
                outputs=(ProviderOutputInputV2(source_request_reference=authority.request_envelope.request_units[0].source_request_reference, ordinal=0, generated_text=output["output"], finish_reason=ProviderFinishReasonV2.COMPLETED if output["terminal_eos"] else ProviderFinishReasonV2.LENGTH),),
                failure_code=None if output["terminal_eos"] else "core-v1-2-finish-length",
            )
            return ProviderExecutionResultV2(request_id=authority.context.request_id, provider_id=authority.provider.provider_id, request_envelope_identity=authority.request_envelope.identity, outcome=ExecutionOutcomeV2.COMPLETED, finished_at=datetime.now(UTC), provider_result=projection)
        except Exception as exc:  # noqa: BLE001 - local runtime failures are isolated
            trace.update(exception_type=type(exc).__name__, exception_message=str(exc)[:2000])
            self._write_trace(trace_path, trace)
            return _failure(authority, ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE, "experimental-core-v1-2-local-execution-failure")

    def _invoke(self, authority: ProviderExecutionRequestV2, trace_path: Path, trace: dict[str, object]) -> dict[str, object]:
        if len(authority.request_envelope.request_units) != 1:
            raise ValueError("Core V1.2 requires exactly one request unit")
        unit = authority.request_envelope.request_units[0]
        payload = {
            "prompt": "\n\n".join(message.content for message in unit.messages),
            "max_new_tokens": self._max_output_tokens,
        }
        runner = self._project_root / "src" / "pastila_scout" / "experimental_core_v1_2_runner.py"
        if not runner.is_file():
            raise FileNotFoundError("Core V1.2 local runner is unavailable")
        with tempfile.TemporaryDirectory(prefix="pastila-core-v1-2-") as directory:
            root = Path(directory); request_path, response_path = root / "request.json", root / "response.json"
            runner_trace_path = root / "runner-lifecycle.json"
            request_path.write_text(json.dumps(payload, ensure_ascii=False), "utf-8")
            runner_wsl_path = _wsl_path(runner)
            request_wsl_path = _wsl_path(request_path)
            response_wsl_path = _wsl_path(response_path)
            prompt_wsl_path = _wsl_path(self._project_root / _PROMPT_RELATIVE)
            runner_trace_wsl_path = _wsl_path(runner_trace_path)
            trace["runner_path"] = runner_wsl_path
            trace["runner_launch_attempted"] = True
            self._write_trace(trace_path, trace)
            invocation = self._wsl_boundary.build_invocation(
                consumer_id="editor-core-v1.2",
                authority_reference=authority.request_envelope.identity,
                arguments=(runner_wsl_path, request_wsl_path, response_wsl_path,
                           prompt_wsl_path, runner_trace_wsl_path),
            )
            completed = self._wsl_boundary.execute(
                invocation, timeout_seconds=authority.timeout_policy.timeout_seconds)
            trace["wsl_profile_identity"] = completed.receipt.profile_identity
            trace["wsl_command_identity"] = completed.receipt.command_identity
            trace["wsl_failure_code"] = (
                completed.receipt.failure_code.value
                if completed.receipt.failure_code else None)
            if runner_trace_path.is_file():
                trace.update(json.loads(runner_trace_path.read_text("utf-8")))
            trace["stderr_tail"] = (completed.stderr or "")[-4000:]
            trace["stdout_tail"] = (completed.stdout or "")[-4000:]
            trace["response_received"] = response_path.is_file()
            self._write_trace(trace_path, trace)
            if completed.returncode != 0 or not response_path.is_file():
                raise RuntimeError("Core V1.2 local runner failed")
            result = json.loads(response_path.read_text("utf-8"))
            if set(result) != {"output", "terminal_eos"} or not result["output"]:
                raise ValueError("Core V1.2 returned an invalid response")
            trace["response_validation_passed"] = True
            self._write_trace(trace_path, trace)
            return result

    def _trace_path(self, request_id: str) -> Path:
        digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
        root = self._project_root / "reports" / "editor-diagnostics" / "core-v1-2"
        root.mkdir(parents=True, exist_ok=True)
        return root / f"request-{digest}.json"

    @staticmethod
    def _write_trace(path: Path, trace: dict[str, object]) -> None:
        path.write_text(json.dumps(trace, ensure_ascii=False, indent=2, sort_keys=True) + "\n", "utf-8")


def _wsl_path(path: Path) -> str:
    """Compatibility alias for the canonical application-wide path mapper."""
    return windows_path_to_wsl_v1(path)


def _failure(request, outcome, code):
    return ProviderExecutionResultV2(request_id=request.context.request_id, provider_id=request.provider.provider_id, request_envelope_identity=request.request_envelope.identity, outcome=outcome, finished_at=datetime.now(UTC), failure_code=code, failure_message="PastilaAcida Editor Core V1.2 Experimental failed locally.")


__all__ = ("ADAPTER_PATH", "BASE_PATH", "DISPLAY_NAME", "MODEL_ID", "SYSTEM_PROMPT_ID", "SYSTEM_PROMPT_SHA256", "ExperimentalCoreV12Executor", "is_experimental_core_v1_2", "load_frozen_system_prompt")
