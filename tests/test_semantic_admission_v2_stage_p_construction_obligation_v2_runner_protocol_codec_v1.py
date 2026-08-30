from __future__ import annotations
import hashlib,json
from datetime import UTC,datetime
from pathlib import Path
import pytest
from pastila_scout.wsl_execution_v1 import canonical_model_profile_v1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_application_request_v1 import build_construction_obligation_v2_application_request_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_host_wsl_payload_contract_v1 import build_construction_obligation_v2_host_wsl_payload_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_projector_binding_v1 import prepare_construction_obligation_v2_projector_binding_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_provider_execution_request_binding_v1 import bind_construction_obligation_v2_provider_execution_request_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_request_renderer_v1 import ConstructionObligationV2RequestRendererV1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runner_protocol_codec_v1 import *
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runner_protocol_contract_v1 import DECODER_IDENTITY,PROJECTOR_FREEZE_IDENTITY,RUNNER_PROTOCOL_IDENTITY,TOKENIZER_IDENTITY
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_static_executor_binding_v1 import bind_construction_obligation_v2_static_executor_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_static_payload_binding_v1 import build_construction_obligation_v2_static_payload_v1

ROOT=Path(__file__).resolve().parents[1]; WHEN=datetime(2026,8,28,12,tzinfo=UTC)
def _fixture():
    source=prepare_construction_obligation_v2_projector_binding_v1(candidate_utf8="cerere ș".encode(),factual_authority_utf8="autoritate".encode())
    static=build_construction_obligation_v2_static_payload_v1(source_binding=source)
    rendered=ConstructionObligationV2RequestRendererV1(project_root=ROOT).render(canonical_static_payload=static)
    app=build_construction_obligation_v2_application_request_v1(rendered_request=rendered,requested_at=WHEN)
    execution=bind_construction_obligation_v2_provider_execution_request_v1(candidate=app)
    host=build_construction_obligation_v2_host_wsl_payload_v1(execution_binding=execution,rendered_request=rendered,canonical_static_payload=static,max_output_tokens=731)
    binding=bind_construction_obligation_v2_static_executor_v1(project_root=ROOT,raw_host_payload=host,wsl_boundary=WslExecutionBoundaryV1_1(canonical_model_profile_v1()))
    raw=build_runner_request_v1(raw_host_payload=host,static_binding=binding)
    return raw,parse_runner_request_v1(raw_request=raw)

def test_request_round_trip_and_mutation_rejection():
    raw,request=_fixture(); assert request.max_output_tokens==731
    value=json.loads(raw);value["source_context_identity"]="0"*64
    with pytest.raises(ValueError,match="HOST_MISMATCH"):parse_runner_request_v1(raw_request=(json.dumps(value,sort_keys=True,separators=(",",":"))+"\n").encode())

def test_lifecycle_chain_and_result_branches():
    _,request=_fixture(); first=build_lifecycle_event_v1(request=request,sequence=0,event="REQUEST_VALIDATED",detail={},previous_event_identity=None)
    first_id=json.loads(first)["event_identity"]
    terminal=build_runner_result_v1(request=request,status="TERMINAL_OUTPUT",lifecycle_terminal_event_identity=first_id,output=b"{}")
    assert json.loads(terminal)["terminal_eos"] is True
    failure=build_runner_result_v1(request=request,status="EXECUTION_FAILURE",lifecycle_terminal_event_identity=first_id,execution_failure_code="TRANSPORT")
    assert json.loads(failure)["output_utf8_base64"] is None
    with pytest.raises(ValueError,match="BRANCH_INVALID"):build_runner_result_v1(request=request,status="TERMINAL_OUTPUT",lifecycle_terminal_event_identity=first_id)

def test_identity_bound_no_legal_receipt_validation():
    _,request=_fixture();value={"schema_name":"pastila-semantic-admission-v2-construction-obligation-v2-no-legal-token-receipt","schema_version":"1.0.0-evaluation.1","protocol_identity":RUNNER_PROTOCOL_IDENTITY,"projector_freeze_identity":PROJECTOR_FREEZE_IDENTITY,"tokenizer_identity":TOKENIZER_IDENTITY,"decoder_identity":DECODER_IDENTITY,"provider_request_id":request.provider_request_id,"source_context_identity":request.source_context_identity,"generated_prefix_sha256":hashlib.sha256(b"[]").hexdigest(),"generated_token_count":0,"character_state_identity":"1"*64,"dfa_mode":"PREFIX","terminal":False,"allowed_token_count":0,"failure_code":"NO_LEGAL_TOKEN_NONTERMINAL","receipt_identity":""}
    canonical=lambda v:(json.dumps(v,ensure_ascii=True,sort_keys=True,separators=(",",":"))+"\n").encode()
    value["receipt_identity"]=hashlib.sha256(canonical({k:v for k,v in value.items() if k!="receipt_identity"})).hexdigest();raw=canonical(value)
    assert validate_no_legal_token_receipt_v1(raw_receipt=raw,request=request)==value["receipt_identity"]
    value["provider_request_id"]="wrong"
    with pytest.raises(ValueError,match="BINDING_MISMATCH"):validate_no_legal_token_receipt_v1(raw_receipt=canonical(value),request=request)


def test_v1_2_1_no_legal_receipt_preserves_terminal_semantic_classification():
    from types import SimpleNamespace
    from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_request_bound_callback_adapter_v1_2_1 import _no_legal_receipt
    _, request = _fixture()
    terminal_candidate = b'{"observed":"terminal"}'
    raw = _no_legal_receipt(
        request=request, authority="a" * 64, generated=(10, 11),
        terminal_candidate=terminal_candidate,
        receipt=SimpleNamespace(
            request_context_identity=request.source_context_identity,
            decoded_sha256=hashlib.sha256(terminal_candidate).hexdigest(),
            dfa_mode="TERMINAL", terminal=True,
            reason_code="SEMANTIC_COMPLETENESS_AUTHORITY_COVERAGE_INCOMPLETE"))
    value = json.loads(raw)
    assert value["schema_version"] == "1.2.1"
    assert value["projector_terminal"] is True
    assert value["failure_code"] == "SEMANTIC_COMPLETENESS_EOS_WITHHELD"
    assert value["projector_reason_code"] == (
        "SEMANTIC_COMPLETENESS_AUTHORITY_COVERAGE_INCOMPLETE")
    assert value["terminal_candidate_utf8_bytes"] == 23
    assert validate_no_legal_token_receipt_v1(
        raw_receipt=raw, request=request) == value["receipt_identity"]

    canonical = lambda item: (json.dumps(
        item, ensure_ascii=True, sort_keys=True,
        separators=(",", ":")) + "\n").encode()
    mutations = (
        {"terminal_candidate_utf8_base64": "Zm9yZ2Vk"},
        {"terminal_candidate_sha256": "0" * 64},
        {"projector_decoded_sha256": "0" * 64},
        {"authority_receipt_identity": "0" * 64},
        {"character_state_identity": "0" * 64},
    )
    for mutation in mutations:
        forged = {**value, **mutation}
        forged["receipt_identity"] = hashlib.sha256(canonical({
            key: item for key, item in forged.items()
            if key != "receipt_identity"})).hexdigest()
        with pytest.raises(ValueError):
            validate_no_legal_token_receipt_v1(
                raw_receipt=canonical(forged), request=request)

def test_codec_has_no_runtime_imports():
    text=(ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_runner_protocol_codec_v1.py").read_text("utf-8")
    for word in ("transformers","tokenizers","torch","subprocess","experimental_core",".execute(","build_invocation","generate("):assert word not in text
