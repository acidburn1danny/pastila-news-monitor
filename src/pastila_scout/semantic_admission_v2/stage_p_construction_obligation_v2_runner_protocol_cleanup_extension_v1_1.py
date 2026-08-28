"""Supplemental cleanup/result protocol; frozen runner protocol V1 is unchanged."""
from __future__ import annotations

import hashlib
import json


CLEANUP_EXTENSION_IDENTITY = "4636f0937ebc620f3fe086e9ae69ee5e21884cbf6e73cbee69a90962dab1c136"
BASE_RUNNER_PROTOCOL_IDENTITY = "cb9f14284353fafba05094b005f3a97793dbb079e5bed81abacddaafb7d155bf"
RUNTIME_OPERATIONS_CONTRACT_IDENTITY = "cc97c93651f42998a0cd921a0e32ae3a78a04e4fe5580d06395232496b3b0483"


def build_cleanup_receipt_v1_1(
    *, provider_request_id: str, source_context_identity: str,
    worker_terminal_event_identity: str, cleanup_status: str,
    cleanup_failure_code: str | None,
) -> bytes:
    if cleanup_status not in {"CLEANUP_COMPLETED", "CLEANUP_FAILED"}:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_CLEANUP_STATUS_INVALID")
    if (cleanup_status == "CLEANUP_COMPLETED") != (cleanup_failure_code is None):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_CLEANUP_FAILURE_BINDING_INVALID")
    _identity(provider_request_id, "PROVIDER_REQUEST")
    _sha(source_context_identity, "SOURCE_CONTEXT")
    _sha(worker_terminal_event_identity, "WORKER_TERMINAL_EVENT")
    if cleanup_failure_code is not None:
        _identity(cleanup_failure_code, "CLEANUP_FAILURE")
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-cleanup-receipt-v1-1",
        "schema_version": "1.1.0",
        "cleanup_extension_identity": CLEANUP_EXTENSION_IDENTITY,
        "base_runner_protocol_identity": BASE_RUNNER_PROTOCOL_IDENTITY,
        "provider_request_id": provider_request_id,
        "source_context_identity": source_context_identity,
        "worker_terminal_event_identity": worker_terminal_event_identity,
        "cleanup_status": cleanup_status,
        "cleanup_failure_code": cleanup_failure_code,
        "receipt_identity": "",
    }
    value["receipt_identity"] = hashlib.sha256(_canonical(
        {key: item for key, item in value.items() if key != "receipt_identity"}
    )).hexdigest()
    return _canonical(value)


def build_result_envelope_v1_1(
    *, raw_base_runner_result: bytes, raw_cleanup_receipt: bytes,
    raw_partial_output: bytes | None,
) -> bytes:
    base = _object(raw_base_runner_result, "BASE_RESULT")
    cleanup = _object(raw_cleanup_receipt, "CLEANUP_RECEIPT")
    if (
        base.get("protocol_identity") != BASE_RUNNER_PROTOCOL_IDENTITY
        or base.get("schema_name") != "pastila-semantic-admission-v2-construction-obligation-v2-runner-result"
        or raw_base_runner_result != _canonical(base)
    ):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_BASE_RESULT_INVALID")
    cleanup_required = {
        "schema_name", "schema_version", "cleanup_extension_identity",
        "base_runner_protocol_identity", "provider_request_id",
        "source_context_identity", "worker_terminal_event_identity",
        "cleanup_status", "cleanup_failure_code", "receipt_identity",
    }
    expected_cleanup_identity = hashlib.sha256(_canonical(
        {key: item for key, item in cleanup.items() if key != "receipt_identity"}
    )).hexdigest()
    if (
        set(cleanup) != cleanup_required
        or cleanup.get("cleanup_extension_identity") != CLEANUP_EXTENSION_IDENTITY
        or cleanup.get("base_runner_protocol_identity") != BASE_RUNNER_PROTOCOL_IDENTITY
        or cleanup.get("receipt_identity") != expected_cleanup_identity
        or raw_cleanup_receipt != _canonical(cleanup)
        or cleanup.get("provider_request_id") != base.get("provider_request_id")
        or cleanup.get("source_context_identity") != base.get("source_context_identity")
        or cleanup.get("worker_terminal_event_identity") != base.get("lifecycle_terminal_event_identity")
    ):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_CLEANUP_RESULT_BINDING_MISMATCH")
    if base.get("status") == "TERMINAL_OUTPUT" and cleanup["cleanup_status"] != "CLEANUP_COMPLETED":
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_SUCCESS_WITHOUT_CLEANUP_FORBIDDEN")
    if cleanup["cleanup_status"] == "CLEANUP_FAILED" and base.get("status") != "EXECUTION_FAILURE":
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_CLEANUP_FAILURE_CLASSIFICATION_MISMATCH")
    if raw_partial_output is not None and base.get("output_utf8_base64") is not None:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_PARTIAL_OUTPUT_SEMANTIC_AUTHORITY_FORBIDDEN")
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-runner-result-envelope-v1-1",
        "schema_version": "1.1.0",
        "cleanup_extension_identity": CLEANUP_EXTENSION_IDENTITY,
        "base_runner_protocol_identity": BASE_RUNNER_PROTOCOL_IDENTITY,
        "base_result_identity": base["result_identity"],
        "cleanup_receipt_identity": cleanup["receipt_identity"],
        "partial_output_sha256": (
            hashlib.sha256(raw_partial_output).hexdigest()
            if raw_partial_output is not None else None
        ),
        "partial_output_semantic_authority": False,
        "envelope_identity": "",
    }
    value["envelope_identity"] = hashlib.sha256(_canonical(
        {key: item for key, item in value.items() if key != "envelope_identity"}
    )).hexdigest()
    return _canonical(value)


def _object(raw: bytes, label: str) -> dict[str, object]:
    if type(raw) is not bytes or not raw:
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_BYTES_REQUIRED")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_JSON_INVALID") from exc
    if type(value) is not dict:
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_SHAPE_INVALID")
    return value


def _identity(value: object, label: str) -> None:
    if type(value) is not str or not value or len(value) > 240:
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_IDENTITY_INVALID")


def _sha(value: object, label: str) -> None:
    if (type(value) is not str or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)):
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_SHA256_INVALID")


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "BASE_RUNNER_PROTOCOL_IDENTITY", "CLEANUP_EXTENSION_IDENTITY",
    "build_cleanup_receipt_v1_1", "build_result_envelope_v1_1",
)
