from __future__ import annotations

import json

from pastila_scout.semantic_admission_v2.capturing_coordinator_v2_1 import (
    CapturingSemanticAdmissionCoordinatorV21, ContractDiagnosticV21,
)
from test_semantic_admission_v2 import _input, _response


def _coordinator(f,s):
    return CapturingSemanticAdmissionCoordinatorV21(gate_f=f,gate_s=s,
        gate_f_identity="f",gate_s_identity="s",gate_f_prompt_identity="pf",gate_s_prompt_identity="ps")


def test_preserves_exact_raw_text_and_matches_receipt_hash():
    raw_f=_response("FACTUAL_SEMANTIC","PASS"); raw_s=_response("STORY_SPECIFICITY","PASS")
    result=_coordinator(lambda _:raw_f,lambda _:raw_s).evaluate(_input())
    assert result.gate_f_evidence.raw_response == raw_f
    assert result.gate_s_evidence.raw_response == raw_s
    assert result.gate_f_evidence.diagnostic is ContractDiagnosticV21.VALID
    assert result.gate_f_evidence.raw_response_sha256 == result.receipt.gate_f.raw_response_sha256


def test_classifies_markdown_fence_as_non_json_and_preserves_it():
    raw='```json\n{"gate_id":"FACTUAL_SEMANTIC"}\n```'
    result=_coordinator(lambda _:raw,lambda _:_response("STORY_SPECIFICITY","PASS")).evaluate(_input())
    assert result.gate_f_evidence.raw_response == raw
    assert result.gate_f_evidence.diagnostic is ContractDiagnosticV21.NON_JSON


def test_classifies_wrong_keys_and_strict_schema_separately():
    wrong=json.dumps({"gate_id":"FACTUAL_SEMANTIC","decision":"PASS","reason_records":[],"extra":1})
    invalid=json.dumps({"gate_id":"STORY_SPECIFICITY","decision":"FAIL","reason_records":[]})
    result=_coordinator(lambda _:wrong,lambda _:invalid).evaluate(_input())
    assert result.gate_f_evidence.diagnostic is ContractDiagnosticV21.WRONG_KEY_SET
    assert result.gate_s_evidence.diagnostic is ContractDiagnosticV21.STRICT_SCHEMA_INVALID


def test_evaluator_exception_is_captured_without_retry():
    calls=0
    def fail(_):
        nonlocal calls; calls+=1; raise RuntimeError("bounded")
    result=_coordinator(fail,lambda _:_response("STORY_SPECIFICITY","PASS")).evaluate(_input())
    assert calls==1
    assert result.gate_f_evidence.raw_response is None
    assert result.gate_f_evidence.diagnostic is ContractDiagnosticV21.EVALUATOR_EXCEPTION
    assert result.gate_f_evidence.evaluator_exception_type == "RuntimeError"
