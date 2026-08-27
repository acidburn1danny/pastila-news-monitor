"""Request-bound zero-model callback adapter V1.1."""
from __future__ import annotations
import hashlib,json
from typing import Callable,Mapping,Sequence
from .stage_p_construction_obligation_v2_projector_binding_v1 import (
 DECODER_IDENTITY,PROJECTOR_FREEZE_IDENTITY,TOKENIZER_IDENTITY,
 ConstructionObligationV2ProjectorSourceBindingV1)
from .stage_p_construction_obligation_v2_runner_protocol_codec_v1 import RunnerRequestV1
from .stage_p_construction_obligation_v2_runner_protocol_contract_v1 import RUNNER_PROTOCOL_IDENTITY,STATIC_EXECUTOR_BINDING_IDENTITY
from .stage_p_construction_obligation_v2_zero_model_callback_adapter_v1 import (
 ADAPTER_IDENTITY as V1_ADAPTER_IDENTITY,ConstructionObligationV2ZeroModelCallbackAdapterV1,
 ZeroModelCallbackDecisionV1)

ADAPTER_IDENTITY="97d50000a06ac878c425e1b7be44ad67f934d6a31d10d0f9150d205673f6b647"

class ConstructionObligationV2RequestBoundCallbackAdapterV1_1:
 def __init__(self,*,request:RunnerRequestV1,source_binding:ConstructionObligationV2ProjectorSourceBindingV1,token_pieces:Mapping[int,str])->None:
  if type(request)is not RunnerRequestV1:raise TypeError("CONSTRUCTION_OBLIGATION_V2_RUNNER_REQUEST_EXACT_TYPE_REQUIRED")
  if type(source_binding)is not ConstructionObligationV2ProjectorSourceBindingV1:raise TypeError("CONSTRUCTION_OBLIGATION_V2_SOURCE_BINDING_EXACT_TYPE_REQUIRED")
  if request.source_context_identity!=source_binding.source_context_identity:raise ValueError("CONSTRUCTION_OBLIGATION_V2_CALLBACK_REQUEST_CONTEXT_MISMATCH")
  self.request=request;self._base=ConstructionObligationV2ZeroModelCallbackAdapterV1(source_binding=source_binding,token_pieces=token_pieces)
 def project(self,*,generated_token_ids:Sequence[int],decode:Callable[[Sequence[int]],str])->ZeroModelCallbackDecisionV1:
  decision=self._base.project(generated_token_ids=generated_token_ids,decode=decode)
  if decision.no_legal_token_receipt is None:return decision
  prior=json.loads(decision.no_legal_token_receipt)
  value={"schema_name":prior["schema_name"],"schema_version":prior["schema_version"],
   "protocol_identity":RUNNER_PROTOCOL_IDENTITY,"projector_freeze_identity":PROJECTOR_FREEZE_IDENTITY,
   "tokenizer_identity":TOKENIZER_IDENTITY,"decoder_identity":DECODER_IDENTITY,
   "provider_request_id":self.request.provider_request_id,"source_context_identity":self.request.source_context_identity,
   "generated_prefix_sha256":prior["generated_prefix_sha256"],"generated_token_count":prior["generated_token_count"],
   "character_state_identity":prior["character_state_identity"],"dfa_mode":prior["dfa_mode"],
   "terminal":False,"allowed_token_count":0,"failure_code":"NO_LEGAL_TOKEN_NONTERMINAL","receipt_identity":""}
  value["receipt_identity"]=hashlib.sha256(_canonical({k:v for k,v in value.items() if k!="receipt_identity"})).hexdigest()
  return ZeroModelCallbackDecisionV1((),decision.projection_receipt,_canonical(value))

def request_bound_adapter_instance_identity_v1(adapter:ConstructionObligationV2RequestBoundCallbackAdapterV1_1)->str:
 if type(adapter)is not ConstructionObligationV2RequestBoundCallbackAdapterV1_1:raise TypeError("CONSTRUCTION_OBLIGATION_V2_REQUEST_BOUND_ADAPTER_EXACT_TYPE_REQUIRED")
 return hashlib.sha256("\n".join(("STAGE_P_CONSTRUCTION_OBLIGATION_V2_REQUEST_BOUND_CALLBACK_INSTANCE_V1_1",
  ADAPTER_IDENTITY,V1_ADAPTER_IDENTITY,RUNNER_PROTOCOL_IDENTITY,STATIC_EXECUTOR_BINDING_IDENTITY,
  adapter.request.provider_request_id,adapter.request.source_context_identity,adapter.request.host_payload_sha256)).encode()).hexdigest()
def _canonical(value):return (json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
__all__=("ADAPTER_IDENTITY","ConstructionObligationV2RequestBoundCallbackAdapterV1_1","request_bound_adapter_instance_identity_v1")
