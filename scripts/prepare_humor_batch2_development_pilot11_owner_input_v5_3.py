"""Freeze content-free Pilot 11 owner-input preparation under Governance V5.3."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
FREEZE_COMMIT = "ee8685d1f6dbb2775d92cdcfa39b784705a4aadf"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{FREEZE_COMMIT}:{path}"], cwd=ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), f"artifact exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == FREEZE_COMMIT, "HEAD")
    contract = load("docs/artifacts/humor-mechanics-batch2-development-constructor-contract-v5-3.json")
    governance = load("docs/artifacts/humor-mechanics-batch2-semantic-edge-role-continuity-governance-v5-3.json")
    schema = load("docs/artifacts/humor-mechanics-batch2-semantic-edge-role-continuity-conformance-schema-v5-3.json")
    implementation = load("docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v5-3.json")
    provider = load("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-3-realization-provider-implementation.json")
    emitter = load("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-3-candidate-emitter-implementation.json")
    runtime_audit = load("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-3-runtime-static-audit-v1.json")
    expected = {
        "contract": (contract["constructor_contract_identity"], "9d811b18c16e8770549c19c9d8be63ef6f04e030fa67b5a47167b5e7ddc1bef6"),
        "governance": (governance["governance_identity"], "073d68d9d21c76974d12eb8e3f591f4172197377bfb36c2de2f85a5afe079dd6"),
        "schema": (schema["schema_identity"], "4b26df92539082f11b83c83f76b1d158c7c8f4c87304bdcdd8a6129644f532f3"),
        "implementation": (implementation["constructor_implementation_identity"], "18bd032218924cc8d2890301a1c92a376036918affddea335904a1491c807237"),
        "provider": (provider["realization_provider_implementation_identity"], "c458ecb1c9fe64285f0b70db1ccb9be6ed3e48a4f461f72d22abc0a1f0714a93"),
        "emitter": (emitter["candidate_emitter_implementation_identity"], "5a274ac6f140708066f587071e31f5376c0a985e5430d2537839c9627685ad5d"),
        "audit": (runtime_audit["static_audit_identity"], "46b24207afbfa388862598ea3c75a55342be13e108bef1fcd154f2612ec182b8"),
    }
    for name, (actual, wanted) in expected.items():
        require(actual == wanted, name)
    require(runtime_audit["verdict"] == "PASS_V5_3_PROVIDER_EMITTER_INTEGRATION_STATIC_AUDIT_ZERO_CONSTRUCTION_NO_RELEASE", "verdict")

    template_core = {
        "schema_name": "batch2-internally-owned-owner-input-pilot11-v1", "schema_version": "1.0.0",
        "pilot_id": "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-11",
        "source": {
            "filename": "owner-source-pilot11-v1.txt", "declared_encoding": "UTF-8", "bom": False,
            "line_endings": "LF", "terminal_lf_count": 1, "source_version": "OWNER_MUST_SUPPLY_SEMVER",
            "capture_timestamp": "OWNER_MUST_SUPPLY_ISO8601_WITH_OFFSET",
            "acquisition_timestamp": "OWNER_MUST_SUPPLY_ISO8601_WITH_OFFSET",
            "acquisition_channel": "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE",
            "intended_partition": "DEVELOPMENT", "subject_class": "OWNER_MUST_SUPPLY",
            "authority_scope": "OWNER_MUST_SUPPLY", "world_scope": "OWNER_MUST_SUPPLY",
        },
        "contributor": {key: "OWNER_MUST_SUPPLY_OR_CHOOSE" for key in (
            "public_identity", "legal_identity_commitment", "legal_identity_verification_reference", "role",
            "rights_holder_identity", "rights_holder_relationship", "identity_disclosure_approved_for_commit")},
        "ownership_declarations": {key: "OWNER_MUST_CHOOSE_BOOLEAN" for key in (
            "original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant",
            "contains_undisclosed_third_party_material", "contains_private_or_confidential_information", "contains_personal_data",
            "contains_unlawfully_obtained_information", "contains_unattributed_quotation", "contains_reputation_sensitive_allegation")},
        "independent_grants": {key: "OWNER_MUST_CHOOSE_BOOLEAN_INDEPENDENTLY" for key in (
            "immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation",
            "model_exposure", "training", "runtime_integration", "production_routing")},
        "rights_terms": {key: "OWNER_MUST_CHOOSE_OR_DECLARE" for key in (
            "territory", "effective_at", "expires_at", "attribution_requirement", "compensation_terms", "revocation_terms",
            "correction_policy", "supersession_policy", "survival_of_completed_uses")},
        "source_status_declarations": {
            "source_is_neutral_factual_authority": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_was_not_selected_or_shaped_for_any_mechanism_pool_target_proposition_result_assignment_obligation_constructor_compatibility_semantic_role_signature_affordance_topology_realization_plan_witness_topology_creative_marker_or_expected_positive_outcome": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_contains_no_mechanism_obligation_creative_premise_candidate_constructor_test_semantic_role_affordance_witness_or_template_marker": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_has_no_revision_sibling_same_event_or_syndication_relationship_with_pilots_01_02_03_04_05_06_07_08_09_10": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_does_not_reuse_pilots_01_02_03_04_05_06_07_08_09_10_wording_entities_events_or_source_structures": "OWNER_MUST_CHOOSE_BOOLEAN",
            "known_and_unknown_boundaries_are_explicit": "OWNER_MUST_CHOOSE_BOOLEAN",
        },
        "owner_instruction": {key: "OWNER_MUST_CHOOSE_BOOLEAN" for key in (
            "request_preingestion_validation_only", "permit_derived_hashes_and_coordinates", "permit_registered_custodial_signing_requests",
            "permit_git_object_archival", "permit_development_partition_seal", "operational_content_access_after_ingestion")},
        "owner_confirmation": {"owner_identity": "OWNER_MUST_SUPPLY", "confirmed": "OWNER_MUST_CHOOSE_BOOLEAN",
                               "confirmation_statement": "OWNER_MUST_SUPPLY_EXPLICIT_STATEMENT"},
    }
    template = {**template_core, "template_identity": seal("B2_DEVELOPMENT_PILOT11_OWNER_DECLARATION_TEMPLATE_V1", template_core)}
    authority_matrix = {key: False for key in (
        "source_acquisition", "content_access", "content_ingestion", "archive_write", "custodial_signing", "g01a_admission",
        "g01b_admission", "proposition_sufficiency_evaluation", "target_assignment", "obligation_assignment",
        "constructor_source_compatibility_check", "semantic_role_or_affordance_planning", "constructor_release", "construction",
        "realization", "candidate_emission", "semantic_edge_validation", "fragment_collision_evaluation", "g02", "g02c", "g03",
        "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")}
    request_core = {
        "schema_name": "batch2-development-pilot11-owner-input-request-v1", "schema_version": "1.0.0",
        "status": "BLOCKED_AWAITING_OWNER_INPUT",
        "preparation_verdict": "PASS_CONTENT_FREE_METADATA_FIRST_OWNER_PACKAGE_GOVERNANCE_V5_3",
        "bound_freeze_commit": FREEZE_COMMIT, "governance_identity": governance["governance_identity"],
        "conformance_schema_identity": schema["schema_identity"], "constructor_contract_identity": contract["constructor_contract_identity"],
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "realization_provider_implementation_identity": provider["realization_provider_implementation_identity"],
        "candidate_emitter_implementation_identity": emitter["candidate_emitter_implementation_identity"],
        "constructor_static_audit_identity": runtime_audit["static_audit_identity"],
        "pilot10_preservation": "IMMUTABLE_NONPOSITIVE_G02C_REJECTION_UNCHANGED",
        "constructor_v5_2_preservation": "PASS_BYTE_EXACT", "constructor_v5_3_release": "NOT_PERFORMED",
        "content_accessed": False, "source_family_created": False, "blind_material_accessed": False,
        "owner_files_required": [
            {"filename": "owner-source-pilot11-v1.txt", "encoding": "UTF-8_NO_BOM", "line_endings": "LF_ONLY", "terminal_lf_count": 1,
             "content": "OWNER_AUTHORED_BYTE_EXACT_NEUTRAL_FACTUAL_SOURCE"},
            {"filename": "owner-declaration-pilot11-v1.json", "canonical_requirement": "UTF8_JSON_NO_BOM_LF_ONE_TERMINAL_LF",
             "content": "OWNER_COMPLETED_DECLARATION_FROM_TEMPLATE"}],
        "source_content_requirements": {
            "minimum_independently_bindable_factual_propositions": 2, "must_be_owner_authored": True,
            "must_be_neutral_nonhumorous": True, "must_be_fresh_independent_of_pilots_01_through_10": True,
            "must_expose_scope_modality_time_and_known_unknown_boundaries_where_applicable": True,
            "must_not_be_optimized_for_any_downstream_gate_or_result": True,
            "prohibited_shaping": ["MECHANISM_OR_POOL_TARGET", "PROPOSITION_RESULT_ASSIGNMENT_OR_OBLIGATION",
                                   "CONSTRUCTOR_COMPATIBILITY", "SEMANTIC_ROLE_SIGNATURE_OR_AFFORDANCE_TOPOLOGY",
                                   "REALIZATION_PLAN_OR_WITNESS_TOPOLOGY", "CREATIVE_MARKER_OR_EXPECTED_POSITIVE_OUTCOME"]},
        "mandatory_phase_order": ["STRICT_PREINGESTION_VALIDATION", "PROSPECTIVE_IDENTITIES_AND_UNSIGNED_SIGNING_PACKET",
            "OWNER_OPERATED_CUSTODIAL_SIGNATURES", "ATOMIC_IMMUTABLE_INGESTION", "G01A", "G01B",
            "SEPARATELY_AUTHORIZED_PROPOSITION_SUFFICIENCY_GATE", "SEPARATELY_AUTHORIZED_ASSIGNMENT_DESIGN",
            "SEPARATELY_AUTHORIZED_CONSTRUCTOR_V5_3_SOURCE_COMPATIBILITY_AND_STATIC_SEMANTIC_PLAN_CHECK",
            "SEPARATELY_AUTHORIZED_G02B_RELEASE_DECISION", "SEPARATELY_AUTHORIZED_ONE_ATTEMPT_CONSTRUCTION",
            "MANDATORY_V5_3_POST_REALIZATION_PRE_EMISSION_SEMANTIC_CONFORMANCE",
            "MANDATORY_POSTCONSTRUCTION_FRAGMENT_COLLISION_GATE_BEFORE_G02"],
        "unassigned": {key: "UNASSIGNED" for key in ("source_family_id", "event_family_id", "authority_family_id",
            "topic_entity_family_id", "selected_proposition", "target_mechanism", "operational_obligation",
            "creative_premise_family_id", "creative_marker_family_id", "semantic_role_signature", "affordance_topology",
            "realization_plan", "witness_topology")},
        "declaration_template_identity": template["template_identity"], "authority_matrix": authority_matrix,
    }
    request = {**request_core, "owner_input_request_identity": seal("B2_DEVELOPMENT_PILOT11_OWNER_INPUT_REQUEST_V1", request_core)}
    audit_core = {
        "schema_name": "batch2-development-pilot11-owner-input-request-audit-v1", "schema_version": "1.0.0",
        "owner_input_request_identity": request["owner_input_request_identity"], "declaration_template_identity": template["template_identity"],
        "content_free": True, "pilots01_through_10_preserved": True, "constructors_v5_2_and_v5_3_preserved": True,
        "frozen_v5_3_identities_bound_but_not_released_or_invoked": True, "mechanism_neutral": True,
        "semantic_role_affordance_realization_and_witness_topology_unassigned": True, "blind_material_accessed": False,
        "proposition_evaluation_performed": False, "assignment_performed": False, "construction_authority": False,
        "deterministic_blockers": [], "external_input_blocker": "OWNER_AUTHORED_SOURCE_BYTES_AND_COMPLETED_DECLARATION_REQUIRED",
        "audit_verdict": "PASS_CONTENT_FREE_STOP_REQUIRED", "release_authority": False,
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT11_OWNER_INPUT_REQUEST_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot11-owner-declaration-template-v1.json", template)
    write("humor-mechanics-batch2-development-pilot11-owner-input-request-v1.json", request)
    write("humor-mechanics-batch2-development-pilot11-owner-input-request-audit-v1.json", audit)
    print(json.dumps({"status": request["status"], "request": request["owner_input_request_identity"],
                      "template": template["template_identity"], "audit": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
