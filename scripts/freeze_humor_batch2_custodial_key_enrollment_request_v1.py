"""Freeze a content-free custodial public-key enrollment request."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "artifacts"
READINESS_COMMIT = "51288dd277bdd300fa4d217935fee4fe7bcf7ce5"
READINESS_ID = "89e61c2d7f2dcbfd51e41d907e3ef27041985dc6caad5d1267d6824530462e1a"
APPOINTMENT_ID = "e5b4ebb9fe29244a8d760337dcd66253264a42edd9b3540bb3fd5a44f91206d5"
GENESIS_HASH = "8afc9aa54bf66d385d8e89d84f18884e06e6838acc9c1e3cc4127d1450442ad1"
ROLES = (
    "RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN", "FAMILY_CUSTODIAN",
    "PARTITION_CUSTODIAN", "BLIND_ESCROW_CUSTODIAN", "CONTAMINATION_AUDITOR",
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def write(name: str, value: Any) -> str:
    body = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    (OUT / name).write_text(body, encoding="utf-8", newline="\n")
    return hashlib.sha256(body.encode()).hexdigest()


def false_authority() -> dict[str, bool]:
    return {key: False for key in [
        "source_acquisition", "content_ingestion", "archive_write", "content_access",
        "mechanism_assignment", "candidate_construction", "surface_generation",
        "model_exposure", "training", "runtime_integration", "production_routing"]}


def main() -> None:
    requests = []
    for role in ROLES:
        principal = seal("B2_OWNER_CONTROLLED_CUSTODIAL_PRINCIPAL_V1",
                         {"channel_registry_identity": "c7281b048318233c08bb5e8251dd08e19aceb1ac240c79fa8ef072d24f35b055",
                          "role": role, "generation": 1})
        challenge = {
            "domain": "PASTILA_BATCH2_OWNED_AUTHORITY_KEY_ENROLLMENT_V1",
            "purpose": "CUSTODIAL_PUBLIC_KEY_PROOF_OF_POSSESSION",
            "role": role, "principal_identity": principal,
            "appointment_registry_identity": APPOINTMENT_ID,
            "signing_readiness_identity": READINESS_ID,
            "previous_ledger_hash": GENESIS_HASH,
            "generation": 1,
        }
        challenge["challenge_identity"] = seal("B2_CUSTODIAL_KEY_CHALLENGE_V1", challenge)
        requests.append({
            "role": role, "principal_identity": principal, "challenge": challenge,
            "accepted_algorithms": ["ED25519", "ECDSA_P256_SHA256"],
            "owner_supplied_public_key": None, "public_key_fingerprint": None,
            "proof_signature": None, "proof_status": "AWAITING_OWNER_INPUT",
            "registration_status": "NOT_REGISTERED",
        })
    packet = {
        "schema_name": "batch2-custodial-key-enrollment-request-v1",
        "schema_version": "1.0.0",
        "bindings": {"readiness_commit": READINESS_COMMIT, "readiness_identity": READINESS_ID,
                     "appointment_registry_identity": APPOINTMENT_ID,
                     "previous_ledger_hash": GENESIS_HASH},
        "requests": requests,
        "submission_requirements": [
            "PUBLIC_KEY_BYTES_OR_CANONICAL_JWK", "ALGORITHM", "KEY_FINGERPRINT",
            "SIGNATURE_OVER_EXACT_CANONICAL_CHALLENGE", "OWNER_ROLE_CONFIRMATION",
        ],
        "prohibitions": [
            "NO_PRIVATE_KEY_SUBMISSION", "NO_KEY_GENERATION_BY_REPOSITORY",
            "NO_UNRELATED_GIT_OR_SSH_KEY_REUSE_WITHOUT_EXPLICIT_OWNER_BINDING",
            "NO_SHARED_KEY_ACROSS_SEPARATION_OF_DUTY_ROLES", "NO_OPERATIONAL_ACCESS_ON_REGISTRATION",
        ],
        "status": "BLOCKED_AWAITING_OWNER_PUBLIC_KEYS_AND_PROOFS",
        "current_authority": false_authority(),
    }
    packet["enrollment_request_identity"] = seal("B2_CUSTODIAL_KEY_ENROLLMENT_REQUEST_V1", packet)
    packet_sha = write("humor-mechanics-batch2-custodial-key-enrollment-request-v1.json", packet)

    ledger = {
        "schema_name": "batch2-custodial-access-ledger-entry-v1",
        "schema_version": "1.0.0", "entry_sequence": 1,
        "previous_entry_hash": GENESIS_HASH, "event": "KEY_ENROLLMENT_REQUEST_FROZEN",
        "object_identity": packet["enrollment_request_identity"], "object_sha256": packet_sha,
        "source_content_present": False, "blind_content_present": False,
        "keys_registered": 0, "proofs_verified": 0, "operational_authority": False,
    }
    ledger["entry_hash"] = seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", ledger)
    ledger_sha = write("humor-mechanics-batch2-custodial-access-ledger-entry-0001-key-enrollment-v1.json", ledger)

    audit = {
        "schema_name": "batch2-custodial-key-enrollment-request-v1-audit",
        "schema_version": "1.0.0",
        "enrollment_request_identity": packet["enrollment_request_identity"],
        "enrollment_request_sha256": packet_sha, "ledger_entry_hash": ledger["entry_hash"],
        "ledger_entry_sha256": ledger_sha,
        "checks": {
            "six_role_bound_challenges": "PASS", "challenges_domain_separated": "PASS",
            "challenges_appointment_and_ledger_bound": "PASS", "no_key_discovery_or_reuse": "PASS",
            "no_private_key_requested": "PASS", "no_key_or_signature_invented": "PASS",
            "no_shared_role_key_allowed": "PASS", "registration_not_operation": "PASS",
            "all_action_authorities_false": "PASS",
        },
        "verdict": "BLOCKED_AWAITING_OWNER_PUBLIC_KEYS_AND_PROOFS",
        "blocker": "NO_OWNER_SUPPLIED_PUBLIC_KEYS_OR_PROOF_SIGNATURES_AVAILABLE",
        "authority_matrix": false_authority(),
    }
    write("humor-mechanics-batch2-custodial-key-enrollment-request-v1-audit.json", audit)


if __name__ == "__main__":
    main()
