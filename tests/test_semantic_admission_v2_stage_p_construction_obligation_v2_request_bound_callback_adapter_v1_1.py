from __future__ import annotations
import json
from pathlib import Path
import pytest
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_projector_binding_v1 import prepare_construction_obligation_v2_projector_binding_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_request_bound_callback_adapter_v1_1 import *
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runner_protocol_codec_v1 import RunnerRequestV1,validate_no_legal_token_receipt_v1

ROOT=Path(__file__).resolve().parents[1]
def _fixture(context="context"):
 binding=prepare_construction_obligation_v2_projector_binding_v1(candidate_utf8=context.encode(),factual_authority_utf8=b"authority")
 request=RunnerRequestV1("application-request-v1:abc",binding.source_context_identity,"1"*64,b"payload",731)
 return request,binding
def test_request_bound_no_legal_receipt_validates_against_actual_request():
 request,binding=_fixture();adapter=ConstructionObligationV2RequestBoundCallbackAdapterV1_1(request=request,source_binding=binding,token_pieces={10:"x",2:""})
 decision=adapter.project(generated_token_ids=(),decode=lambda _:"")
 value=json.loads(decision.no_legal_token_receipt);assert value["provider_request_id"]==request.provider_request_id
 assert validate_no_legal_token_receipt_v1(raw_receipt=decision.no_legal_token_receipt,request=request)==value["receipt_identity"]
 assert len(request_bound_adapter_instance_identity_v1(adapter))==64
def test_continuable_decision_is_unchanged_and_deterministic():
 request,binding=_fixture();adapter=ConstructionObligationV2RequestBoundCallbackAdapterV1_1(request=request,source_binding=binding,token_pieces={10:"{",2:""})
 result=adapter.project(generated_token_ids=(),decode=lambda _:"");assert result.allowed_token_ids==(10,);assert result.no_legal_token_receipt is None
def test_cross_request_context_fails_before_projection():
 request,_=_fixture("one");_,other=_fixture("two")
 with pytest.raises(ValueError,match="REQUEST_CONTEXT_MISMATCH"):ConstructionObligationV2RequestBoundCallbackAdapterV1_1(request=request,source_binding=other,token_pieces={10:"{"})
def test_source_is_zero_model_and_zero_execution():
 text=(ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_request_bound_callback_adapter_v1_1.py").read_text("utf-8")
 for word in ("transformers","tokenizers","torch","subprocess","experimental_core",".execute(","build_invocation","generate("):assert word not in text
