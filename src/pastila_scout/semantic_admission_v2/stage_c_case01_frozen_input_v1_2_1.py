"""Exact frozen-input admission for Case 01 Stage C V1.2.1.

This module is pure validation.  It has no provider, process, WSL, model, or
generation edge and cannot regenerate Stage P.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .immutable_source_span_reference_v1 import ImmutableUtf8SourceV1, SourceRoleV1
from .stage_p_construction_obligation_semantic_completeness_v1 import (
    CASE01_CANONICAL_POLICY_IDENTITY,
    SemanticCompletenessAdmissionV1,
    SemanticCompletenessPolicyV1,
)

CASE_ID = "HMCV1-SASC-01"
EVIDENCE_COMMIT = "2c5ce79396ecd14df16a452e8ce46ff65b394f54"
EVALUATION_COMMIT = "e0ca07356e507ab02b1e7e94908ff6cf00adbe71"
CLOSURE_COMMIT = "a95ab38c4b72776f41397292e97a7257d2832aaf"
RAW_OUTPUT_SHA256 = "e5ca27cf26a4752a23460187fe315b1e5eb5fe1822b194d21a5371cca232e19d"
EVALUATION_RECEIPT_IDENTITY = "77cfab340bf4a4a490f34ae80642655d0127934f0c52fa852dd8e4154298ca4b"
EVALUATION_RECEIPT_SHA256 = "d86a309e2ee0741d49049a010e0ae50adf8ae7061dd768daadebb63e8e1b6096"
CLOSURE_RECEIPT_IDENTITY = "5b772bd9e385d3f47a003cf7014f069f25d80147a99af953f920418018b060e7"
SOURCE_CONTEXT_IDENTITY = "2ba2c7dcb5c8e19350a3acf37ed9d9c9daf6d058fc38811d06d3460825e9b610"
EXPECTED_TOPOLOGY = {"construction_ids": ["C1"], "entry_ids": ["P1", "P2"], "creative_audit_ids": ["T1"]}


@dataclass(frozen=True, slots=True)
class FrozenStageCCase01InputV1_2_1:
    binding_identity: str
    raw_ledger: bytes
    candidate: bytes
    factual_authority: bytes
    raw_output_sha256: str
    candidate_sha256: str
    factual_authority_sha256: str
    source_context_identity: str
    semantic_policy_identity: str
    evaluation_receipt_identity: str
    closure_receipt_identity: str
    evidence_commit: str
    evaluation_commit: str
    closure_commit: str


def admit_frozen_stage_c_case01_input_v1_2_1(
    *, raw_ledger: bytes, candidate: bytes, factual_authority: bytes,
    raw_evaluation_receipt: bytes, raw_closure_receipt: bytes,
) -> FrozenStageCCase01InputV1_2_1:
    for value, label in ((raw_ledger, "LEDGER"), (candidate, "CANDIDATE"),
                         (factual_authority, "AUTHORITY"),
                         (raw_evaluation_receipt, "EVALUATION"),
                         (raw_closure_receipt, "CLOSURE")):
        if type(value) is not bytes:
            raise TypeError(f"STAGE_C_CASE01_{label}_EXACT_BYTES_REQUIRED")
    if hashlib.sha256(raw_ledger).hexdigest() != RAW_OUTPUT_SHA256:
        raise ValueError("STAGE_C_CASE01_FROZEN_LEDGER_IDENTITY_MISMATCH")
    candidate_source = ImmutableUtf8SourceV1.bind(role=SourceRoleV1.CANDIDATE, data=candidate)
    authority_source = ImmutableUtf8SourceV1.bind(role=SourceRoleV1.FACTUAL_AUTHORITY, data=factual_authority)
    policy = SemanticCompletenessPolicyV1.bind(
        candidate=candidate_source, factual_authority=authority_source)
    if policy.identity != CASE01_CANONICAL_POLICY_IDENTITY:
        raise ValueError("STAGE_C_CASE01_CANONICAL_SEMANTIC_POLICY_REQUIRED")
    ledger = SemanticCompletenessAdmissionV1(policy).validate_terminal(
        raw_ledger.decode("utf-8", errors="strict"))
    topology = {
        "construction_ids": [item.construction_id for item in ledger.construction_role_audit.construction_records],
        "entry_ids": [item.entry_id for item in ledger.entries],
        "creative_audit_ids": [item.audit_id for item in ledger.creative_target_audits],
    }
    if topology != EXPECTED_TOPOLOGY:
        raise ValueError("STAGE_C_CASE01_FROZEN_TOPOLOGY_MISMATCH")
    evaluation = _canonical_object(raw_evaluation_receipt, "EVALUATION")
    closure = _canonical_object(raw_closure_receipt, "CLOSURE")
    if (evaluation.get("evaluation_receipt_identity") != EVALUATION_RECEIPT_IDENTITY
            or hashlib.sha256(raw_evaluation_receipt).hexdigest() != EVALUATION_RECEIPT_SHA256):
        raise ValueError("STAGE_C_CASE01_EVALUATION_RECEIPT_BYTES_MISMATCH")
    _verify_seal(closure, "closure_receipt_identity", CLOSURE_RECEIPT_IDENTITY)
    if not (
        evaluation.get("case_id") == CASE_ID
        and evaluation.get("evidence_commit") == EVIDENCE_COMMIT
        and evaluation.get("raw_output_sha256") == RAW_OUTPUT_SHA256
        and evaluation.get("semantic_policy_identity") == CASE01_CANONICAL_POLICY_IDENTITY
        and evaluation.get("source_context_identity", SOURCE_CONTEXT_IDENTITY) == SOURCE_CONTEXT_IDENTITY
        and evaluation.get("topology") == EXPECTED_TOPOLOGY
        and evaluation.get("verdict") == "PASS"
        and evaluation.get("execution_attempts_consumed") == 1
        and evaluation.get("execution_attempts_remaining") == 0
        and evaluation.get("stage_c_performed") is False
    ):
        raise ValueError("STAGE_C_CASE01_EVALUATION_BINDING_INVALID")
    stage_c = closure.get("stage_c")
    if not (
        closure.get("case_id") == CASE_ID
        and closure.get("evaluation", {}).get("commit") == EVALUATION_COMMIT
        and closure.get("evaluation", {}).get("receipt_identity") == EVALUATION_RECEIPT_IDENTITY
        and closure.get("evaluation", {}).get("verdict") == "PASS"
        and closure.get("execution", {}).get("evidence_commit") == EVIDENCE_COMMIT
        and closure.get("execution", {}).get("raw_output_sha256") == RAW_OUTPUT_SHA256
        and closure.get("execution", {}).get("attempts_consumed") == 1
        and closure.get("execution", {}).get("attempts_remaining") == 0
        and stage_c == {"authorized": False, "constructed": False, "executed": False,
                        "status": "ELIGIBLE_REQUIRES_SEPARATE_OWNER_AUTHORITY"}
    ):
        raise ValueError("STAGE_C_CASE01_CLOSURE_BINDING_INVALID")
    material = {
        "schema": "STAGE_C_CASE01_FROZEN_INPUT_V1_2_1",
        "case_id": CASE_ID, "evidence_commit": EVIDENCE_COMMIT,
        "evaluation_commit": EVALUATION_COMMIT, "closure_commit": CLOSURE_COMMIT,
        "raw_output_sha256": RAW_OUTPUT_SHA256,
        "candidate_sha256": candidate_source.sha256,
        "factual_authority_sha256": authority_source.sha256,
        "source_context_identity": SOURCE_CONTEXT_IDENTITY,
        "semantic_policy_identity": policy.identity,
        "evaluation_receipt_identity": EVALUATION_RECEIPT_IDENTITY,
        "closure_receipt_identity": CLOSURE_RECEIPT_IDENTITY,
        "topology": EXPECTED_TOPOLOGY,
    }
    return FrozenStageCCase01InputV1_2_1(
        hashlib.sha256(_canonical(material)).hexdigest(), raw_ledger, candidate,
        factual_authority, RAW_OUTPUT_SHA256, candidate_source.sha256,
        authority_source.sha256, SOURCE_CONTEXT_IDENTITY, policy.identity,
        EVALUATION_RECEIPT_IDENTITY, CLOSURE_RECEIPT_IDENTITY, EVIDENCE_COMMIT,
        EVALUATION_COMMIT, CLOSURE_COMMIT)


def _canonical_object(raw: bytes, label: str) -> dict[str, object]:
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise ValueError(f"STAGE_C_CASE01_{label}_JSON_INVALID") from exc
    if type(value) is not dict or raw != _canonical(value) + b"\n":
        raise ValueError(f"STAGE_C_CASE01_{label}_CANONICAL_BYTES_REQUIRED")
    return value


def _verify_seal(value: dict[str, object], field: str, expected: str) -> None:
    if value.get(field) != expected:
        raise ValueError("STAGE_C_CASE01_RECEIPT_IDENTITY_MISMATCH")
    body = {key: item for key, item in value.items() if key != field}
    if hashlib.sha256(_canonical(body)).hexdigest() != expected:
        raise ValueError("STAGE_C_CASE01_RECEIPT_SEAL_INVALID")


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


__all__ = ("FrozenStageCCase01InputV1_2_1", "admit_frozen_stage_c_case01_input_v1_2_1")
