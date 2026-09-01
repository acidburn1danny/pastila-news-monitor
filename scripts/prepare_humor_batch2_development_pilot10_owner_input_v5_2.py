"""Freeze content-free metadata-first owner-input preparation for Pilot 10 under V5.2."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
FREEZE_COMMIT = "9d652f41ef8a5db3b81d4537d025b5f3875c4b26"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_json(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{FREEZE_COMMIT}:{path}"], cwd=ROOT))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), "artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == FREEZE_COMMIT, "HEAD")
    contract = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-contract-v5-2.json")
    governance = git_json("docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-governance-v5-2.json")
    schema = git_json("docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-conformance-schema-v5-2.json")
    implementation = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v5-2.json")
    runtime_audit = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-2-runtime-static-audit-v1.json")
    regression = git_json("docs/artifacts/humor-mechanics-batch2-pilot09-plan-to-surface-regression-v1.json")
    require(contract["constructor_contract_identity"] == "69138467540b37cbfb8444596d9a37119f8b74d002e0c491c8ff599ce77cec77", "contract")
    require(governance["governance_identity"] == "80bbf059956424ce6f20885de51ce900f6116b40a223a107a46a29d3b012efc6", "governance")
    require(schema["schema_identity"] == "084ddf4d8e9f215db3665370221260c351d3befe747c4dbb45ab35baac4c993b", "schema")
    require(implementation["constructor_implementation_identity"] == "bdf48e9942f097f0259831c0f2f611e50644cdbe7179a2dc7d990bf9ab2b5493", "implementation")
    require(runtime_audit["static_audit_identity"] == "1171e1a53acbb733c530d2f2e4fa753284a9f4747ab905d9c2a57d7b22b3399d", "audit")
    require(runtime_audit["verdict"] == "PASS_V5_2_REALIZATION_PROVIDER_AND_CANDIDATE_EMITTER_IMPLEMENTATION_STATIC_AUDIT_ZERO_CONSTRUCTION_NO_RELEASE", "audit verdict")
    require(regression["regression_identity"] == "46555766257446703ef92cf4b3fe48716a55a1daf2c14ba5749890d028ae7f00", "regression")

    template_core = {
        "schema_name": "batch2-internally-owned-owner-input-pilot10-v1",
        "schema_version": "1.0.0",
        "pilot_id": "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-10",
        "source": {
            "filename": "owner-source-pilot10-v1.txt",
            "declared_encoding": "UTF-8",
            "bom": False,
            "line_endings": "LF",
            "terminal_lf_count": 1,
            "source_version": "OWNER_MUST_SUPPLY_SEMVER",
            "capture_timestamp": "OWNER_MUST_SUPPLY_ISO8601_WITH_OFFSET",
            "acquisition_timestamp": "OWNER_MUST_SUPPLY_ISO8601_WITH_OFFSET",
            "acquisition_channel": "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE",
            "intended_partition": "DEVELOPMENT",
            "subject_class": "OWNER_MUST_SUPPLY",
            "authority_scope": "OWNER_MUST_SUPPLY",
            "world_scope": "OWNER_MUST_SUPPLY",
        },
        "contributor": {key: "OWNER_MUST_SUPPLY_OR_CHOOSE" for key in (
            "public_identity", "legal_identity_commitment", "legal_identity_verification_reference", "role",
            "rights_holder_identity", "rights_holder_relationship", "identity_disclosure_approved_for_commit",
        )},
        "ownership_declarations": {key: "OWNER_MUST_CHOOSE_BOOLEAN" for key in (
            "original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant",
            "contains_undisclosed_third_party_material", "contains_private_or_confidential_information",
            "contains_personal_data", "contains_unlawfully_obtained_information", "contains_unattributed_quotation",
            "contains_reputation_sensitive_allegation",
        )},
        "independent_grants": {key: "OWNER_MUST_CHOOSE_BOOLEAN_INDEPENDENTLY" for key in (
            "immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery",
            "construction_and_evaluation", "model_exposure", "training", "runtime_integration", "production_routing",
        )},
        "rights_terms": {key: "OWNER_MUST_CHOOSE_OR_DECLARE" for key in (
            "territory", "effective_at", "expires_at", "attribution_requirement", "compensation_terms",
            "revocation_terms", "correction_policy", "supersession_policy", "survival_of_completed_uses",
        )},
        "source_status_declarations": {
            "source_is_neutral_factual_authority": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_was_not_selected_or_shaped_for_any_mechanism_pool_target_proposition_result_assignment_obligation_constructor_compatibility_realization_plan_witness_topology_creative_marker_or_expected_positive_outcome": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_contains_no_mechanism_obligation_creative_premise_candidate_constructor_test_witness_or_template_marker": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_has_no_revision_sibling_same_event_or_syndication_relationship_with_pilots_01_02_03_04_05_06_07_08_09": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_does_not_reuse_pilots_01_02_03_04_05_06_07_08_09_wording_entities_events_or_source_structures": "OWNER_MUST_CHOOSE_BOOLEAN",
            "known_and_unknown_boundaries_are_explicit": "OWNER_MUST_CHOOSE_BOOLEAN",
        },
        "owner_instruction": {key: "OWNER_MUST_CHOOSE_BOOLEAN" for key in (
            "request_preingestion_validation_only", "permit_derived_hashes_and_coordinates",
            "permit_registered_custodial_signing_requests", "permit_git_object_archival",
            "permit_development_partition_seal", "operational_content_access_after_ingestion",
        )},
        "owner_confirmation": {
            "owner_identity": "OWNER_MUST_SUPPLY",
            "confirmed": "OWNER_MUST_CHOOSE_BOOLEAN",
            "confirmation_statement": "OWNER_MUST_SUPPLY_EXPLICIT_STATEMENT",
        },
    }
    template = {**template_core, "template_identity": seal("B2_DEVELOPMENT_PILOT10_OWNER_DECLARATION_TEMPLATE_V1", template_core)}
    authority_matrix = {key: False for key in (
        "source_acquisition", "content_access", "content_ingestion", "archive_write", "custodial_signing",
        "g01a_admission", "g01b_admission", "proposition_sufficiency_evaluation", "target_assignment",
        "obligation_assignment", "constructor_source_compatibility_check", "constructor_release", "construction",
        "generation", "post_realization_pre_emission_conformance", "candidate_emission",
        "fragment_collision_evaluation", "g02", "g02c", "g03", "g04b_pool_certification",
        "model_exposure", "training", "runtime_integration", "production_routing",
    )}
    request_core = {
        "schema_name": "batch2-development-pilot10-owner-input-request-v1",
        "schema_version": "1.0.0",
        "status": "BLOCKED_AWAITING_OWNER_INPUT",
        "preparation_verdict": "PASS_CONTENT_FREE_METADATA_FIRST_OWNER_PACKAGE_GOVERNANCE_V5_2",
        "bound_freeze_commit": FREEZE_COMMIT,
        "governance_identity": governance["governance_identity"],
        "conformance_schema_identity": schema["schema_identity"],
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "realization_provider_implementation_identity": implementation["realization_provider_implementation_identity"],
        "candidate_emitter_implementation_identity": implementation["candidate_emitter_implementation_identity"],
        "constructor_static_audit_identity": runtime_audit["static_audit_identity"],
        "pilot09_regression_identity": regression["regression_identity"],
        "pilot09_preservation": "IMMUTABLE_NONPOSITIVE_G02C_REJECTION_UNCHANGED",
        "constructor_v5_1_preservation": "BYTE_EXACT_HISTORICAL_VERIFICATION_ONLY_NO_FUTURE_RELEASE",
        "content_accessed": False,
        "source_family_created": False,
        "blind_material_accessed": False,
        "owner_files_required": [
            {"filename": "owner-source-pilot10-v1.txt", "encoding": "UTF-8_NO_BOM", "line_endings": "LF_ONLY", "terminal_lf_count": 1, "content": "OWNER_AUTHORED_BYTE_EXACT_NEUTRAL_FACTUAL_SOURCE"},
            {"filename": "owner-declaration-pilot10-v1.json", "canonical_requirement": "UTF8_JSON_NO_BOM_LF_ONE_TERMINAL_LF", "content": "OWNER_COMPLETED_DECLARATION_FROM_TEMPLATE"},
        ],
        "source_content_requirements": {
            "minimum_independently_bindable_factual_propositions": 2,
            "must_be_owner_authored": True,
            "must_be_neutral_nonhumorous": True,
            "must_be_fresh_independent_source_event_topic_authority_and_revision_family": True,
            "must_expose_scope_modality_time_and_known_unknown_boundaries_where_applicable": True,
            "must_not_be_optimized_for_any_downstream_gate_or_result": True,
            "prohibited": [
                "PILOT01_THROUGH_09_WORDING_ENTITY_EVENT_OR_SOURCE_STRUCTURE_REUSE",
                "REVISION_SIBLING_SYNDICATION_OR_SAME_EVENT_RELATION_TO_PRIOR_PILOTS",
                "MECHANISM_POOL_TARGET_PROPOSITION_RESULT_ASSIGNMENT_OR_OBLIGATION_SHAPED_FRAMING",
                "CONSTRUCTOR_COMPATIBILITY_REALIZATION_PLAN_WITNESS_TOPOLOGY_OR_CREATIVE_MARKER_SHAPING",
                "EXPECTED_POSITIVE_OUTCOME_OPTIMIZATION",
                "GOVERNANCE_OR_INSTRUCTION_STYLE_LANGUAGE",
                "PERSONAL_PRIVATE_CONFIDENTIAL_SENSITIVE_ALLEGATION_OR_THIRD_PARTY_COPYRIGHTED_CONTENT",
            ],
        },
        "mandatory_phase_order": [
            "STRICT_PREINGESTION_VALIDATION",
            "PROSPECTIVE_IDENTITIES_AND_UNSIGNED_SIGNING_PACKET",
            "OWNER_OPERATED_CUSTODIAL_SIGNATURES",
            "ATOMIC_IMMUTABLE_INGESTION",
            "G01A",
            "G01B",
            "SEPARATELY_AUTHORIZED_PROPOSITION_SUFFICIENCY_GATE",
            "SEPARATELY_AUTHORIZED_ASSIGNMENT_DESIGN",
            "SEPARATELY_AUTHORIZED_CONSTRUCTOR_V5_2_SOURCE_COMPATIBILITY_STATIC_CHECK",
            "SEPARATELY_AUTHORIZED_G02B_RELEASE_DECISION",
            "SEPARATELY_AUTHORIZED_ONE_ATTEMPT_CONSTRUCTION",
            "MANDATORY_V5_2_POST_REALIZATION_PRE_EMISSION_CONFORMANCE",
            "MANDATORY_POSTCONSTRUCTION_FRAGMENT_COLLISION_GATE_BEFORE_G02",
        ],
        "post_g01_boundary": {
            "proposition_evaluation_status": "NOT_PERFORMED",
            "assignment_status": "NOT_PERFORMED",
            "constructor_source_compatibility_status": "NOT_PERFORMED",
            "constructor_release_status": "NOT_PERFORMED",
            "realization_or_witness_planning_status": "NOT_PERFORMED",
            "earliest_permitted_time": "ONLY_AFTER_G01A_AND_G01B_PASS",
            "must_not_influence_source_selection_wording_ingestion_or_g01": True,
        },
        "unassigned": {
            "source_family_id": "UNASSIGNED_PENDING_OWNER_BYTES",
            "event_family_id": "UNASSIGNED_PENDING_OWNER_BYTES",
            "authority_family_id": "UNASSIGNED_PENDING_OWNER_BYTES",
            "topic_entity_family_id": "UNASSIGNED_PENDING_OWNER_BYTES",
            "selected_proposition": "UNASSIGNED",
            "target_mechanism": "UNASSIGNED",
            "operational_obligation": "UNASSIGNED",
            "creative_premise_family_id": "UNASSIGNED",
            "construction_revision_family_id": "UNASSIGNED",
            "creative_marker_family_id": "UNASSIGNED",
            "realization_plan": "UNASSIGNED",
            "witness_topology": "UNASSIGNED",
        },
        "declaration_template_identity": template["template_identity"],
        "authority_matrix": authority_matrix,
    }
    request = {**request_core, "owner_input_request_identity": seal("B2_DEVELOPMENT_PILOT10_OWNER_INPUT_REQUEST_V1", request_core)}
    audit_core = {
        "schema_name": "batch2-development-pilot10-owner-input-request-audit-v1",
        "schema_version": "1.0.0",
        "owner_input_request_identity": request["owner_input_request_identity"],
        "declaration_template_identity": template["template_identity"],
        "content_free": True,
        "pilot09_and_constructor_v5_1_preserved": True,
        "frozen_v5_2_identities_bound_but_not_released_or_invoked": True,
        "mechanism_neutral": True,
        "blind_material_accessed": False,
        "proposition_evaluation_performed": False,
        "assignment_performed": False,
        "constructor_compatibility_release_or_invocation_performed": False,
        "realization_plan_or_witness_topology_selected": False,
        "source_selection_uses_downstream_gate_or_expected_result": False,
        "construction_authority": False,
        "deterministic_blockers": [],
        "external_input_blocker": "OWNER_AUTHORED_SOURCE_BYTES_AND_COMPLETED_DECLARATION_REQUIRED",
        "audit_verdict": "PASS_CONTENT_FREE_STOP_REQUIRED",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT10_OWNER_INPUT_REQUEST_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot10-owner-declaration-template-v1.json", template)
    write("humor-mechanics-batch2-development-pilot10-owner-input-request-v1.json", request)
    write("humor-mechanics-batch2-development-pilot10-owner-input-request-audit-v1.json", audit)
    print(json.dumps({"status": request["status"], "preparation_verdict": request["preparation_verdict"],
                      "owner_input_request_identity": request["owner_input_request_identity"],
                      "template_identity": template["template_identity"], "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
