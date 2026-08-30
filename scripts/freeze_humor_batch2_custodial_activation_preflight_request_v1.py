"""Freeze the atomic content-free custodial activation-preflight request."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "artifacts"
REGISTRATION_COMMIT = "cab04b6e43b13fefe6ab048b6ac8c7dbabe630b7"
REGISTRATION_ID = "01912e139471ec23cba5861c8f575f098a6248d39ebbe5ec2ee043493d392ebe"
PRIOR_LEDGER = "b37cc702be9990638d4f196c1399f42dc3695ad1f271022759e114a3c559a00b"
REGISTRATION_PATH = OUT / "humor-mechanics-batch2-custodial-public-key-registration-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def main() -> None:
    registration = json.loads(REGISTRATION_PATH.read_text(encoding="utf-8"))
    principals = {item["role"]: item["principal_identity"] for item in registration["registrations"]}
    operations = [
        ("RIGHTS_METADATA_ADMISSION_PREFLIGHT", ["RIGHTS_CUSTODIAN"]),
        ("ARCHIVE_ADMISSION_PREFLIGHT", ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"]),
        ("FAMILY_CLOSURE_PREFLIGHT", ["FAMILY_CUSTODIAN"]),
        ("PARTITION_SEAL_PREFLIGHT", ["PARTITION_CUSTODIAN"]),
        ("BLIND_ESCROW_ADMISSION_PREFLIGHT", ["PARTITION_CUSTODIAN", "BLIND_ESCROW_CUSTODIAN"]),
        ("CONTAMINATION_AUDIT_PREFLIGHT", ["CONTAMINATION_AUDITOR"]),
    ]
    operation_records = []
    for index, (purpose, signer_roles) in enumerate(operations):
        structural_object = {
            "object_kind": "NONCONTENT_METADATA_ONLY_PLACEHOLDER",
            "ordinal": index, "purpose": purpose,
            "placeholder_commitment": seal("B2_NONCONTENT_PREFLIGHT_PLACEHOLDER_V1",
                                           {"ordinal": index, "purpose": purpose}),
            "contains_source_content": False, "grants_operational_authority": False,
        }
        operation_records.append({
            "ordinal": index, "purpose": purpose,
            "object_identity": seal("B2_ACTIVATION_PREFLIGHT_OBJECT_V1", structural_object),
            "structural_object": structural_object,
            "required_signer_roles": signer_roles,
            "distinct_signers_required": len(signer_roles) > 1,
        })
    batch_core = {
        "registration_commit": REGISTRATION_COMMIT, "registration_identity": REGISTRATION_ID,
        "prior_ledger_head": PRIOR_LEDGER, "atomic": True,
        "operations": operation_records,
    }
    batch_identity = seal("B2_CUSTODIAL_ACTIVATION_PREFLIGHT_BATCH_V1", batch_core)
    signature_requests = []
    for operation in operation_records:
        for role in operation["required_signer_roles"]:
            challenge = {
                "domain": "PASTILA_BATCH2_CUSTODIAL_ACTIVATION_PREFLIGHT_V1",
                "purpose": operation["purpose"], "signer_role": role,
                "principal_identity": principals[role],
                "object_identity": operation["object_identity"],
                "batch_identity": batch_identity, "operation_ordinal": operation["ordinal"],
                "nonce": seal("B2_ACTIVATION_PREFLIGHT_NONCE_V1",
                              {"batch": batch_identity, "ordinal": operation["ordinal"], "role": role}),
                "prior_ledger_head": PRIOR_LEDGER,
                "grants_operational_authority": False,
            }
            challenge["challenge_identity"] = seal("B2_ACTIVATION_PREFLIGHT_SIGNATURE_CHALLENGE_V1", challenge)
            signature_requests.append({
                "operation_ordinal": operation["ordinal"], "purpose": operation["purpose"],
                "signer_role": role, "principal_identity": principals[role],
                "challenge": challenge, "signature_status": "AWAITING_OWNER_SIGNATURE",
            })
    request = {
        "schema_name": "batch2-custodial-activation-preflight-request-v1",
        "schema_version": "1.0.0", "batch_core": batch_core,
        "batch_identity": batch_identity, "signature_requests": signature_requests,
        "required_signature_count": len(signature_requests),
        "fail_closed_mutations": [
            "WRONG_ROLE_SIGNER", "REUSED_SIGNATURE", "REUSED_NONCE", "STALE_LEDGER_HEAD",
            "ALTERED_OBJECT_IDENTITY", "ALTERED_PURPOSE", "ALTERED_DOMAIN",
            "MISSING_COUNTERSIGNATURE", "SAME_ROLE_COUNTERSIGNATURE",
            "DUPLICATE_KEY_SUBSTITUTION", "REVOKED_OR_UNREGISTERED_KEY",
            "UNAUTHORIZED_LEDGER_APPEND", "REPLAY_PREVIOUS_VALID_PREFLIGHT_EVENT",
            "CROSS_PURPOSE_SIGNATURE_REUSE",
        ],
        "status": "AWAITING_OWNER_CONTROLLED_PREFLIGHT_SIGNATURES",
        "ledger_events_appended": 0,
        "activation_readiness": "NOT_YET_ESTABLISHED",
        "operational_content_access": False,
        "authority_matrix": {key: False for key in [
            "source_acquisition", "content_ingestion", "archive_write", "content_access",
            "mechanism_assignment", "candidate_construction", "surface_generation",
            "model_exposure", "training", "runtime_integration", "production_routing"]},
    }
    request["request_identity"] = seal("B2_CUSTODIAL_ACTIVATION_PREFLIGHT_REQUEST_V1", request)
    body = json.dumps(request, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    (OUT / "humor-mechanics-batch2-custodial-activation-preflight-request-v1.json").write_text(
        body, encoding="utf-8", newline="\n")
    print(json.dumps({"request_identity": request["request_identity"],
                      "batch_identity": batch_identity,
                      "signature_requests": len(signature_requests),
                      "ledger_events_appended": 0,
                      "status": request["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
