from __future__ import annotations

import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2 import GateIdV2
from pastila_scout.semantic_admission_v2.core_adapter_v2_3 import CoreV12SemanticEvaluatorAdapterV23
from pastila_scout.semantic_admission_v2.models import GateResponseV2, REASON_CODES_V2

ROOT = Path(__file__).resolve().parents[1]


class ForbiddenExecutor:
    calls = 0

    def execute(self, request):
        self.calls += 1
        raise AssertionError("V2.3 zero-inference test invoked executor")


def _request() -> dict[str, str]:
    return {"gate_id": "FACTUAL_SEMANTIC", "factual_summary": "Rezumat factual guvernat suficient de lung.", "candidate": "Comentariu candidat."}


def test_v23_is_gate_f_only_and_renders_exact_unpadded_candidate() -> None:
    forbidden = ForbiddenExecutor()
    adapter = CoreV12SemanticEvaluatorAdapterV23(project_root=ROOT, executor=forbidden, gate_id=GateIdV2.FACTUAL_SEMANTIC)
    prompt = adapter.render_prompt(_request())
    assert prompt == prompt.strip()
    assert "```" not in prompt
    assert "first {, last }" in prompt
    assert "{factual_summary}" not in prompt and "{candidate}" not in prompt
    assert forbidden.calls == 0
    with pytest.raises(ValueError, match="Gate-F-only"):
        CoreV12SemanticEvaluatorAdapterV23(project_root=ROOT, executor=forbidden, gate_id=GateIdV2.STORY_SPECIFICITY)


def test_v23_preserves_all_gate_f_semantic_codes() -> None:
    prompt = (ROOT / "docs/artifacts/semantic-admission-v2-gate-f-contract-v2-3-prompt.txt").read_text(encoding="utf-8")
    expected = {code for code in REASON_CODES_V2 if code.startswith("FSEM_")} | {"ADMISSION_INDETERMINATE"}
    assert expected == {code for code in expected if code in prompt}


@pytest.mark.parametrize("value", [
    {"gate_id": "FACTUAL_SEMANTIC", "decision": "PASS", "reason_records": []},
    {"gate_id": "FACTUAL_SEMANTIC", "decision": "FAIL", "reason_records": [{"code": "FSEM_UNSUPPORTED_CAUSALITY", "status": "DECISIVE", "candidate_span": "din cauza", "authority_support": None, "unsupported_proposition": "cauzalitate nesusținută", "confidence": 0.9}]},
    {"gate_id": "FACTUAL_SEMANTIC", "decision": "INDETERMINATE", "reason_records": [{"code": "ADMISSION_INDETERMINATE", "status": "DECISIVE", "candidate_span": None, "authority_support": None, "unsupported_proposition": "autoritate insuficientă", "confidence": 0.5}]},
])
def test_v23_allowed_response_forms_satisfy_unchanged_strict_parser(value: dict) -> None:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    GateResponseV2.model_validate_json(raw, strict=True)
