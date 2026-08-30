"""Canonical zero-execution codec for the frozen V2 runner protocol."""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Mapping

from .stage_p_construction_obligation_v2_host_wsl_payload_contract_v1 import (
    CONTRACT_IDENTITY as HOST_PAYLOAD_CONTRACT_IDENTITY,
    parse_construction_obligation_v2_host_wsl_payload_v1)
from .stage_p_construction_obligation_v2_runner_protocol_contract_v1 import (
    DECODER_IDENTITY, PROJECTOR_FREEZE_IDENTITY, RUNNER_PROTOCOL_IDENTITY,
    STATIC_EXECUTOR_BINDING_IDENTITY, TOKENIZER_IDENTITY)
from .stage_p_construction_obligation_v2_static_executor_binding_v1 import (
    ConstructionObligationV2StaticExecutorBindingV1)


CODEC_IDENTITY = "09de75b7ecc52dedde19bf1f773c52ecf5a0a9da72da30a28113778b3867398f"
_VERSION = "1.0.0-evaluation.1"


@dataclass(frozen=True, slots=True)
class RunnerRequestV1:
    provider_request_id: str
    source_context_identity: str
    host_payload_sha256: str
    host_payload: bytes
    max_output_tokens: int


def build_runner_request_v1(*, raw_host_payload: bytes,
                            static_binding: ConstructionObligationV2StaticExecutorBindingV1) -> bytes:
    if type(static_binding) is not ConstructionObligationV2StaticExecutorBindingV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_STATIC_BINDING_EXACT_TYPE_REQUIRED")
    host = parse_construction_obligation_v2_host_wsl_payload_v1(raw_payload=raw_host_payload)
    digest = hashlib.sha256(raw_host_payload).hexdigest()
    if (static_binding.static_binding_identity != STATIC_EXECUTOR_BINDING_IDENTITY or
            static_binding.host_payload_sha256 != digest or
            static_binding.provider_request_id != host.provider_request_id or
            static_binding.source_context_identity != host.source_context_identity):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNNER_REQUEST_BINDING_MISMATCH")
    return _canonical({"schema_name":"pastila-semantic-admission-v2-construction-obligation-v2-runner-request",
        "schema_version":_VERSION,"protocol_identity":RUNNER_PROTOCOL_IDENTITY,
        "host_payload_contract_identity":HOST_PAYLOAD_CONTRACT_IDENTITY,
        "static_executor_binding_identity":STATIC_EXECUTOR_BINDING_IDENTITY,
        "host_payload_sha256":digest,"host_payload_utf8_base64":base64.b64encode(raw_host_payload).decode("ascii"),
        "provider_request_id":host.provider_request_id,"source_context_identity":host.source_context_identity,
        "max_output_tokens":host.max_output_tokens})


def parse_runner_request_v1(*, raw_request: bytes) -> RunnerRequestV1:
    value = _object(raw_request, "RUNNER_REQUEST")
    required={"schema_name","schema_version","protocol_identity","host_payload_contract_identity",
              "static_executor_binding_identity","host_payload_sha256","host_payload_utf8_base64",
              "provider_request_id","source_context_identity","max_output_tokens"}
    if set(value)!=required or (value["schema_name"],value["schema_version"],value["protocol_identity"],
       value["host_payload_contract_identity"],value["static_executor_binding_identity"]) != (
       "pastila-semantic-admission-v2-construction-obligation-v2-runner-request",_VERSION,
       RUNNER_PROTOCOL_IDENTITY,HOST_PAYLOAD_CONTRACT_IDENTITY,STATIC_EXECUTOR_BINDING_IDENTITY):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNNER_REQUEST_IDENTITY_MISMATCH")
    host_raw=_b64(value["host_payload_utf8_base64"],"RUNNER_REQUEST")
    if hashlib.sha256(host_raw).hexdigest()!=value["host_payload_sha256"]:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNNER_REQUEST_HASH_MISMATCH")
    host=parse_construction_obligation_v2_host_wsl_payload_v1(raw_payload=host_raw)
    if (value["provider_request_id"],value["source_context_identity"],value["max_output_tokens"]) != (
            host.provider_request_id,host.source_context_identity,host.max_output_tokens):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNNER_REQUEST_HOST_MISMATCH")
    if raw_request!=_canonical(value): raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNNER_REQUEST_NOT_CANONICAL")
    return RunnerRequestV1(host.provider_request_id,host.source_context_identity,
                           value["host_payload_sha256"],host_raw,host.max_output_tokens)


