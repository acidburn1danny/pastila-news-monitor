"""Canonical zero-execution host-to-WSL payload for Construction-Obligation V2."""
from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass

from .stage_p_construction_obligation_v2_projector_binding_v1 import (
    DECODER_IDENTITY,
    PROJECTOR_FREEZE_IDENTITY,
    TOKENIZER_IDENTITY,
)
from .stage_p_construction_obligation_v2_provider_execution_request_binding_v1 import (
    BINDING_IDENTITY as PROVIDER_EXECUTION_REQUEST_BINDING_IDENTITY,
    ConstructionObligationV2ProviderExecutionRequestBindingV1,
)
from .stage_p_construction_obligation_v2_request_renderer_v1 import (
    DATA_BEGIN,
    DATA_END,
    ConstructionObligationV2RenderedRequestV1,
)
from .stage_p_construction_obligation_v2_static_payload_binding_v1 import (
    STATIC_PROJECTOR_BINDING_IDENTITY,
    parse_construction_obligation_v2_static_payload_v1,
)


DESIGN_IDENTITY = "31a82ff316f69f98f7ba5df0e53bf5c6262fad5068fb3580430b967e5930658f"
CONTRACT_IDENTITY = "1dc94cda37c270fda49bca7b430bbad4970b3afadf2d0e348cfc3479161e1a49"
MODEL_IDENTITY = "pastila-editor-core-v1.2-experimental"
SCHEMA_NAME = "pastila-semantic-admission-v2-stage-p-construction-obligation-v2-host-wsl-payload"
SCHEMA_VERSION = "1.0.0-evaluation.1"
MAX_OUTPUT_TOKENS = 3200


@dataclass(frozen=True, slots=True)
class ConstructionObligationV2HostWslPayloadV1:
    payload_identity: str
    application_request_identity: str
    provider_request_id: str
    provider_request_envelope_identity: str
    execution_plan_identity: str
    rendered_request_identity: str
    rendered_prompt_sha256: str
    rendered_prompt: str
    static_payload_sha256: str
    static_payload: bytes
    source_context_identity: str
    max_output_tokens: int


def build_construction_obligation_v2_host_wsl_payload_v1(
    *,
    execution_binding: ConstructionObligationV2ProviderExecutionRequestBindingV1,
    rendered_request: ConstructionObligationV2RenderedRequestV1,
    canonical_static_payload: bytes,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
) -> bytes:
    """Build canonical bytes only; this function has no launch capability."""
    values = _validated_values(
        execution_binding, rendered_request, canonical_static_payload, max_output_tokens
    )
    value = _json_value(*values)
    return _canonical_bytes(value)


