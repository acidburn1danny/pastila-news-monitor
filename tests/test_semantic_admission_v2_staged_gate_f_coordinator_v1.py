from __future__ import annotations

import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.staged_gate_f_coordinator_v1 import (
    StageIdentityBindingV1, StagedFinalDecisionV1, StagedGateFCoordinatorV1,
)

SUMMARY="Autoritatea spune că regulile ar putea fi schimbate anul viitor."
CANDIDATE="Regulile s-au schimbat deja și testul decide viitorul elevilor."


def _ledger(*, decision="COMPLETE", unresolved=False):
    value={"stage_id":"PROPOSITION_LEDGER","coverage_decision":decision,"entries":[{
        "entry_id":"P1","entry_type":"UNRESOLVED_SCOPE" if unresolved else "REAL_WORLD_COMMITMENT",
        "candidate_span":"Regulile s-au schimbat deja","authority_support":"regulile ar putea fi schimbate anul viitor",
        "commitment":"schimbarea este deja produsă","scope_basis":"UNRESOLVED" if unresolved else "ASSERTED",
        "event_alignment":"UNRESOLVED" if unresolved else "GOVERNED_EVENT",
        "authority_modality":"UNRESOLVED" if unresolved else "POSSIBLE",
        "candidate_modality":"UNRESOLVED" if unresolved else "CERTAIN_OR_ACTUAL",
        "authority_timing":"UNRESOLVED" if unresolved else "FUTURE",
        "candidate_timing":"UNRESOLVED" if unresolved else "COMPLETED","independence_group":"G1"}],
        "coverage_receipt":{"candidate_reviewed_as_whole":True,"embedded_propositions_checked":True,
        "creative_scope_checked":True,"unresolved_scope_present":unresolved}}
    return json.dumps(value,ensure_ascii=False,separators=(",",":"))


def _gate(decision="PASS"):
    reasons=[] if decision=="PASS" else [{"code":"FSEM_CERTAINTY_MUTATION","status":"DECISIVE",
        "candidate_span":"s-au schimbat deja","authority_support":"ar putea fi schimbate",
        "unsupported_proposition":"posibilitatea devine fapt","confidence":0.9}]
    return json.dumps({"gate_id":"FACTUAL_SEMANTIC","decision":decision,"reason_records":reasons},ensure_ascii=False,separators=(",",":"))


class Scripted:
    def __init__(self, raw): self.raw,self.calls=raw,0
    def __call__(self, request): self.calls+=1; return self.raw


class Forbidden:
    def __init__(self): self.calls=0
    def __call__(self, request): self.calls+=1; raise AssertionError("forbidden evaluator invoked")


def _coordinator(tmp_path, p, c):
    p_binding=StageIdentityBindingV1(evaluator_identity="stage-p-eval",prompt_identity="stage-p-prompt",
        grammar_identity="stage-p-grammar",model_identity="core-v1.2")
    c_binding=StageIdentityBindingV1(evaluator_identity="stage-c-eval",prompt_identity="stage-c-prompt",
        grammar_identity="gate-f-v1",model_identity="core-v1.2")
    return StagedGateFCoordinatorV1(stage_p=p,stage_c=c,evidence_root=tmp_path,
        stage_p_binding=p_binding,stage_c_binding=c_binding)


def test_complete_then_pass_uses_exactly_two_calls_and_captures_before_validation(tmp_path: Path) -> None:
    p,c=Scripted(_ledger()),Scripted(_gate())
    receipt=_coordinator(tmp_path,p,c).evaluate(case_id="case-pass",factual_summary=SUMMARY,candidate=CANDIDATE)
    assert receipt.final_decision is StagedFinalDecisionV1.PASS_GATE_F
    assert receipt.calls_consumed==2 and receipt.unused_call_budget==0
    assert p.calls==c.calls==1
    assert Path(receipt.stage_p.raw_path).read_bytes()==p.raw.encode()
    assert Path(receipt.stage_c.raw_path).read_bytes()==c.raw.encode()
    assert (tmp_path/"case-pass/aggregate-receipt.json").is_file()
    assert receipt.stage_p.prompt_identity=="stage-p-prompt"


def test_indeterminate_stage_p_abstains_after_one_call_and_never_calls_c(tmp_path: Path) -> None:
    p,c=Scripted(_ledger(decision="INDETERMINATE",unresolved=True)),Forbidden()
    receipt=_coordinator(tmp_path,p,c).evaluate(case_id="case-indeterminate",factual_summary=SUMMARY,candidate=CANDIDATE)
    assert receipt.final_decision is StagedFinalDecisionV1.ABSTAIN
    assert receipt.precedence_reason=="STAGE_P_INDETERMINATE"
    assert receipt.calls_consumed==1 and receipt.unused_call_budget==1 and c.calls==0


def test_invalid_stage_p_raw_is_durable_and_abstains_without_c(tmp_path: Path) -> None:
    p,c=Scripted('{"broken":true}'),Forbidden()
    receipt=_coordinator(tmp_path,p,c).evaluate(case_id="case-invalid",factual_summary=SUMMARY,candidate=CANDIDATE)
    assert Path(receipt.stage_p.raw_path).read_text("utf-8")==p.raw
    assert receipt.precedence_reason=="STAGE_P_SCHEMA_OR_SOURCE_VALIDATION_FAILURE"
    assert c.calls==0 and receipt.calls_consumed==1


def test_stage_p_provider_exception_is_recorded_and_stops(tmp_path: Path) -> None:
    p,c=Forbidden(),Forbidden()
    receipt=_coordinator(tmp_path,p,c).evaluate(case_id="case-provider",factual_summary=SUMMARY,candidate=CANDIDATE)
    assert receipt.precedence_reason=="STAGE_P_PROVIDER_OR_TRANSPORT_FAILURE"
    assert (tmp_path/"case-provider/stage-p-provider-exception.json").is_file()
    assert p.calls==1 and c.calls==0


def test_stage_c_failure_rejects_and_cross_source_span_abstains(tmp_path: Path) -> None:
    p,c=Scripted(_ledger()),Scripted(_gate("FAIL"))
    rejected=_coordinator(tmp_path,p,c).evaluate(case_id="case-reject",factual_summary=SUMMARY,candidate=CANDIDATE)
    assert rejected.final_decision is StagedFinalDecisionV1.REJECT_FACTUAL_SEMANTIC
    bad=json.loads(_gate("FAIL")); bad["reason_records"][0]["candidate_span"]="ar putea fi schimbate"
    p2,c2=Scripted(_ledger()),Scripted(json.dumps(bad,separators=(",",":")))
    abstained=_coordinator(tmp_path,p2,c2).evaluate(case_id="case-bad-span",factual_summary=SUMMARY,candidate=CANDIDATE)
    assert abstained.final_decision is StagedFinalDecisionV1.ABSTAIN
    assert abstained.precedence_reason=="STAGE_C_SCHEMA_OR_SOURCE_VALIDATION_FAILURE"


def test_case_directory_is_append_only_and_cannot_be_overwritten(tmp_path: Path) -> None:
    coordinator=_coordinator(tmp_path,Scripted(_ledger()),Scripted(_gate()))
    coordinator.evaluate(case_id="same",factual_summary=SUMMARY,candidate=CANDIDATE)
    with pytest.raises(FileExistsError):
        coordinator.evaluate(case_id="same",factual_summary=SUMMARY,candidate=CANDIDATE)


def test_zero_inference_construction_does_not_touch_evaluators(tmp_path: Path) -> None:
    p,c=Forbidden(),Forbidden()
    _coordinator(tmp_path,p,c)
    assert p.calls==c.calls==0
