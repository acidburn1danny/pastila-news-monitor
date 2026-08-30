"""Freeze the content-free qualification of Batch 2's internally owned lane."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "artifacts"
PROTOCOL_COMMIT = "eb0c094e512ee934a8c54fc2a0087e1346bd7d29"
PROTOCOL_ID = "c5ee6343adad61110f3c08b36b4e9d66e271889e9fe542044cba44ad6e926a09"
PROTOCOL_SHA = "ee4ea50ba411b2ca607a798f452bb2f17176f22b707be286b3c346649b2574fd"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def write(name: str, value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    (OUT / name).write_text(data, encoding="utf-8", newline="\n")
    return hashlib.sha256(data.encode()).hexdigest()


def no_actions() -> dict[str, bool]:
    return {
        "source_acquisition": False, "content_ingestion": False, "mechanism_assignment": False,
        "candidate_construction": False, "surface_generation": False, "model_exposure": False,
        "training": False, "runtime_integration": False, "production_routing": False,
    }


def main() -> None:
    declaration = {
        "schema_name": "batch2-internally-owned-rights-declaration-template-v1",
        "schema_version": "1.0.0",
        "template_only": True,
        "not_a_grant_until_completed_and_sealed": True,
        "required_identity_fields": [
            "declaration_id", "contributor_legal_identity", "rights_holder_identity",
            "contributor_role", "source_family_commitment", "effective_at",
        ],
        "required_declarations": [
            "ORIGINAL_AUTHORSHIP_OR_DOCUMENTED_RIGHTS_OWNERSHIP",
            "NO_UNDISCLOSED_THIRD_PARTY_MATERIAL",
            "NO_CONFIDENTIAL_PRIVATE_OR_UNLAWFULLY_OBTAINED_INFORMATION",
            "FACTUAL_PROPOSITIONS_AND_QUALIFICATIONS_IDENTIFIED_BY_CONTRIBUTOR",
            "RIGHT_TO_MAKE_THE_SELECTED_ACTION_SPECIFIC_GRANTS",
        ],
        "independent_grants": {
            "DISCOVERY": {"value": "UNSELECTED", "required_explicit_boolean": True},
            "CONSTRUCTION_EVALUATION": {"value": "UNSELECTED", "required_explicit_boolean": True},
            "TRAINING": {"value": "UNSELECTED", "required_explicit_boolean": True},
            "PRODUCTION": {"value": "UNSELECTED", "required_explicit_boolean": True},
        },
        "grant_noninheritance": True,
        "required_terms": {
            "territory": "EXPLICIT_VALUE_REQUIRED", "expiry": "EXPLICIT_VALUE_OR_NO_EXPIRY_REQUIRED",
            "attribution": "EXPLICIT_VALUE_REQUIRED", "compensation": "EXPLICIT_VALUE_REQUIRED",
            "revocation": "PROSPECTIVE_FAIL_CLOSED_AND_CONSUMED_USE_ACCOUNTING_REQUIRED",
            "correction": "NEW_IMMUTABLE_REVISION_ONLY",
            "supersession": "EXPLICIT_PREDECESSOR_SUCCESSOR_CHAIN",
        },
        "execution_requirements": [
            "CONTRIBUTOR_SIGNATURE_OR_OWNER_SEAL", "RIGHTS_CUSTODIAN_COUNTERSEAL",
            "CANONICAL_BYTES_SHA256", "SIGNATURE_TIME", "NO_BLANK_REQUIRED_FIELD",
        ],
        "current_grant": no_actions(),
    }
    declaration["template_identity"] = seal("B2_INTERNALLY_OWNED_DECLARATION_TEMPLATE_V1", declaration)
    declaration_sha = write("humor-mechanics-batch2-internally-owned-rights-declaration-template-v1.json", declaration)

    archive = {
        "schema_name": "batch2-owned-authority-immutable-archive-qualification-v1",
        "schema_version": "1.0.0",
        "qualified_design": "GIT_OBJECT_OR_GIT_BOUND_CONTENT_ADDRESSED_ARCHIVE",
        "requirements": [
            "ORIGINAL_BYTES_RETRIEVABLE_BY_IDENTITY", "SHA256_AND_BYTE_LENGTH",
            "UTF8_ENCODING_DECLARATION", "CAPTURE_TIMESTAMP", "SOURCE_VERSION",
            "INDEPENDENT_CHARACTER_AND_UTF8_BYTE_COORDINATES", "ATOMIC_OBJECT_CREATION",
            "READ_AFTER_WRITE_BYTE_VERIFICATION", "NO_IN_PLACE_MUTATION",
            "CORRECTION_CREATES_SUCCESSOR", "REVOCATION_TOMBSTONE_DOES_NOT_DELETE_AUDIT_CHAIN",
        ],
        "archive_receipt_fields": [
            "archive_object_identity", "original_bytes_sha256", "byte_length", "git_blob_or_store_object",
            "capture_time", "writer_role", "rights_instrument_id", "readback_sha256",
            "previous_receipt_hash", "receipt_hash",
        ],
        "admission_order": [
            "COMPLETED_RIGHTS_INSTRUMENT", "METADATA_CAPTURE", "ARCHIVE_WRITE",
            "READBACK_VERIFICATION", "SOURCE_PACKAGE_SEAL", "FAMILY_CLOSURE",
            "PARTITION_SEAL", "PARTITION_SPECIFIC_ACCESS",
        ],
        "metadata_only_test_backend": "REPOSITORY_GIT_OBJECT_DATABASE_READ_ONLY_EXISTING_GOVERNANCE_OBJECT",
        "qualified_backend": "REPOSITORY_GIT_OBJECT_DATABASE",
        "qualification_readback": {
            "commit": PROTOCOL_COMMIT,
            "path": "docs/artifacts/humor-mechanics-batch2-owned-authority-acquisition-protocol-v1.json",
            "expected_sha256": PROTOCOL_SHA,
            "source_content": False,
        },
        "production_archive_selected": True,
        "archive_write_authorized": False,
        "content_ingestion_authorized": False,
    }
    archive["archive_spec_identity"] = seal("B2_IMMUTABLE_ARCHIVE_QUALIFICATION_V1", archive)
    archive_sha = write("humor-mechanics-batch2-immutable-archive-qualification-v1.json", archive)

    roles = {
        "schema_name": "batch2-owned-authority-custodial-role-matrix-v1",
        "schema_version": "1.0.0",
        "roles": {
            "RIGHTS_CUSTODIAN": {"may": ["VALIDATE_INSTRUMENT_METADATA", "COUNTERSEAL"],
                                 "must_not": ["ASSIGN_MECHANISM", "CONSTRUCT", "SELECT_OUTPUT"]},
            "ACQUISITION_CUSTODIAN": {"may": ["RECEIVE_AUTHORIZED_SOURCE", "WRITE_ARCHIVE"],
                                     "must_not": ["ASSIGN_MECHANISM", "SELECT_PARTITION_BY_CONTENT"]},
            "FAMILY_CUSTODIAN": {"may": ["DEDUPE_METADATA", "SEAL_FAMILY_CLOSURE"],
                                "must_not": ["CONSTRUCT", "MOVE_RELATIVE_ACROSS_PARTITIONS"]},
            "PARTITION_CUSTODIAN": {"may": ["APPLY_FROZEN_METADATA_RULE", "SEAL_PARTITION"],
                                   "must_not": ["READ_BLIND_SURFACE", "OVERRIDE_ASSIGNMENT"]},
            "BLIND_ESCROW_CUSTODIAN": {"may": ["HOLD_BLIND_BYTES", "AUDIT_RIGHTS"],
                                      "must_not": ["DISCLOSE_TO_CONSTRUCTOR", "TUNE_SYSTEM", "TRAIN"]},
            "CONTAMINATION_AUDITOR": {"may": ["READ_ACCESS_LOG_METADATA", "FAIL_CLOSED"],
                                     "must_not": ["DISCLOSE_CONTENT", "RECLASSIFY_CONTAMINATED"]},
        },
        "separation_of_duties": [
            ["RIGHTS_CUSTODIAN", "CONSTRUCTOR"], ["ACQUISITION_CUSTODIAN", "ASSIGNMENT_CUSTODIAN"],
            ["BLIND_ESCROW_CUSTODIAN", "CONSTRUCTOR"], ["CONTAMINATION_AUDITOR", "OWNER_SELECTOR"],
        ],
        "appointments": "UNASSIGNED_REQUIRES_SEPARATE_OWNER_APPOINTMENT",
        "credentials_provisioned": False,
        "operational_access_enabled": False,
    }
    roles["role_matrix_identity"] = seal("B2_CUSTODIAL_ROLE_MATRIX_V1", roles)
    roles_sha = write("humor-mechanics-batch2-custodial-role-matrix-v1.json", roles)

    fixtures = {
        "schema_name": "batch2-internally-owned-channel-metadata-only-conformance-v1",
        "schema_version": "1.0.0",
        "contains_source_content": False,
        "placeholder_policy": "FIXED_NONCONTENT_HASHES_AND_IDENTIFIERS_ONLY",
        "cases": {
            "VALID_COMPLETE_TEMPLATE_SHAPE": "PASS_PROTOCOL_SHAPE_ONLY_NOT_A_REAL_GRANT",
            "MISSING_CONTRIBUTOR_SIGNATURE": "REJECTED",
            "MISSING_RIGHTS_CUSTODIAN_COUNTERSEAL": "REJECTED",
            "AMBIGUOUS_AUTHORSHIP": "REJECTED",
            "UNDISCLOSED_THIRD_PARTY_RIGHTS": "REJECTED",
            "DISCOVERY_GRANT_USED_FOR_CONSTRUCTION": "REJECTED",
            "CONSTRUCTION_GRANT_USED_FOR_TRAINING": "REJECTED",
            "TRAINING_GRANT_USED_FOR_PRODUCTION": "REJECTED",
            "REVOKED_INSTRUMENT": "REJECTED",
            "INSTRUMENT_BYTES_MUTATED_AFTER_SEAL": "REJECTED",
            "ARCHIVE_WRITE_WITHOUT_RIGHTS": "REJECTED",
            "ARCHIVE_READBACK_HASH_MISMATCH": "REJECTED",
            "IN_PLACE_SOURCE_CORRECTION": "REJECTED",
            "CHARACTER_BYTE_COORDINATES_COLLAPSED": "REJECTED",
            "CONTENT_ACCESS_BEFORE_PARTITION_SEAL": "REJECTED",
            "BLIND_ACCESS_BY_CONSTRUCTOR": "REJECTED",
            "UNAUTHORIZED_ROLE_COMBINATION": "REJECTED",
            "HIDDEN_MECHANISM_ASSIGNMENT_FIELD": "REJECTED",
        },
        "actions_performed": {"sources_acquired": 0, "content_ingested": 0, "content_bytes_created": 0,
                              "blind_surfaces_read": 0, "model_calls": 0},
    }
    fixtures["fixture_suite_identity"] = seal("B2_INTERNALLY_OWNED_METADATA_FIXTURES_V1", fixtures)
    fixtures_sha = write("humor-mechanics-batch2-internally-owned-metadata-conformance-v1.json", fixtures)

    registry = {
        "schema_name": "batch2-owned-authority-approved-channel-registry-v1",
        "schema_version": "1.0.0",
        "protocol_commit": PROTOCOL_COMMIT, "protocol_identity": PROTOCOL_ID, "protocol_sha256": PROTOCOL_SHA,
        "channels": {
            "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE": {
                "qualification": "QUALIFIED_PROTOCOL_DESIGN_ONLY",
                "qualification_artifacts": {
                    "declaration_template_sha256": declaration_sha, "archive_spec_sha256": archive_sha,
                    "role_matrix_sha256": roles_sha, "metadata_fixture_sha256": fixtures_sha,
                },
                "source_acquisition_enabled": False, "content_ingestion_enabled": False,
                "reason_disabled": "REQUIRES_SEPARATE_SOURCE_ACQUISITION_AUTHORITY_AND_CUSTODIAN_APPOINTMENTS",
            },
            "AFFIRMATIVELY_LICENSED_EXTERNAL_MATERIAL": {
                "qualification": "NOT_YET_QUALIFIED", "source_acquisition_enabled": False,
                "content_ingestion_enabled": False,
            },
            "COMPATIBLE_PUBLIC_DOMAIN_OR_OPEN_LICENSE_MATERIAL": {
                "qualification": "NOT_YET_QUALIFIED", "source_acquisition_enabled": False,
                "content_ingestion_enabled": False,
            },
        },
        "current_authority": no_actions(),
    }
    registry["registry_identity"] = seal("B2_APPROVED_CHANNEL_REGISTRY_V1", registry)
    registry_sha = write("humor-mechanics-batch2-approved-channel-registry-v1.json", registry)

    audit = {
        "schema_name": "batch2-internally-owned-channel-qualification-v1-audit",
        "schema_version": "1.0.0",
        "bindings": {
            "protocol_identity": PROTOCOL_ID, "registry_identity": registry["registry_identity"],
            "registry_sha256": registry_sha, "declaration_template_identity": declaration["template_identity"],
            "archive_spec_identity": archive["archive_spec_identity"], "role_matrix_identity": roles["role_matrix_identity"],
            "fixture_suite_identity": fixtures["fixture_suite_identity"],
        },
        "checks": {
            "rights_action_specific_and_noninheriting": "PASS",
            "template_cannot_act_as_unsigned_grant": "PASS",
            "archive_design_content_addressed_and_immutable": "PASS",
            "character_and_utf8_coordinates_independent": "PASS",
            "roles_separated_and_unappointed": "PASS",
            "blind_access_fail_closed": "PASS",
            "metadata_fixtures_contain_no_source_content": "PASS",
            "qualified_does_not_mean_operationally_enabled": "PASS",
            "external_and_open_lanes_remain_disabled": "PASS",
            "all_action_authorities_false": "PASS",
        },
        "deterministic_defects_remaining": [],
        "verdict": "PASS_CONTENT_FREE_CHANNEL_QUALIFICATION",
        "authority_matrix": no_actions(),
        "next_phase": "SEPARATE_CONTENT_FREE_CUSTODIAL_APPOINTMENT_AND_SIGNING_READINESS",
    }
    write("humor-mechanics-batch2-internally-owned-channel-qualification-v1-audit.json", audit)


if __name__ == "__main__":
    main()
