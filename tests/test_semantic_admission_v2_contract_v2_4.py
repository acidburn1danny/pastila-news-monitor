from __future__ import annotations

import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2 import GateIdV2
from pastila_scout.semantic_admission_v2.core_adapter_v2_4 import CoreV12SemanticEvaluatorAdapterV24
from pastila_scout.semantic_admission_v2.gate_f_constraint_v1 import GATE_F_CODES, GateFConstraintStateV1
from pastila_scout.semantic_admission_v2.models import REASON_CODES_V2

ROOT = Path(__file__).resolve().parents[1]


class ForbiddenExecutor:
    calls = 0

    def execute(self, request):
        self.calls += 1
        raise AssertionError("V2.4 zero-inference test invoked executor")


def _adapter() -> tuple[CoreV12SemanticEvaluatorAdapterV24, ForbiddenExecutor]:
    forbidden = ForbiddenExecutor()
    return CoreV12SemanticEvaluatorAdapterV24(project_root=ROOT, executor=forbidden, gate_id=GateIdV2.FACTUAL_SEMANTIC), forbidden


def test_v24_exact_unpadded_request_construction_is_zero_inference() -> None:
    adapter, forbidden = _adapter()
    prompt = adapter.render_prompt({"gate_id":"FACTUAL_SEMANTIC","factual_summary":"Rezumat factual.","candidate":"Comentariu."})
    assert prompt == prompt.strip()
    assert "Rezumat factual." in prompt and "Comentariu." in prompt
    assert "{factual_summary}" not in prompt and "{candidate}" not in prompt
    assert forbidden.calls == 0
    with pytest.raises(ValueError, match="Gate-F-only"):
        CoreV12SemanticEvaluatorAdapterV24(project_root=ROOT, executor=forbidden, gate_id=GateIdV2.STORY_SPECIFICITY)


def test_v24_encodes_figurative_scope_and_factual_return_distinction() -> None:
    prompt = (ROOT / "docs/artifacts/semantic-admission-v2-gate-f-contract-v2-4-prompt.txt").read_text("utf-8")
    assert "Do not literalize a figurative vehicle" in prompt
    assert "protected creative language returns to an unsupported real-world proposition" in prompt
    assert "Genericity and template quality are not factual unsafety" in prompt


def test_v24_requires_embedded_presupposed_and_exhaustive_propositions() -> None:
    prompt = (ROOT / "docs/artifacts/semantic-admission-v2-gate-f-contract-v2-4-prompt.txt").read_text("utf-8")
    assert "asserted, presupposed, entailed, or necessarily implied" in prompt
    assert "surface semantic head cannot shield" in prompt
    assert "Add separate records for all material unsupported propositions/classes" in prompt


def test_v24_semantic_head_rules_cover_every_governed_code_without_namespace_change() -> None:
    prompt = (ROOT / "docs/artifacts/semantic-admission-v2-gate-f-contract-v2-4-prompt.txt").read_text("utf-8")
    expected = {code for code in REASON_CODES_V2 if code.startswith("FSEM_")} | {"ADMISSION_INDETERMINATE"}
    assert set(GATE_F_CODES) == expected
    assert all(code in prompt for code in expected)
    assert "not by nearby tone or the sentence's surface head" in prompt


def test_v24_case_contract_requires_exact_pass_and_negative_reasons() -> None:
    candidate = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-gate-f-contract-v2-4-candidate.json").read_text("utf-8"))
    assert candidate["acceptance_contract"]["exact_pass_case_ids"] == ["HMCV1-SASC-01", "HMCV1-SASC-02", "HMCV1-SASC-04"]
    assert candidate["acceptance_contract"]["exact_negative_case_ids"] == ["HMCV1-SASC-03", "HMCV1-SASC-05", "HMCV1-SASC-06", "HMCV1-SASC-07", "HMCV1-SASC-08", "HMCV1-SASC-09", "HMCV1-SASC-10"]
    design = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-gate-f-remediation-design-v1.json").read_text("utf-8"))
    reasons = {item["case_id"]: (item.get("decisive", []), item.get("supporting", [])) for item in design["run4_case_contract"]}
    assert reasons == {
        "HMCV1-SASC-01": ([], []),
        "HMCV1-SASC-02": ([], []),
        "HMCV1-SASC-03": (["FSEM_UNSUPPORTED_BIOGRAPHY_OR_HISTORY"], ["FSEM_UNSUPPORTED_PREMISE_TO_DIRECTIVE"]),
        "HMCV1-SASC-04": ([], []),
        "HMCV1-SASC-05": (["FSEM_UNSUPPORTED_MOTIVE_OR_INTENT"], []),
        "HMCV1-SASC-06": (["FSEM_UNSUPPORTED_BIOGRAPHY_OR_HISTORY"], ["FSEM_UNSUPPORTED_PREMISE_TO_DIRECTIVE"]),
        "HMCV1-SASC-07": (["FSEM_UNSUPPORTED_EMOTION_OR_REACTION"], []),
        "HMCV1-SASC-08": (["FSEM_UNSUPPORTED_OUTCOME_OR_STATUS"], []),
        "HMCV1-SASC-09": (["FSEM_UNSUPPORTED_BIOGRAPHY_OR_HISTORY"], ["FSEM_UNSUPPORTED_CAPACITY"]),
        "HMCV1-SASC-10": (["FSEM_CERTAINTY_MUTATION"], ["FSEM_TIMING_MUTATION", "FSEM_UNSUPPORTED_LIFE_STAKES"]),
    }


def test_v24_multi_reason_response_is_accepted_by_unchanged_constraint() -> None:
    raw = json.dumps({"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[
        {"code":"FSEM_CERTAINTY_MUTATION","status":"DECISIVE","candidate_span":"sigur","authority_support":None,"unsupported_proposition":"certitudine","confidence":0.9},
        {"code":"FSEM_TIMING_MUTATION","status":"SUPPORTING","candidate_span":"acum","authority_support":None,"unsupported_proposition":"timp","confidence":0.9},
        {"code":"FSEM_UNSUPPORTED_LIFE_STAKES","status":"SUPPORTING","candidate_span":"viitorul","authority_support":None,"unsupported_proposition":"mize","confidence":0.9},
    ]}, ensure_ascii=False, separators=(",", ":"))
    assert GateFConstraintStateV1().feed(raw).can_eos


def test_v24_grants_no_probe_runtime_or_gate_s_authority() -> None:
    candidate = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-gate-f-contract-v2-4-candidate.json").read_text("utf-8"))
    assert candidate["inference_authority"] is candidate["runtime_authority"] is candidate["training_authority"] is False
    assert candidate["preserved"]["gate_s"] == "UNCHANGED_AND_SEPARATE"
