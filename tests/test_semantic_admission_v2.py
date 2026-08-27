from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from pastila_scout.semantic_admission_v2 import (
    AdmissionInputV2, AuthorityBindingV2, CandidateBindingV2,
    FinalAdmissionDecisionV2, PortabilityControlV2, RuntimeBindingV2,
    SemanticAdmissionCoordinatorV2, SurfaceDefenseFindingV2,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _input(*, surface=()):
    summary = "O autoritate a propus schimbarea numelui unui parc public existent."
    candidate = "Numele nou aleargă deja, deși parcul încă stă pe loc."
    controls = []
    for case_id, text in (("CONTROL-1", "Debitul unui fluviu va scădea ușor în următoarele zile."),
                          ("CONTROL-2", "O pană de curent a întrerupt alimentarea mai multor cartiere.")):
        controls.append(PortabilityControlV2(case_id=case_id, factual_summary=text,
            factual_summary_sha256=_sha(text), authority_identity="authority:"+case_id))
    return AdmissionInputV2(case_id="SOURCE-1",
        authority=AuthorityBindingV2(factual_summary=summary, factual_summary_sha256=_sha(summary),
                                     authority_identity="authority:source", byte_immutable=True),
        candidate=CandidateBindingV2(commentary=candidate, candidate_sha256=_sha(candidate),
                                     raw_response_sha256="0"*64),
        runtime=RuntimeBindingV2(application_identity="app", core_identity="core", voice_identity="voice",
                                 prompt_identity="prompt", model_identity="model"),
        portability_controls=tuple(controls), surface_findings=surface)


def _response(gate, decision, reasons=()):
    return json.dumps({"gate_id":gate,"decision":decision,"reason_records":list(reasons)}, separators=(",", ":"))


def _reason(code):
    return {"code":code,"status":"DECISIVE","candidate_span":"span","authority_support":None,
            "unsupported_proposition":"unsupported","confidence":0.9}


def _coordinator(f, s):
    return SemanticAdmissionCoordinatorV2(gate_f=f, gate_s=s, gate_f_identity="eval:f",
        gate_s_identity="eval:s", gate_f_prompt_identity="prompt:f", gate_s_prompt_identity="prompt:s")


def test_both_pass_yields_quarantined_diagnostic_admission():
    receipt = _coordinator(lambda _: _response("FACTUAL_SEMANTIC","PASS"),
                           lambda _: _response("STORY_SPECIFICITY","PASS")).evaluate(_input())
    assert receipt.final_decision is FinalAdmissionDecisionV2.ADMIT
    assert receipt.eligibility == "QUARANTINED_EVALUATION_ONLY"
    assert receipt.current_runtime_admission_affected is False
    assert receipt.receipt_identity.startswith("sha256:")


def test_factual_failure_has_precedence_but_both_gates_execute():
    calls = []
    def f(_): calls.append("f"); return _response("FACTUAL_SEMANTIC","FAIL",[_reason("FSEM_UNSUPPORTED_MOTIVE_OR_INTENT")])
    def s(_): calls.append("s"); return _response("STORY_SPECIFICITY","PASS")
    receipt = _coordinator(f,s).evaluate(_input())
    assert calls == ["f","s"]
    assert receipt.final_decision is FinalAdmissionDecisionV2.REJECT_FACTUAL_SEMANTIC
    assert receipt.precedence_reason == "FSEM_UNSUPPORTED_MOTIVE_OR_INTENT"


def test_specificity_failure_is_not_factual_unsafety():
    receipt = _coordinator(lambda _: _response("FACTUAL_SEMANTIC","PASS"),
        lambda _: _response("STORY_SPECIFICITY","FAIL_GENERIC_PORTABLE",[_reason("SPEC_GENERIC_PORTABLE")])).evaluate(_input())
    assert receipt.final_decision is FinalAdmissionDecisionV2.REJECT_OWNER_QUALITY
    assert receipt.precedence_reason == "SPEC_GENERIC_PORTABLE"


def test_malformed_evaluator_output_fails_closed_without_retry():
    calls = {"f":0,"s":0}
    def f(_): calls["f"] += 1; return "not-json"
    def s(_): calls["s"] += 1; return _response("STORY_SPECIFICITY","PASS")
    receipt = _coordinator(f,s).evaluate(_input())
    assert calls == {"f":1,"s":1}
    assert receipt.final_decision is FinalAdmissionDecisionV2.ADMISSION_ABSTAINED
    assert receipt.gate_f.error_code == "ADMISSION_EVALUATOR_FAILURE"


def test_surface_entity_proxy_is_preserved_but_cannot_override_semantic_pass():
    value = _input(surface=(SurfaceDefenseFindingV2(code="factual_entity_reuse"),))
    receipt = _coordinator(lambda _: _response("FACTUAL_SEMANTIC","PASS"),
                           lambda _: _response("STORY_SPECIFICITY","PASS")).evaluate(value)
    assert receipt.final_decision is FinalAdmissionDecisionV2.ADMIT
    assert receipt.surface_findings[0].role.value == "DEFENSE_IN_DEPTH_ONLY"


def test_authority_and_candidate_hash_drift_are_rejected_before_evaluation():
    with pytest.raises(ValidationError, match="factual authority byte binding failed"):
        AuthorityBindingV2(factual_summary="A"*30, factual_summary_sha256="0"*64,
                           authority_identity="authority", byte_immutable=True)
    with pytest.raises(ValidationError, match="candidate byte binding failed"):
        CandidateBindingV2(commentary="candidate", candidate_sha256="0"*64,
                           raw_response_sha256="0"*64)


def test_wrong_gate_and_extra_keys_fail_closed():
    wrong = lambda _: json.dumps({"gate_id":"STORY_SPECIFICITY","decision":"PASS","reason_records":[],"extra":1})
    receipt = _coordinator(wrong, lambda _: _response("STORY_SPECIFICITY","PASS")).evaluate(_input())
    assert receipt.final_decision is FinalAdmissionDecisionV2.ADMISSION_ABSTAINED


def test_unknown_reason_code_fails_closed():
    unknown = lambda _: _response("FACTUAL_SEMANTIC", "FAIL", [_reason("FSEM_NOT_GOVERNED")])
    receipt = _coordinator(unknown, lambda _: _response("STORY_SPECIFICITY", "PASS")).evaluate(_input())
    assert receipt.final_decision is FinalAdmissionDecisionV2.ADMISSION_ABSTAINED
    assert receipt.gate_f.error_code == "ADMISSION_EVALUATOR_FAILURE"
