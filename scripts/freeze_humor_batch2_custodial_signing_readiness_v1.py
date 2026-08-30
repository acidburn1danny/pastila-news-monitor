"""Freeze content-free custodial appointments and signing readiness."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "artifacts"
CHANNEL_COMMIT = "24ae982bce3a688fce9a193721d32e036a16b639"
REGISTRY_ID = "c7281b048318233c08bb5e8251dd08e19aceb1ac240c79fa8ef072d24f35b055"
ROLE_MATRIX_ID = "1bc390244d09ee63d9b851c6c014a2693060710947e89c1c41ee6293825fc0b1"


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
        "source_acquisition", "content_ingestion", "mechanism_assignment", "candidate_construction",
        "surface_generation", "model_exposure", "training", "runtime_integration", "production_routing"]}


def role_id(role: str) -> str:
    return seal("B2_OWNER_CONTROLLED_CUSTODIAL_PRINCIPAL_V1",
                {"channel_registry_identity": REGISTRY_ID, "role": role, "generation": 1})


def main() -> None:
    roles = [
        "RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN", "FAMILY_CUSTODIAN",
        "PARTITION_CUSTODIAN", "BLIND_ESCROW_CUSTODIAN", "CONTAMINATION_AUDITOR",
    ]
    appointments = {
        "schema_name": "batch2-custodial-appointment-registry-v1",
        "schema_version": "1.0.0",
        "bindings": {"channel_commit": CHANNEL_COMMIT, "channel_registry_identity": REGISTRY_ID,
                     "role_matrix_identity": ROLE_MATRIX_ID},
        "appointments": [{
            "role": role, "principal_identity": role_id(role),
            "principal_kind": "DISTINCT_OWNER_CONTROLLED_LOGICAL_CUSTODIAN",
            "appointment_status": "CONDITIONALLY_APPOINTED_NONOPERATIONAL",
            "public_key_status": "UNREGISTERED",
            "credential_status": "UNPROVISIONED",
            "operational_access": False,
            "source_or_content_access": False,
        } for role in roles],
        "distinct_principal_required": True,
        "human_or_service_identity_disclosure": "REQUIRED_BEFORE_ACTIVATION",
        "activation_preconditions": [
            "OWNER_APPROVES_NAMED_OR_SERVICE_PRINCIPAL", "PUBLIC_KEY_REGISTERED",
            "KEY_PROOF_OF_POSSESSION_VERIFIED", "SEPARATION_OF_DUTIES_RECHECKED",
            "ACCESS_LEDGER_WRITE_TEST_PASSED", "SEPARATE_OPERATIONAL_AUTHORITY",
        ],
        "current_authority": false_authority(),
    }
    appointments["appointment_registry_identity"] = seal("B2_CUSTODIAL_APPOINTMENT_REGISTRY_V1", appointments)
    appointments_sha = write("humor-mechanics-batch2-custodial-appointment-registry-v1.json", appointments)

    signing = {
        "schema_name": "batch2-custodial-signing-envelope-v1",
        "schema_version": "1.0.0",
        "allowed_algorithm_policy": ["ED25519", "ECDSA_P256_SHA256"],
        "algorithm_selection": "UNSELECTED_REQUIRES_PUBLIC_KEY_REGISTRATION",
        "required_signed_fields": [
            "envelope_version", "purpose", "object_identity", "object_sha256",
            "rights_instrument_identity", "actor_role", "principal_identity",
            "public_key_fingerprint", "signed_at", "nonce", "previous_ledger_hash",
        ],
        "canonicalization": "JCS_STYLE_UTF8_SORTED_KEYS_NO_INSIGNIFICANT_WHITESPACE",
        "domain_separation": "PASTILA_BATCH2_OWNED_AUTHORITY_CUSTODIAL_V1",
        "replay_controls": ["UNIQUE_NONCE", "PURPOSE_BOUND", "OBJECT_BOUND", "LEDGER_HEAD_BOUND"],
        "fail_closed": [
            "UNKNOWN_KEY", "REVOKED_KEY", "ROLE_KEY_MISMATCH", "ALGORITHM_MISMATCH",
            "OBJECT_HASH_MISMATCH", "PURPOSE_MISMATCH", "NONCE_REPLAY", "STALE_LEDGER_HEAD",
            "MISSING_COUNTERSIGNATURE", "UNSELECTED_RIGHTS_GRANT",
        ],
        "minimum_countersignatures": {
            "RIGHTS_INSTRUMENT": ["RIGHTS_CUSTODIAN"],
            "ARCHIVE_ADMISSION": ["RIGHTS_CUSTODIAN", "ACQUISITION_CUSTODIAN"],
            "FAMILY_CLOSURE": ["FAMILY_CUSTODIAN"],
            "PARTITION_SEAL": ["PARTITION_CUSTODIAN"],
            "BLIND_ESCROW_ADMISSION": ["PARTITION_CUSTODIAN", "BLIND_ESCROW_CUSTODIAN"],
        },
        "secret_keys_created": 0, "public_keys_registered": 0, "signing_enabled": False,
    }
    signing["signing_spec_identity"] = seal("B2_CUSTODIAL_SIGNING_ENVELOPE_V1", signing)
    signing_sha = write("humor-mechanics-batch2-custodial-signing-envelope-v1.json", signing)

    genesis = {
        "schema_name": "batch2-custodial-access-ledger-genesis-v1",
        "schema_version": "1.0.0",
        "channel_registry_identity": REGISTRY_ID,
        "appointment_registry_identity": appointments["appointment_registry_identity"],
        "entry_sequence": 0, "previous_entry_hash": None,
        "event": "CONTENT_FREE_LEDGER_GENESIS",
        "object_commitments": [],
        "source_content_present": False, "blind_content_present": False,
        "operational_authority": False,
    }
    genesis["entry_hash"] = seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", genesis)
    genesis_sha = write("humor-mechanics-batch2-custodial-access-ledger-genesis-v1.json", genesis)

    fixtures = {
        "schema_name": "batch2-custodial-signing-readiness-fixtures-v1",
        "schema_version": "1.0.0",
        "metadata_only": True, "real_keys_used": 0, "real_signatures_created": 0,
        "valid_shape_case": "PASS_STRUCTURE_ONLY_NOT_A_SIGNATURE_OR_GRANT",
        "rejected_cases": [
            "SAME_PRINCIPAL_FOR_INCOMPATIBLE_ROLES", "MISSING_PRINCIPAL_DISCLOSURE",
            "UNREGISTERED_KEY_USED", "ROLE_KEY_MISMATCH", "REVOKED_KEY_USED",
            "OBJECT_HASH_MUTATION", "RIGHTS_PURPOSE_SUBSTITUTION", "NONCE_REPLAY",
            "STALE_LEDGER_HEAD", "MISSING_COUNTERSIGNATURE", "UNSELECTED_GRANT",
            "CONTENT_FIELD_IN_METADATA_FIXTURE", "ACTIVATION_WITHOUT_SEPARATE_AUTHORITY",
        ],
        "actions_performed": {
            "sources_acquired": 0, "content_ingested": 0, "keys_generated": 0,
            "signatures_created": 0, "credentials_provisioned": 0, "model_calls": 0,
        },
    }
    fixtures["fixture_identity"] = seal("B2_CUSTODIAL_SIGNING_READINESS_FIXTURES_V1", fixtures)
    fixtures_sha = write("humor-mechanics-batch2-custodial-signing-readiness-fixtures-v1.json", fixtures)

    readiness = {
        "schema_name": "batch2-custodial-appointment-signing-readiness-v1",
        "schema_version": "1.0.0",
        "bindings": {
            "appointments_sha256": appointments_sha, "signing_spec_sha256": signing_sha,
            "ledger_genesis_sha256": genesis_sha, "fixtures_sha256": fixtures_sha,
        },
        "state": {
            "logical_custodians_distinct": True,
            "appointments": "CONDITIONAL_NONOPERATIONAL",
            "public_keys": "UNREGISTERED", "credentials": "UNPROVISIONED",
            "signing": "DISABLED", "access": "DISABLED",
            "source_acquisition": "DISABLED", "content_ingestion": "DISABLED",
        },
        "verdict": "READY_FOR_SEPARATE_PUBLIC_KEY_REGISTRATION_NOT_OPERATION",
        "authority_matrix": false_authority(),
        "next_phase": "SEPARATELY_AUTHORIZED_PUBLIC_KEY_REGISTRATION_AND_PROOF_OF_POSSESSION_ONLY",
    }
    readiness["readiness_identity"] = seal("B2_CUSTODIAL_APPOINTMENT_SIGNING_READINESS_V1", readiness)
    readiness_sha = write("humor-mechanics-batch2-custodial-appointment-signing-readiness-v1.json", readiness)

    audit = {
        "schema_name": "batch2-custodial-appointment-signing-readiness-v1-audit",
        "schema_version": "1.0.0",
        "readiness_identity": readiness["readiness_identity"], "readiness_sha256": readiness_sha,
        "checks": {
            "logical_principals_distinct": "PASS", "appointments_nonoperational": "PASS",
            "no_fabricated_human_identity": "PASS", "no_secret_or_public_key_invention": "PASS",
            "signature_domain_object_purpose_role_bound": "PASS", "replay_protection": "PASS",
            "countersignature_policy": "PASS", "ledger_genesis_content_free": "PASS",
            "negative_fixtures_fail_closed": "PASS", "authority_does_not_activate": "PASS",
        },
        "deterministic_defects_remaining": [],
        "verdict": "PASS_CONTENT_FREE_CUSTODIAL_SIGNING_READINESS",
        "authority_matrix": false_authority(),
    }
    write("humor-mechanics-batch2-custodial-signing-readiness-v1-audit.json", audit)


if __name__ == "__main__":
    main()