def build_lifecycle_event_v1(*, request: RunnerRequestV1, sequence: int, event: str,
                             detail: Mapping[str, object], previous_event_identity: str|None) -> bytes:
    events=("REQUEST_VALIDATED","TOKENIZER_IDENTITY_VALIDATED","PROJECTOR_CONSTRUCTED",
            "MODEL_LOAD_STARTED","MODEL_LOAD_COMPLETED","GENERATION_STARTED","NO_LEGAL_TOKEN",
            "TERMINAL_EOS","EXECUTION_FAILED")
    if type(sequence)is not int or sequence<0 or event not in events or (sequence==0)!=(previous_event_identity is None):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_LIFECYCLE_CHAIN_INVALID")
    detail_sha=hashlib.sha256(_canonical(dict(detail))).hexdigest()
    value={"schema_name":"pastila-semantic-admission-v2-construction-obligation-v2-runner-lifecycle-event",
           "schema_version":_VERSION,"protocol_identity":RUNNER_PROTOCOL_IDENTITY,
           "provider_request_id":request.provider_request_id,"sequence":sequence,"event":event,
           "detail_sha256":detail_sha,"previous_event_identity":previous_event_identity,"event_identity":""}
    value["event_identity"]=hashlib.sha256(_canonical({k:v for k,v in value.items() if k!="event_identity"})).hexdigest()
    return _canonical(value)


def validate_no_legal_token_receipt_v1(*, raw_receipt: bytes, request: RunnerRequestV1) -> str:
    value=_object(raw_receipt,"NO_LEGAL_TOKEN_RECEIPT")
    common={"schema_name","schema_version","protocol_identity","projector_freeze_identity",
      "tokenizer_identity","decoder_identity","provider_request_id","source_context_identity",
      "generated_prefix_sha256","generated_token_count","character_state_identity","dfa_mode",
      "terminal","allowed_token_count","failure_code","receipt_identity"}
    extended=common|{"projector_terminal","projector_reason_code",
      "authority_receipt_identity","projector_decoded_sha256",
      "generated_token_ids","decoded_prefix_utf8_base64",
      "decoded_prefix_sha256","decoded_prefix_utf8_bytes",
      "terminal_candidate_utf8_base64","terminal_candidate_sha256",
      "terminal_candidate_utf8_bytes"}
    if set(value) not in (common,extended) or (value["schema_name"],value["protocol_identity"],
      value["projector_freeze_identity"],value["tokenizer_identity"],value["decoder_identity"]) != (
      "pastila-semantic-admission-v2-construction-obligation-v2-no-legal-token-receipt",
      RUNNER_PROTOCOL_IDENTITY,PROJECTOR_FREEZE_IDENTITY,TOKENIZER_IDENTITY,DECODER_IDENTITY):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_NO_LEGAL_TOKEN_IDENTITY_MISMATCH")
    if (value["provider_request_id"],value["source_context_identity"],value["terminal"],
        value["allowed_token_count"]) != (request.provider_request_id,
        request.source_context_identity,False,0):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_NO_LEGAL_TOKEN_BINDING_MISMATCH")
    if set(value)==common:
        if (value["schema_version"] != _VERSION
                or value["failure_code"] != "NO_LEGAL_TOKEN_NONTERMINAL"):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_NO_LEGAL_TOKEN_CLASSIFICATION_MISMATCH")
    elif (value["schema_version"] != "1.2.1"
            or type(value["projector_terminal"]) is not bool
            or type(value["projector_reason_code"]) is not str
            or not value["projector_reason_code"]
            or value["failure_code"] != (
                "SEMANTIC_COMPLETENESS_EOS_WITHHELD"
                if value["projector_terminal"]
                else "TOKENIZATION_DEAD_NO_VALID_TOKEN")):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_NO_LEGAL_TOKEN_CLASSIFICATION_MISMATCH")
    if set(value)==extended:
        if (type(value["authority_receipt_identity"]) is not str
                or len(value["authority_receipt_identity"]) != 64
                or type(value["projector_decoded_sha256"]) is not str
                or len(value["projector_decoded_sha256"]) != 64):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_NO_LEGAL_TOKEN_CHAIN_INVALID")
        expected_character_state=hashlib.sha256("\n".join((
            value["authority_receipt_identity"], value["source_context_identity"],
            value["projector_decoded_sha256"], value["dfa_mode"],
            str(value["projector_terminal"]))).encode()).hexdigest()
        if value["character_state_identity"] != expected_character_state:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_NO_LEGAL_TOKEN_CHAIN_INVALID")
        if (type(value["generated_token_ids"]) is not list
                or any(type(item) is not int or item < 0
                       for item in value["generated_token_ids"])
                or len(value["generated_token_ids"]) != value["generated_token_count"]
                or hashlib.sha256(json.dumps(
                    tuple(value["generated_token_ids"]),
                    separators=(",", ":")).encode()).hexdigest()
                    != value["generated_prefix_sha256"]):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_GENERATED_HISTORY_IDENTITY_MISMATCH")
        if (type(value["decoded_prefix_utf8_base64"]) is not str
                or type(value["decoded_prefix_sha256"]) is not str
                or type(value["decoded_prefix_utf8_bytes"]) is not int):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_DECODED_PREFIX_MISSING")
        decoded_prefix=_b64(value["decoded_prefix_utf8_base64"],"DECODED_PREFIX")
        try:decoded_prefix.decode("utf-8",errors="strict")
        except UnicodeDecodeError as exc:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_DECODED_PREFIX_UTF8_INVALID") from exc
        if (len(decoded_prefix)!=value["decoded_prefix_utf8_bytes"]
                or hashlib.sha256(decoded_prefix).hexdigest()!=value["decoded_prefix_sha256"]
                or value["decoded_prefix_sha256"]!=value["projector_decoded_sha256"]):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_DECODED_PREFIX_IDENTITY_MISMATCH")
        candidate_fields=(value["terminal_candidate_utf8_base64"],
                          value["terminal_candidate_sha256"],
                          value["terminal_candidate_utf8_bytes"])
        if value["projector_terminal"]:
            if (type(candidate_fields[0]) is not str
                    or type(candidate_fields[1]) is not str
                    or type(candidate_fields[2]) is not int):
                raise ValueError("CONSTRUCTION_OBLIGATION_V2_TERMINAL_CANDIDATE_MISSING")
            candidate=_b64(candidate_fields[0],"TERMINAL_CANDIDATE")
            try:candidate.decode("utf-8",errors="strict")
            except UnicodeDecodeError as exc:
                raise ValueError("CONSTRUCTION_OBLIGATION_V2_TERMINAL_CANDIDATE_UTF8_INVALID") from exc
            if (len(candidate)!=candidate_fields[2]
                    or hashlib.sha256(candidate).hexdigest()!=candidate_fields[1]
                    or candidate_fields[1] != value["projector_decoded_sha256"]):
                raise ValueError("CONSTRUCTION_OBLIGATION_V2_TERMINAL_CANDIDATE_IDENTITY_MISMATCH")
        elif candidate_fields != (None,None,None):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_NONTERMINAL_CANDIDATE_FORBIDDEN")
    expected=hashlib.sha256(_canonical({k:v for k,v in value.items() if k!="receipt_identity"})).hexdigest()
    if value["receipt_identity"]!=expected or raw_receipt!=_canonical(value):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_NO_LEGAL_TOKEN_SEAL_MISMATCH")
    return expected


