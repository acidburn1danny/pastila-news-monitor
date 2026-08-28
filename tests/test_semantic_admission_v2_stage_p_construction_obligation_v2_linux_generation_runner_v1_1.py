from __future__ import annotations

from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_composition_v1_1 import (
    LINUX_GENERATION_COMPOSITION_IDENTITY,
    LinuxGenerationCompositionOutcomeV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_runner_v1_1 import (
    INNER_TIMEOUT_SECONDS,
    LINUX_GENERATION_RUNNER_IDENTITY,
    run_linux_generation_runner_v1_1,
)

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt"


def _inputs(tmp_path):
    paths = []
    for name, raw in (("policy", b"policy"), ("authority", b"authority"),
                      ("request", b"request")):
        path = tmp_path / name
        path.write_bytes(raw)
        paths.append(path)
    return paths


def test_v1_1_runner_calls_only_injected_v1_1_composition(tmp_path) -> None:
    policy, authority, request = _inputs(tmp_path)
    evidence = tmp_path / "evidence"
    calls = []
    expected = LinuxGenerationCompositionOutcomeV1(
        LINUX_GENERATION_COMPOSITION_IDENTITY, "sink", object(), ())
    result = run_linux_generation_runner_v1_1(
        policy_receipt_path=policy, authority_receipt_path=authority,
        runner_request_path=request, system_prompt_path=PROMPT,
        evidence_root=evidence,
        composition=lambda **kwargs: calls.append(kwargs) or expected)
    assert result is expected and len(calls) == 1
    assert calls[0]["raw_authority_receipt"] == b"authority"
    assert calls[0]["timeout_seconds"] == INNER_TIMEOUT_SECONDS == 1200.0
    assert not evidence.exists()
    assert LINUX_GENERATION_RUNNER_IDENTITY == "ed9303593dea53b9375913e3cb1640cdb11f2e347299435532f7e3935bf755da"


def test_v1_1_runner_fails_before_composition_on_drift(tmp_path) -> None:
    policy, authority, request = _inputs(tmp_path)
    prompt = tmp_path / "prompt"
    prompt.write_text("drift", "utf-8")
    calls = []
    with pytest.raises(ValueError, match="SYSTEM_PROMPT_IDENTITY"):
        run_linux_generation_runner_v1_1(
            policy_receipt_path=policy, authority_receipt_path=authority,
            runner_request_path=request, system_prompt_path=prompt,
            evidence_root=tmp_path / "evidence",
            composition=lambda **kwargs: calls.append(kwargs))
    assert calls == []
