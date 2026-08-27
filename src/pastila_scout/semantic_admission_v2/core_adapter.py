"""Evaluation-only Core V1.2 adapters for Semantic Admission V2."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from pastila_scout.application_request_authority_v1 import (
    ApplicationProviderRequestV1, ApplicationRequestAuthorityV1,
)
from pastila_scout.provider_execution_v2 import CancellationTokenV2, ExecutionOutcomeV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.provider_v2 import ProviderFinishReasonV2, ProviderResultStatusV2

from .models import GateIdV2

GATE_F_PROMPT_SHA256 = "1d0017a3058ee46c9774f9fa2138d5ea1bad50beb068d07f75a0de2699c192a4"
GATE_S_PROMPT_SHA256 = "ecd038c4bf430c38e18b5bc1c33ead418d856fb3fbbeeaf365e5a60c7319e82f"
GATE_F_EXECUTION_PROMPT_SHA256 = "59e31ee7cbfbaf025f63975adedf70bc5e72c64c3caf4fa65de905e3fc97f7cc"
GATE_S_EXECUTION_PROMPT_SHA256 = "982ff769eea1e37c3cb5d61fa1d9ca7e052826af260fcb9d6ad64dde868b6956"
SETTINGS_SHA256 = "283a42dcceb8c2946deae816c287c6470c23bfc4194ca6c29694ba21983969b8"
GATE_F_EVALUATOR_IDENTITY = "65566b6227ee8118af1e441b7fc1595c3fe4973b34a382db6cd8b47d61a8518c"
GATE_S_EVALUATOR_IDENTITY = "78b1ab76bb4a062f7aec986020fd4da7b460c4ab1f3d3790c5a3a2ef4d43c920"


class CoreV12SemanticEvaluatorAdapter:
    """One strict local provider call; no retry, repair, or selection."""

    def __init__(self, *, project_root: Path, executor, gate_id: GateIdV2) -> None:
        self._root = project_root.resolve(strict=True)
        self._executor = executor
        self.gate_id = gate_id
        settings_path = self._root / "docs" / "artifacts" / "semantic-admission-v2-evaluator-settings.json"
        if _sha(settings_path.read_bytes()) != SETTINGS_SHA256:
            raise RuntimeError("SAV2 evaluator settings identity drift")
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        self._timeout = float(settings["timeout_seconds_per_gate"])
        self._template, self.prompt_identity = _load_prompt(self._root, gate_id)
        self.evaluator_identity = (GATE_F_EVALUATOR_IDENTITY if gate_id is GateIdV2.FACTUAL_SEMANTIC
                                   else GATE_S_EVALUATOR_IDENTITY)

    def render_prompt(self, request: dict[str, object]) -> str:
        expected = GateIdV2(request.get("gate_id"))
        if expected is not self.gate_id:
            raise ValueError("request gate does not match evaluator")
        summary, candidate = request.get("factual_summary"), request.get("candidate")
        if type(summary) is not str or type(candidate) is not str:
            raise ValueError("evaluator request text is invalid")
        prompt = self._template.replace("{factual_summary}", summary).replace("{candidate}", candidate)
        if self.gate_id is GateIdV2.STORY_SPECIFICITY:
            controls = request.get("controls")
            if type(controls) is not list or not 2 <= len(controls) <= 3:
                raise ValueError("specificity controls are invalid")
            lines = []
            for item in controls:
                if type(item) is not dict or type(item.get("case_id")) is not str or type(item.get("factual_summary")) is not str:
                    raise ValueError("specificity control is invalid")
                lines.append(f"[{item['case_id']}] {item['factual_summary']}")
            prompt = prompt.replace("{controls}", "\n".join(lines))
        if "{factual_summary}" in prompt or "{candidate}" in prompt or "{controls}" in prompt:
            raise ValueError("evaluator prompt construction incomplete")
        return prompt

    def __call__(self, request: dict[str, object]) -> str:
        prompt = self.render_prompt(request)
        authority = ApplicationRequestAuthorityV1().build(ApplicationProviderRequestV1(
            ProviderChoiceV1.OLLAMA, prompt,
            f"semantic-admission-v2:{self.gate_id.value.lower()}:{_sha(prompt.encode())[:32]}",
            datetime.now(UTC), TimeoutPolicyV2(timeout_seconds=self._timeout),
            CancellationTokenV2(cancellation_requested=False)))
        result = self._executor.execute(authority)
        if (result.outcome is not ExecutionOutcomeV2.COMPLETED or result.provider_result is None
                or result.provider_result.status is not ProviderResultStatusV2.SUCCESS
                or len(result.provider_result.outputs) != 1
                or result.provider_result.outputs[0].finish_reason is not ProviderFinishReasonV2.COMPLETED):
            raise RuntimeError("SAV2 local evaluator failed")
        return result.provider_result.outputs[0].generated_text


def _load_prompt(root: Path, gate_id: GateIdV2) -> tuple[str, str]:
    name, expected, execution_expected = (("semantic-admission-v2-gate-f-prompt.txt", GATE_F_PROMPT_SHA256, GATE_F_EXECUTION_PROMPT_SHA256)
                      if gate_id is GateIdV2.FACTUAL_SEMANTIC else
                      ("semantic-admission-v2-gate-s-prompt.txt", GATE_S_PROMPT_SHA256, GATE_S_EXECUTION_PROMPT_SHA256))
    data = (root / "docs" / "artifacts" / name).read_bytes()
    if _sha(data) != expected:
        raise RuntimeError("SAV2 evaluator prompt identity drift")
    if not data.endswith(b"\n") or data.endswith(b"\n\n"):
        raise RuntimeError("SAV2 evaluator prompt terminal newline drift")
    execution_data = data[:-1]
    if _sha(execution_data) != execution_expected:
        raise RuntimeError("SAV2 executable prompt identity drift")
    text = execution_data.decode("utf-8", errors="strict")
    return text, "sha256:" + execution_expected


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


__all__ = ("CoreV12SemanticEvaluatorAdapter", "GATE_F_EVALUATOR_IDENTITY",
           "GATE_F_PROMPT_SHA256", "GATE_S_EVALUATOR_IDENTITY", "GATE_S_PROMPT_SHA256",
           "GATE_F_EXECUTION_PROMPT_SHA256", "GATE_S_EXECUTION_PROMPT_SHA256")