def parse_construction_obligation_v2_host_wsl_payload_v1(
    *, raw_payload: bytes,
) -> ConstructionObligationV2HostWslPayloadV1:
    if type(raw_payload) is not bytes or not raw_payload:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_HOST_WSL_PAYLOAD_BYTES_REQUIRED")
    try:
        value = json.loads(raw_payload.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_HOST_WSL_PAYLOAD_JSON_INVALID") from exc
    required = {
        "schema_name", "schema_version", "contract_identity", "design_identity",
        "projector_freeze_identity", "static_projector_binding_identity",
        "provider_execution_request_binding_identity", "model_identity",
        "tokenizer_identity", "decoder_identity", "application_request_identity",
        "provider_request_id", "provider_request_envelope_identity",
        "execution_plan_identity", "rendered_request_identity",
        "rendered_prompt_utf8_base64", "rendered_prompt_sha256",
        "static_payload_utf8_base64", "static_payload_sha256",
        "source_context_identity", "max_output_tokens", "payload_identity",
    }
    if type(value) is not dict or set(value) != required:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_HOST_WSL_PAYLOAD_SHAPE_INVALID")
    constants = (
        value["schema_name"], value["schema_version"], value["contract_identity"],
        value["design_identity"], value["projector_freeze_identity"],
        value["static_projector_binding_identity"],
        value["provider_execution_request_binding_identity"], value["model_identity"],
        value["tokenizer_identity"], value["decoder_identity"],
    )
    expected = (
        SCHEMA_NAME, SCHEMA_VERSION, CONTRACT_IDENTITY, DESIGN_IDENTITY,
        PROJECTOR_FREEZE_IDENTITY, STATIC_PROJECTOR_BINDING_IDENTITY,
        PROVIDER_EXECUTION_REQUEST_BINDING_IDENTITY, MODEL_IDENTITY,
        TOKENIZER_IDENTITY, DECODER_IDENTITY,
    )
    if constants != expected:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_HOST_WSL_PAYLOAD_IDENTITY_MISMATCH")
    prompt = _decode(value["rendered_prompt_utf8_base64"], "RENDERED_PROMPT")
    static = _decode(value["static_payload_utf8_base64"], "STATIC_PAYLOAD")
    if (
        hashlib.sha256(prompt).hexdigest() != value["rendered_prompt_sha256"]
        or hashlib.sha256(static).hexdigest() != value["static_payload_sha256"]
    ):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_HOST_WSL_PAYLOAD_HASH_MISMATCH")
    parsed_static = parse_construction_obligation_v2_static_payload_v1(raw_payload=static)
    _verify_embedded_static(prompt, static)
    if parsed_static.source_binding.source_context_identity != value["source_context_identity"]:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_HOST_WSL_PAYLOAD_CONTEXT_MISMATCH")
    text_fields = (
        "application_request_identity", "provider_request_id",
        "provider_request_envelope_identity", "execution_plan_identity",
        "rendered_request_identity", "source_context_identity",
    )
    if any(type(value[name]) is not str or not value[name] for name in text_fields):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_HOST_WSL_PAYLOAD_FIELD_INVALID")
    if type(value["max_output_tokens"]) is not int or not 0 < value["max_output_tokens"] <= MAX_OUTPUT_TOKENS:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_HOST_WSL_PAYLOAD_TOKEN_CEILING_INVALID")
    if value["payload_identity"] != _payload_identity(value):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_HOST_WSL_PAYLOAD_SEAL_MISMATCH")
    if raw_payload != _canonical_bytes(value):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_HOST_WSL_PAYLOAD_NOT_CANONICAL")
    return ConstructionObligationV2HostWslPayloadV1(
        value["payload_identity"], value["application_request_identity"],
        value["provider_request_id"], value["provider_request_envelope_identity"],
        value["execution_plan_identity"], value["rendered_request_identity"],
        value["rendered_prompt_sha256"], prompt.decode("utf-8", errors="strict"),
        value["static_payload_sha256"], static, value["source_context_identity"],
        value["max_output_tokens"],
    )


def _validated_values(execution_binding, rendered_request, static, max_output_tokens):
    if type(execution_binding) is not ConstructionObligationV2ProviderExecutionRequestBindingV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_EXECUTION_BINDING_EXACT_TYPE_REQUIRED")
    if type(rendered_request) is not ConstructionObligationV2RenderedRequestV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_RENDERED_REQUEST_EXACT_TYPE_REQUIRED")
    if type(static) is not bytes or not static:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_STATIC_PAYLOAD_BYTES_REQUIRED")
    if type(max_output_tokens) is not int or not 0 < max_output_tokens <= MAX_OUTPUT_TOKENS:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_HOST_WSL_PAYLOAD_TOKEN_CEILING_INVALID")
    if (
        execution_binding.binding_identity != PROVIDER_EXECUTION_REQUEST_BINDING_IDENTITY
        or execution_binding.projector_freeze_identity != PROJECTOR_FREEZE_IDENTITY
    ):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_EXECUTION_BINDING_IDENTITY_MISMATCH")
    parsed = parse_construction_obligation_v2_static_payload_v1(raw_payload=static)
    prompt = rendered_request.rendered_prompt.encode("utf-8")
    if (
        hashlib.sha256(prompt).hexdigest() != rendered_request.rendered_prompt_sha256
        or hashlib.sha256(static).hexdigest() != rendered_request.static_payload_sha256
    ):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RENDERED_REQUEST_HASH_MISMATCH")
    _verify_embedded_static(prompt, static)
    request = execution_binding.provider_execution_request
    units = request.request_intent.request_units
    if (
        len(units) != 1 or len(units[0].messages) != 1
        or units[0].messages[0].role != "generation"
        or units[0].messages[0].content != rendered_request.rendered_prompt
    ):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_EXECUTION_PROMPT_MISMATCH")
    return (
        execution_binding.application_request_identity, request.context.request_id,
        request.request_envelope.identity, request.request_intent.execution_plan_identity,
        rendered_request.request_identity, prompt, static,
        parsed.source_binding.source_context_identity, max_output_tokens,
    )


def _json_value(application_identity, request_id, envelope_identity, plan_identity,
                rendered_identity, prompt, static, context_identity, max_tokens):
    value = {
        "schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION,
        "contract_identity": CONTRACT_IDENTITY, "design_identity": DESIGN_IDENTITY,
        "projector_freeze_identity": PROJECTOR_FREEZE_IDENTITY,
        "static_projector_binding_identity": STATIC_PROJECTOR_BINDING_IDENTITY,
        "provider_execution_request_binding_identity": PROVIDER_EXECUTION_REQUEST_BINDING_IDENTITY,
        "model_identity": MODEL_IDENTITY, "tokenizer_identity": TOKENIZER_IDENTITY,
        "decoder_identity": DECODER_IDENTITY,
        "application_request_identity": application_identity,
        "provider_request_id": request_id,
        "provider_request_envelope_identity": envelope_identity,
        "execution_plan_identity": plan_identity,
        "rendered_request_identity": rendered_identity,
        "rendered_prompt_utf8_base64": base64.b64encode(prompt).decode("ascii"),
        "rendered_prompt_sha256": hashlib.sha256(prompt).hexdigest(),
        "static_payload_utf8_base64": base64.b64encode(static).decode("ascii"),
        "static_payload_sha256": hashlib.sha256(static).hexdigest(),
        "source_context_identity": context_identity, "max_output_tokens": max_tokens,
        "payload_identity": "",
    }
    value["payload_identity"] = _payload_identity(value)
    return value


def _payload_identity(value: dict[str, object]) -> str:
    sealed = {key: item for key, item in value.items() if key != "payload_identity"}
    return hashlib.sha256(_canonical_bytes(sealed)).hexdigest()


def _canonical_bytes(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def _decode(value: object, label: str) -> bytes:
    if type(value) is not str:
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_HOST_WSL_{label}_BASE64_INVALID")
    try:
        raw = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_HOST_WSL_{label}_BASE64_INVALID") from exc
    if base64.b64encode(raw).decode("ascii") != value:
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_HOST_WSL_{label}_BASE64_INVALID")
    return raw


def _verify_embedded_static(prompt: bytes, static: bytes) -> None:
    marker = b"\n" + DATA_BEGIN + b"\n"
    if prompt.count(marker) != 1 or prompt.count(DATA_END) != 1 or not prompt.endswith(DATA_END):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_HOST_WSL_PROMPT_DELIMITER_MISMATCH")
    if prompt.split(marker, 1)[1][:-len(DATA_END)] != static:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_HOST_WSL_STATIC_PAYLOAD_MISMATCH")


__all__ = (
    "CONTRACT_IDENTITY", "ConstructionObligationV2HostWslPayloadV1",
    "build_construction_obligation_v2_host_wsl_payload_v1",
    "parse_construction_obligation_v2_host_wsl_payload_v1",
)
