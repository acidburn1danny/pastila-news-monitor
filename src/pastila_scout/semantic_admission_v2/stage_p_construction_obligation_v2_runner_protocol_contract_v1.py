"""Canonical zero-execution runner protocol schemas for Construction-Obligation V2."""
from __future__ import annotations

import hashlib
import json
from typing import Final


HOST_PAYLOAD_CONTRACT_IDENTITY: Final = "1dc94cda37c270fda49bca7b430bbad4970b3afadf2d0e348cfc3479161e1a49"
STATIC_EXECUTOR_BINDING_IDENTITY: Final = "46265e64cfac4217493529020f7517d6af1f10d93f14a3fed2abd2cc6e8c4572"
PROJECTOR_FREEZE_IDENTITY: Final = "974d5e6257256d7397cb68f90952c66809a536cf5525cbef58b3bbfce6791587"
TOKENIZER_IDENTITY: Final = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
DECODER_IDENTITY: Final = "ministral-tokenizer-decode-skip-special-cleanup-false-v1"

_SHA = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
_IDENTITY = {"type": "string", "minLength": 1, "maxLength": 240}
_BASE64 = {"type": "string", "pattern": "^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$"}

_REQUEST_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:pastila:semantic-admission-v2:construction-obligation-v2:runner-request-v1",
    "type": "object", "additionalProperties": False,
    "required": ["schema_name", "schema_version", "protocol_identity",
                 "host_payload_contract_identity", "static_executor_binding_identity",
                 "host_payload_sha256", "host_payload_utf8_base64", "provider_request_id",
                 "source_context_identity", "max_output_tokens"],
    "properties": {
        "schema_name": {"const": "pastila-semantic-admission-v2-construction-obligation-v2-runner-request"},
        "schema_version": {"const": "1.0.0-evaluation.1"},
        "protocol_identity": _SHA,
        "host_payload_contract_identity": {"const": HOST_PAYLOAD_CONTRACT_IDENTITY},
        "static_executor_binding_identity": {"const": STATIC_EXECUTOR_BINDING_IDENTITY},
        "host_payload_sha256": _SHA, "host_payload_utf8_base64": _BASE64,
        "provider_request_id": _IDENTITY, "source_context_identity": _SHA,
        "max_output_tokens": {"type": "integer", "minimum": 1, "maximum": 3200},
    },
}

_NO_LEGAL_TOKEN_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:pastila:semantic-admission-v2:construction-obligation-v2:no-legal-token-receipt-v1",
    "type": "object", "additionalProperties": False,
    "required": ["schema_name", "schema_version", "protocol_identity",
                 "projector_freeze_identity", "tokenizer_identity", "decoder_identity",
                 "provider_request_id", "source_context_identity", "generated_prefix_sha256",
                 "generated_token_count", "character_state_identity", "dfa_mode",
                 "terminal", "allowed_token_count", "failure_code", "receipt_identity"],
    "properties": {
        "schema_name": {"const": "pastila-semantic-admission-v2-construction-obligation-v2-no-legal-token-receipt"},
        "schema_version": {"const": "1.0.0-evaluation.1"}, "protocol_identity": _SHA,
        "projector_freeze_identity": {"const": PROJECTOR_FREEZE_IDENTITY},
        "tokenizer_identity": {"const": TOKENIZER_IDENTITY},
        "decoder_identity": {"const": DECODER_IDENTITY},
        "provider_request_id": _IDENTITY, "source_context_identity": _SHA,
        "generated_prefix_sha256": _SHA,
        "generated_token_count": {"type": "integer", "minimum": 0},
        "character_state_identity": _SHA,
        "dfa_mode": {"enum": ["PREFIX", "DEAD"]},
        "terminal": {"const": False}, "allowed_token_count": {"const": 0},
        "failure_code": {"const": "NO_LEGAL_TOKEN_NONTERMINAL"},
        "receipt_identity": _SHA,
    },
}

_LIFECYCLE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:pastila:semantic-admission-v2:construction-obligation-v2:runner-lifecycle-event-v1",
    "type": "object", "additionalProperties": False,
    "required": ["schema_name", "schema_version", "protocol_identity", "provider_request_id",
                 "sequence", "event", "detail_sha256", "previous_event_identity", "event_identity"],
    "properties": {
        "schema_name": {"const": "pastila-semantic-admission-v2-construction-obligation-v2-runner-lifecycle-event"},
        "schema_version": {"const": "1.0.0-evaluation.1"}, "protocol_identity": _SHA,
        "provider_request_id": _IDENTITY, "sequence": {"type": "integer", "minimum": 0},
        "event": {"enum": ["REQUEST_VALIDATED", "TOKENIZER_IDENTITY_VALIDATED",
                            "PROJECTOR_CONSTRUCTED", "MODEL_LOAD_STARTED", "MODEL_LOAD_COMPLETED",
                            "GENERATION_STARTED", "NO_LEGAL_TOKEN", "TERMINAL_EOS", "EXECUTION_FAILED"]},
        "detail_sha256": _SHA,
        "previous_event_identity": {"oneOf": [{"type": "null"}, _SHA]},
        "event_identity": _SHA,
    },
}

