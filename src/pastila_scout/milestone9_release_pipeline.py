"""Phase-separated release records for the Core V2 Milestone 9 proof chain."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .milestone9_proof_boundary import (
    ARTIFACT_RETENTION_DAYS,
    SCHEDULE_RULE,
    SCHEDULER_DELAY_HOURS,
    derive_schedule,
)
from .semantic_authority_capture_orchestrator_v2_3_7 import canonical
from .semantic_authority_rfc3161_verifier_v2_3_13 import (
    OPENSSL_EXECUTABLE_SHA256,
    RUNTIME_IMAGE_INDEX_SHA256,
)


RELEASE_SCHEMA = "PASTILA_MILESTONE_9_RELEASE_V1"
VALIDATION_SCHEMA = "PASTILA_MILESTONE_9_REQUEST_VALIDATION_V1"
PROOF_SCHEMA = "PASTILA_MILESTONE_9_RFC3161_PROOF_V1"
TSA_ENDPOINT = "http://timestamp.digicert.com"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def compute_identity(value: Mapping[str, object], field: str) -> str:
    body = dict(value)
    body.pop(field, None)
    return sha256(canonical(body))


def identity(value: Mapping[str, object], field: str) -> str:
    body = dict(value)
    claimed = body.pop(field, None)
    actual = compute_identity(body, field)
    if claimed != actual:
        raise ValueError(f"invalid {field}")
    return actual


def validate_release(value: Mapping[str, object]) -> str:
    required = {
        "schema", "freeze_commit", "freeze_tree", "freeze_epoch",
        "workflow_template_sha256", "pipeline_sha256", "schedule_rule",
        "scheduled_utc", "schedule_cron", "scheduler_delay_hours",
        "artifact_retention_days", "runtime_image_index_sha256",
        "openssl_executable_sha256", "tsa_endpoint", "release_identity",
    }
    if set(value) != required or value["schema"] != RELEASE_SCHEMA:
        raise ValueError("release schema")
    if not HEX40.fullmatch(str(value["freeze_commit"])):
        raise ValueError("freeze commit")
    if not HEX40.fullmatch(str(value["freeze_tree"])):
        raise ValueError("freeze tree")
    if not isinstance(value["freeze_epoch"], int) or isinstance(value["freeze_epoch"], bool):
        raise ValueError("freeze epoch")
    fixed = {
        "schedule_rule": SCHEDULE_RULE,
        "scheduler_delay_hours": SCHEDULER_DELAY_HOURS,
        "artifact_retention_days": ARTIFACT_RETENTION_DAYS,
        "runtime_image_index_sha256": RUNTIME_IMAGE_INDEX_SHA256,
        "openssl_executable_sha256": OPENSSL_EXECUTABLE_SHA256,
        "tsa_endpoint": TSA_ENDPOINT,
    }
    if any(value[key] != expected for key, expected in fixed.items()):
        raise ValueError("release authority")
    if (value["scheduled_utc"], value["schedule_cron"]) != derive_schedule(value["freeze_epoch"]):
        raise ValueError("release schedule derivation")
    for key in ("workflow_template_sha256", "pipeline_sha256"):
        if not HEX64.fullmatch(str(value[key])):
            raise ValueError("release digest")
    return identity(value, "release_identity")


@dataclass(frozen=True)
class ValidatedRequest:
    query: bytes
    validation: Mapping[str, object]


def bind_validated_request(
    release: Mapping[str, object], query: bytes, validation: Mapping[str, object]
) -> ValidatedRequest:
    release_identity = validate_release(release)
    required = {
        "schema", "release_identity", "query_sha256", "query_length",
        "runtime_image_index_sha256", "openssl_executable_sha256",
        "offline_network", "query_semantics", "validation_identity",
    }
    if set(validation) != required or validation["schema"] != VALIDATION_SCHEMA:
        raise ValueError("validation schema")
    if validation["release_identity"] != release_identity:
        raise ValueError("validation release")
    if validation["query_sha256"] != sha256(query) or validation["query_length"] != len(query):
        raise ValueError("validation query bytes")
    fixed = {
        "runtime_image_index_sha256": RUNTIME_IMAGE_INDEX_SHA256,
        "openssl_executable_sha256": OPENSSL_EXECUTABLE_SHA256,
        "offline_network": "NETWORK_NONE",
        "query_semantics": "SHA256_IMPRINT_NONCE_CERTREQ_NO_POLICY_NO_EXTENSIONS",
    }
    if any(validation[key] != expected for key, expected in fixed.items()):
        raise ValueError("validation authority")
    identity(validation, "validation_identity")
    return ValidatedRequest(bytes(query), dict(validation))


def validate_proof(
    release: Mapping[str, object], validation: Mapping[str, object],
    query: bytes, receipt: bytes, proof: Mapping[str, object]
) -> str:
    request = bind_validated_request(release, query, validation)
    required = {
        "schema", "release_identity", "validation_identity", "query_sha256",
        "receipt_sha256", "receipt_length", "http_status", "content_type",
        "attempts", "redirects", "offline_verification", "proof_identity",
    }
    if set(proof) != required or proof["schema"] != PROOF_SCHEMA:
        raise ValueError("proof schema")
    fixed = {
        "release_identity": release["release_identity"],
        "validation_identity": request.validation["validation_identity"],
        "query_sha256": sha256(query),
        "receipt_sha256": sha256(receipt),
        "receipt_length": len(receipt),
        "http_status": 200,
        "content_type": "application/timestamp-reply",
        "attempts": 1,
        "redirects": 0,
        "offline_verification": "PASS",
    }
    if any(proof[key] != expected for key, expected in fixed.items()):
        raise ValueError("proof authority")
    return identity(proof, "proof_identity")


def load_canonical(path: Path) -> Mapping[str, object]:
    if path.is_symlink():
        raise ValueError("record symlink")
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict) or raw != canonical(value) + b"\n":
        raise ValueError("record serialization")
    return value