def build_runner_result_v1(*, request: RunnerRequestV1, status: str,
                           lifecycle_terminal_event_identity: str, output: bytes|None=None,
                           no_legal_token_receipt_identity: str|None=None,
                           execution_failure_code: str|None=None) -> bytes:
    terminal=status=="TERMINAL_OUTPUT"
    valid=((terminal and type(output)is bytes and bool(output) and no_legal_token_receipt_identity is None and execution_failure_code is None)
      or (status=="CONSTRAINT_LIVENESS_FAILURE" and output is None and type(no_legal_token_receipt_identity)is str and execution_failure_code is None)
      or (status=="EXECUTION_FAILURE" and output is None and no_legal_token_receipt_identity is None and type(execution_failure_code)is str))
    if not valid: raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNNER_RESULT_BRANCH_INVALID")
    value={"schema_name":"pastila-semantic-admission-v2-construction-obligation-v2-runner-result",
      "schema_version":_VERSION,"protocol_identity":RUNNER_PROTOCOL_IDENTITY,
      "provider_request_id":request.provider_request_id,"source_context_identity":request.source_context_identity,
      "status":status,"output_utf8_base64":base64.b64encode(output).decode("ascii") if output else None,
      "output_sha256":hashlib.sha256(output).hexdigest() if output else None,"terminal_eos":terminal,
      "no_legal_token_receipt_identity":no_legal_token_receipt_identity,
      "execution_failure_code":execution_failure_code,
      "lifecycle_terminal_event_identity":lifecycle_terminal_event_identity,"result_identity":""}
    value["result_identity"]=hashlib.sha256(_canonical({k:v for k,v in value.items() if k!="result_identity"})).hexdigest()
    return _canonical(value)


def _object(raw,label):
    if type(raw)is not bytes or not raw: raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_BYTES_REQUIRED")
    try:value=json.loads(raw.decode("utf-8",errors="strict"))
    except Exception as exc:raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_JSON_INVALID") from exc
    if type(value)is not dict:raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_SHAPE_INVALID")
    return value
def _b64(value,label):
    try:raw=base64.b64decode(value,validate=True)
    except Exception as exc:raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_BASE64_INVALID") from exc
    if base64.b64encode(raw).decode("ascii")!=value:raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_BASE64_INVALID")
    return raw
def _canonical(value):
    return (json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()

__all__=("CODEC_IDENTITY","RunnerRequestV1","build_runner_request_v1","parse_runner_request_v1",
         "build_lifecycle_event_v1","validate_no_legal_token_receipt_v1","build_runner_result_v1")