_RESULT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:pastila:semantic-admission-v2:construction-obligation-v2:runner-result-v1",
    "type": "object", "additionalProperties": False,
    "required": ["schema_name", "schema_version", "protocol_identity", "provider_request_id",
                 "source_context_identity", "status", "output_utf8_base64", "output_sha256",
                 "terminal_eos", "no_legal_token_receipt_identity", "execution_failure_code",
                 "lifecycle_terminal_event_identity", "result_identity"],
    "properties": {
        "schema_name": {"const": "pastila-semantic-admission-v2-construction-obligation-v2-runner-result"},
        "schema_version": {"const": "1.0.0-evaluation.1"}, "protocol_identity": _SHA,
        "provider_request_id": _IDENTITY, "source_context_identity": _SHA,
        "status": {"enum": ["TERMINAL_OUTPUT", "CONSTRAINT_LIVENESS_FAILURE", "EXECUTION_FAILURE"]},
        "output_utf8_base64": {"oneOf": [{"type": "null"}, _BASE64]},
        "output_sha256": {"oneOf": [{"type": "null"}, _SHA]},
        "terminal_eos": {"type": "boolean"},
        "no_legal_token_receipt_identity": {"oneOf": [{"type": "null"}, _SHA]},
        "execution_failure_code": {"oneOf": [{"type": "null"}, _IDENTITY]},
        "lifecycle_terminal_event_identity": _SHA, "result_identity": _SHA,
    },
    "oneOf": [
        {"properties": {"status": {"const": "TERMINAL_OUTPUT"}, "output_utf8_base64": _BASE64,
                        "output_sha256": _SHA, "terminal_eos": {"const": True},
                        "no_legal_token_receipt_identity": {"type": "null"},
                        "execution_failure_code": {"type": "null"}}},
        {"properties": {"status": {"const": "CONSTRAINT_LIVENESS_FAILURE"},
                        "output_utf8_base64": {"type": "null"}, "output_sha256": {"type": "null"},
                        "terminal_eos": {"const": False}, "no_legal_token_receipt_identity": _SHA,
                        "execution_failure_code": {"type": "null"}}},
        {"properties": {"status": {"const": "EXECUTION_FAILURE"},
                        "output_utf8_base64": {"type": "null"}, "output_sha256": {"type": "null"},
                        "terminal_eos": {"const": False},
                        "no_legal_token_receipt_identity": {"type": "null"},
                        "execution_failure_code": _IDENTITY}},
    ],
}


def canonical_schema_bytes(name: str) -> bytes:
    """Return canonical bytes for one frozen protocol schema."""
    schemas = {"request": _REQUEST_SCHEMA, "result": _RESULT_SCHEMA,
               "lifecycle": _LIFECYCLE_SCHEMA, "no_legal_token": _NO_LEGAL_TOKEN_SCHEMA}
    if type(name) is not str or name not in schemas:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RUNNER_PROTOCOL_SCHEMA_NAME_INVALID")
    return (json.dumps(schemas[name], ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def schema_value(name: str) -> dict[str, object]:
    """Return an isolated copy so callers cannot mutate frozen module state."""
    return json.loads(canonical_schema_bytes(name))


SCHEMA_IDENTITIES: Final = {
    name: hashlib.sha256(canonical_schema_bytes(name)).hexdigest()
    for name in ("request", "result", "lifecycle", "no_legal_token")
}
RUNNER_PROTOCOL_IDENTITY: Final = hashlib.sha256("\n".join((
    "STAGE_P_CONSTRUCTION_OBLIGATION_V2_RUNNER_PROTOCOL_CONTRACT_V1",
    HOST_PAYLOAD_CONTRACT_IDENTITY, STATIC_EXECUTOR_BINDING_IDENTITY,
    PROJECTOR_FREEZE_IDENTITY, TOKENIZER_IDENTITY, DECODER_IDENTITY,
    *(SCHEMA_IDENTITIES[name] for name in ("request", "result", "lifecycle", "no_legal_token")),
    "APPEND_ONLY_LIFECYCLE", "FAIL_CLOSED_NO_LEGAL_TOKEN", "ZERO_EXECUTION",
)).encode()).hexdigest()


__all__ = ("RUNNER_PROTOCOL_IDENTITY", "SCHEMA_IDENTITIES", "canonical_schema_bytes", "schema_value")
