from __future__ import annotations

import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2 import GateIdV2
from pastila_scout.semantic_admission_v2.core_adapter_v2_5 import CoreV12SemanticEvaluatorAdapterV25
from pastila_scout.semantic_admission_v2.source_span_validation_v1 import SpanSourceViolationV1, validate_reason_span_sources_v1

ROOT = Path(__file__).resolve().parents[1]


class ForbiddenExecutor:
    calls = 0

    def execute(self, request):
        self.calls += 1
        raise AssertionError("V2.5 zero-inference test invoked executor")


def _raw(*, candidate_span=None, authority_support=None) -> str:
    return json.dumps({"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{
        "code":"FSEM_CERTAINTY_MUTATION","status":"DECISIVE","candidate_span":candidate_span,
        "authority_support":authority_support,"unsupported_proposition":"mutation","confidence":0.9,
    }]}, ensure_ascii=False, separators=(",", ":"))


def test_v25_composes_exact_unpadded_prompt_without_inference() -> None:
    forbidden = ForbiddenExecutor()
    adapter = CoreV12SemanticEvaluatorAdapterV25(project_root=ROOT, executor=forbidden, gate_id=GateIdV2.FACTUAL_SEMANTIC)
    prompt = adapter.render_prompt({"gate_id":"FACTUAL_SEMANTIC","factual_summary":"Fapt posibil în 2027.","candidate":"Ca și cum s-a schimbat acum."})
    assert prompt == prompt.strip()
    assert "SEMANTIC ADMISSION V2.4" in prompt
    assert "V2.5 RESIDUAL DISCIPLINE" in prompt
    assert prompt.index("V2.5 RESIDUAL DISCIPLINE") < prompt.index("FACTUAL SUMMARY:")
    assert forbidden.calls == 0
    with pytest.raises(ValueError, match="Gate-F-only"):
        CoreV12SemanticEvaluatorAdapterV25(project_root=ROOT, executor=forbidden, gate_id=GateIdV2.STORY_SPECIFICITY)


def test_v25_requires_delta_first_negative_evidence_and_status_grouping() -> None:
    addendum = (ROOT / "docs/artifacts/semantic-admission-v2-gate-f-contract-v2-5-addendum.txt").read_text("utf-8")
    assert "possibility/conditionality/certainty" in addendum
    assert "does not itself supply real intent or causality" in addendum
    assert "certainty is DECISIVE and timing is SUPPORTING" in addendum
    assert "Do not mark every detected class DECISIVE" in addendum


def test_source_validator_accepts_exact_candidate_and_authority_membership() -> None:
    response = validate_reason_span_sources_v1(
        raw_response=_raw(candidate_span="s-a schimbat", authority_support="ar putea"),
        factual_summary="Regula ar putea apărea.", candidate="Pare că s-a schimbat deja.",
    )
    assert response.reason_records[0].candidate_span == "s-a schimbat"


def test_source_validator_rejects_authority_text_in_candidate_span_without_repair() -> None:
    with pytest.raises(SpanSourceViolationV1, match="CANDIDATE_SPAN_NOT_IN_CANDIDATE"):
        validate_reason_span_sources_v1(
            raw_response=_raw(candidate_span="ar putea avea parte"),
            factual_summary="Elevii ar putea avea parte de reguli.", candidate="Regulile s-au schimbat.",
        )


def test_source_validator_rejects_candidate_text_in_authority_support_without_repair() -> None:
    with pytest.raises(SpanSourceViolationV1, match="AUTHORITY_SUPPORT_NOT_IN_FACTUAL_SUMMARY"):
        validate_reason_span_sources_v1(
            raw_response=_raw(authority_support="s-au schimbat"),
            factual_summary="Regulile ar putea apărea.", candidate="Regulile s-au schimbat.",
        )


def test_source_validator_allows_null_but_never_mutates_raw_response() -> None:
    raw = _raw(candidate_span=None, authority_support=None)
    validate_reason_span_sources_v1(raw_response=raw, factual_summary="Fapt.", candidate="Comentariu.")
    assert raw == _raw(candidate_span=None, authority_support=None)


def test_v25_acceptance_contract_preserves_case_01_and_exact_case_10() -> None:
    candidate = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-gate-f-contract-v2-5-candidate.json").read_text("utf-8"))
    assert candidate["acceptance_contract"]["HMCV1-SASC-01"] == "Exact PASS with no reasons."
    assert "certainty DECISIVE" in candidate["acceptance_contract"]["HMCV1-SASC-10"]
    assert candidate["preserved"]["gate_s"] == "UNCHANGED_AND_SEPARATE"
    assert candidate["inference_authority"] is candidate["runtime_authority"] is candidate["training_authority"] is False
