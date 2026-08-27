"""Frozen identity and local execution boundary for Core V1.1 Experimental."""

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

DISPLAY_NAME = "PastilaAcida Editor Core V1.1 Experimental"
MODEL_ID = "pastila-editor-core-v1.1-experimental"
SYSTEM_PROMPT_ID = "PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1"
SYSTEM_PROMPT_SHA256 = (
    "9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc"
)
BASE_PATH = "/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142"
ADAPTER_PATH = "/home/pastila/PastilaAcida-Model-Lab/experimental-0.3/runs/pastila-editor-core-v1-1-targeted-20260820-001/checkpoint-final/adapter"
VENV_PYTHON = (
    "/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/.venv/bin/python"
)
_PROMPT_RELATIVE = Path(
    ".experimental-0-3-editor-core-v1-architecture-prompt-first-training-plan-v1-evidence"
) / "PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1.txt"


def is_experimental_core_v1_1(model_identifier: str) -> bool:
    """Return whether a configured model is the exact experimental candidate."""
    return model_identifier == MODEL_ID


def load_frozen_system_prompt(*, project_root: Path) -> str:
    """Load and verify the immutable local prompt authority."""
    prompt = (project_root / _PROMPT_RELATIVE).read_bytes()
    if hashlib.sha256(prompt).hexdigest() != SYSTEM_PROMPT_SHA256:
        raise RuntimeError("Core V1.1 system prompt authority mismatch")
    return prompt.decode("utf-8", errors="strict")


class ExperimentalCoreV11Executor:
    """Execute one frozen local Core request through the validated WSL runtime."""

    def __init__(self, *, project_root: Path,
                 wsl_boundary: WslExecutionBoundaryV1_1 | None = None) -> None:
        self._project_root = project_root.resolve(strict=True)
        self._wsl_boundary = wsl_boundary or WslExecutionBoundaryV1_1(
            canonical_model_profile_v1())
        load_frozen_system_prompt(project_root=self._project_root)

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        authority = ProviderExecutionRequestV2.model_validate(
            request.model_dump(mode="python", warnings=False), strict=True
        )
        if authority.context.cancellation.cancellation_requested:
            return _failure(authority, ExecutionOutcomeV2.CANCELLED, "cancelled")
        try:
            output = self._invoke(authority)
            projection = ProviderResultProjectionV2(
                status=(
                    ProviderResultStatusV2.SUCCESS
                    if output["terminal_eos"]
                    else ProviderResultStatusV2.PARTIAL
                ),
                outputs=(
                    ProviderOutputInputV2(
                        source_request_reference=authority.request_envelope.request_units[0].source_request_reference,
                        ordinal=0,
                        generated_text=output["output"],
                        finish_reason=(
                            ProviderFinishReasonV2.COMPLETED
                            if output["terminal_eos"]
                            else ProviderFinishReasonV2.LENGTH
                        ),
                    ),
                ),
                failure_code=(None if output["terminal_eos"] else "core-v1-1-finish-length"),
            )
            return ProviderExecutionResultV2(
                request_id=authority.context.request_id,
                provider_id=authority.provider.provider_id,
                request_envelope_identity=authority.request_envelope.identity,
                outcome=ExecutionOutcomeV2.COMPLETED,
                finished_at=datetime.now(UTC),
                provider_result=projection,
            )
        except Exception:  # noqa: BLE001 - local runtime failures are isolated
            return _failure(
                authority,
                ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE,
                "experimental-core-v1-1-local-execution-failure",
            )

    def _invoke(self, authority: ProviderExecutionRequestV2) -> dict[str, object]:
        if len(authority.request_envelope.request_units) != 1:
            raise ValueError("Core V1.1 requires exactly one request unit")
        unit = authority.request_envelope.request_units[0]
        prompt = "\n\n".join(message.content for message in unit.messages)
        payload = {
            "prompt": prompt,
            "max_new_tokens": authority.request_envelope.generation.max_output_tokens,
        }
        runner = (
            self._project_root
            / "src"
            / "pastila_scout"
            / "experimental_core_v1_1_runner.py"
        )
        if not runner.is_file():
            raise FileNotFoundError("Core V1.1 local runner is unavailable")
        with tempfile.TemporaryDirectory(prefix="pastila-core-v1-1-") as directory:
            root = Path(directory)
            request_path, response_path = root / "request.json", root / "response.json"
            request_path.write_text(json.dumps(payload, ensure_ascii=False), "utf-8")
            wsl_request = _wsl_path(request_path)
            wsl_response = _wsl_path(response_path)
            wsl_runner = _wsl_path(runner)
            wsl_prompt = _wsl_path(self._project_root / _PROMPT_RELATIVE)
            invocation = self._wsl_boundary.build_invocation(
                consumer_id="editor-core-v1.1",
                authority_reference=authority.request_envelope.identity,
                arguments=(wsl_runner, wsl_request, wsl_response, wsl_prompt),
            )
            completed = self._wsl_boundary.execute(
                invocation, timeout_seconds=authority.timeout_policy.timeout_seconds)
            if completed.returncode != 0 or not response_path.is_file():
                raise RuntimeError("Core V1.1 local runner failed")
            result = json.loads(response_path.read_text("utf-8"))
            if set(result) != {"output", "terminal_eos"} or not result["output"]:
                raise ValueError("Core V1.1 returned an invalid response")
            return result


def _wsl_path(path: Path) -> str:
    """Compatibility wrapper around the canonical pure path mapper."""
    return windows_path_to_wsl_v1(path)


def _failure(request, outcome, code):
    return ProviderExecutionResultV2(
        request_id=request.context.request_id,
        provider_id=request.provider.provider_id,
        request_envelope_identity=request.request_envelope.identity,
        outcome=outcome,
        finished_at=datetime.now(UTC),
        failure_code=code,
        failure_message="PastilaAcida Editor Core V1.1 Experimental failed locally.",
    )


__all__ = (
    "ADAPTER_PATH",
    "BASE_PATH",
    "DISPLAY_NAME",
    "MODEL_ID",
    "SYSTEM_PROMPT_ID",
    "SYSTEM_PROMPT_SHA256",
    "ExperimentalCoreV11Executor",
    "is_experimental_core_v1_1",
    "load_frozen_system_prompt",
)
