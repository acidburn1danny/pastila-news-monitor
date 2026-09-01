"""Freeze content-free metadata-first owner-input preparation for Pilot 09 under Governance V5."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
FREEZE_COMMIT = "17cf86470d098ddddd9d5061d86fe184c43c6ea7"


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
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == FREEZE_COMMIT, "HEAD")
    governance = git_json("docs/artifacts/humor-mechanics-batch2-typed-operand-closed-construction-governance-v5.json")
    schema = git_json("docs/artifacts/humor-mechanics-batch2-typed-operand-closed-construction-conformance-schema-v5.json")
    contract = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-contract-v5.json")
    implementation = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v5.json")
    static_audit = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-static-audit-v1.json")
    regression = git_json("docs/artifacts/humor-mechanics-batch2-pilot08-operand-closure-regression-v1.json")
    require(governance["governance_identity"] == "e81ee4eff9044ee16180ef36a7508fe9f1e7c784fa6830299588cea16c2d3a3e", "governance")
    require(schema["schema_identity"] == "29d7b0f97008ad38e64b8e966f398d829a66299ec805290ebbec3f92848efab6", "schema")
    require(contract["constructor_contract_identity"] == "e42f4741ddab7a6acbdd16f34804cd55408ca5a5428433be3c55eb9b74163c5a", "contract")
    require(implementation["constructor_implementation_identity"] == "caf85ada6fcd296d3798b5d47838d7b8a39d029dac5f6ecae68ace58712b9d61", "implementation")
    require(static_audit["audit_identity"] == "8451c13e5c5ab887e7001e8e090a54cf2d95643d113011e14b217d8f95f66225", "audit")
    require(static_audit["verdict"] == "PASS_IMPLEMENTATION_AND_STATIC_AUDIT_ZERO_CONSTRUCTION_NO_RELEASE", "audit verdict")
    require(regression["regression_identity"] == "e91926a00312b556b3d095abc7ce666b6cd61b2d863c01b5378be43bac1faae8", "regression")

    template_core = {
        "schema_name": "batch2-internally-owned-owner-input-pilot09-v1",
        "schema_version": "1.0.0",
        "pilot_id": "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-09",
        "source": {
            "filename": "owner-source-pilot09-v1.txt",
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
            "source_was_not_selected_or_shaped_for_any_mechanism_pool_target_assignment_obligation_constructor_or_creative_marker": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_contains_no_mechanism_obligation_creative_premise_candidate_constructor_test_or_template_marker": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_has_no_revision_sibling_same_event_or_syndication_relationship_with_pilots_01_02_03_04_05_06_07_08": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_does_not_reuse_pilots_01_02_03_04_05_06_07_08_wording_entities_events_or_source_structures": "OWNER_MUST_CHOOSE_BOOLEAN",
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
    template = {**template_core, "template_identity": seal("B2_DEVELOPMENT_PILOT09_OWNER_DECLARATION_TEMPLATE_V1", template_core)}
    authority_matrix = {key: False for key in (
        "source_acquisition", "content_access", "content_ingestion", "archive_write", "custodial_signing",
        "g01a_admission", "g01b_admission", "proposition_sufficiency_evaluation", "target_assignment",
        "obligation_assignment", "constructor_source_compatibility_check", "constructor_release", "construction",
        "generation", "fragment_collision_evaluation", "g04b_pool_certification", "model_exposure", "training",
        "runtime_integration", "production_routing",
    )}
    request_core = {
        "schema_name": "batch2-development-pilot09-owner-input-request-v1",
        "schema_version": "1.0.0",
        "status": "BLOCKED_AWAITING_OWNER_INPUT",
        "preparation_verdict": "PASS_CONTENT_FREE_METADATA_FIRST_OWNER_PACKAGE_GOVERNANCE_V5",
        "bound_freeze_commit": FREEZE_COMMIT,
        "governance_identity": governance["governance_identity"],
        "conformance_schema_identity": schema["schema_identity"],
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "constructor_static_audit_identity": static_audit["audit_identity"],
        "pilot08_regression_identity": regression["regression_identity"],
        "constructor_v4_preservation": "BYTE_EXACT_HISTORICAL_VERIFICATION_ONLY_NO_FUTURE_RELEASE",
        "pilot08_preservation": "IMMUTABLE_NONPOSITIVE_G02C_REJECTION_UNCHANGED",
        "content_accessed": False,
        "source_family_created": False,
        "blind_material_accessed": False,
        "owner_files_required": [
            {"filename": "owner-source-pilot09-v1.txt", "encoding": "UTF-8_NO_BOM", "line_endings": "LF_ONLY", "terminal_lf_count": 1, "content": "OWNER_AUTHORED_BYTE_EXACT_NEUTRAL_FACTUAL_SOURCE"},
            {"filename": "owner-declaration-pilot09-v1.json", "canonical_requirement": "UTF8_JSON_NO_BOM_LF_ONE_TERMINAL_LF", "content": "OWNER_COMPLETED_DECLARATION_FROM_TEMPLATE"},
        ],
        "source_content_requirements": {
            "minimum_independently_bindable_factual_propositions": 2,
            "must_be_owner_authored": True,
            "must_be_neutral_nonhumorous": True,
            "must_be_fresh_independent_source_event_topic_authority_and_revision_family": True,
            "must_expose_scope_modality_time_and_known_unknown_boundaries_where_applicable": True,
            "must_not_be_optimized_for_post_g01_sufficiency_assignment_obligation_constructor_compatibility_or_creative_marking": True,
            "prohibited": [
                "PILOT01_THROUGH_08_WORDING_ENTITY_EVENT_OR_SOURCE_STRUCTURE_REUSE",
                "REVISION_SIBLING_SYNDICATION_OR_SAME_EVENT_RELATION_TO_PRIOR_PILOTS",
                "HUMOR_MECHANISM_OBLIGATION_CONSTRUCTOR_OR_CREATIVE_MARKER_SHAPED_FRAMING",
                "GOVERNANCE_OR_INSTRUCTION_STYLE_LANGUAGE",
                "PERSONAL_PRIVATE_CONFIDENTIAL_SENSITIVE_ALLEGATION_OR_THIRD_PARTY_COPYRIGHTED_CONTENT",
                "MECHANISM_OBLIGATION_SUFFICIENCY_WITNESS_CREATIVE_PREMISE_CONSTRUCTOR_TEST_OR_TEMPLATE_METADATA",
            ],
        },
        "mandatory_phase_order": [
            "STRICT_PREINGESTION_VALIDATION", "PROSPECTIVE_IDENTITIES_AND_UNSIGNED_SIGNING_PACKET",
            "OWNER_OPERATED_CUSTODIAL_SIGNATURES", "ATOMIC_IMMUTABLE_INGESTION", "G01A", "G01B",
            "SEPARATELY_AUTHORIZED_PROPOSITION_SUFFICIENCY_GATE", "SEPARATELY_AUTHORIZED_ASSIGNMENT_DESIGN",
            "SEPARATELY_AUTHORIZED_CONSTRUCTOR_V5_SOURCE_COMPATIBILITY_STATIC_CHECK", "SEPARATELY_AUTHORIZED_G02B",
            "SEPARATELY_AUTHORIZED_ONE_ATTEMPT_CONSTRUCTION",
            "MANDATORY_POSTCONSTRUCTION_FRAGMENT_COLLISION_GATE_BEFORE_G02",
        ],
        "post_g01_boundary": {
            "proposition_evaluation_status": "NOT_PERFORMED",
            "assignment_status": "NOT_PERFORMED",
            "constructor_source_compatibility_status": "NOT_PERFORMED",
            "constructor_release_status": "NOT_PERFORMED",
            "fragment_denyset_status": "NOT_DERIVED_FOR_PILOT09",
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
        },
        "declaration_template_identity": template["template_identity"],
        "authority_matrix": authority_matrix,
    }
    request = {**request_core, "owner_input_request_identity": seal("B2_DEVELOPMENT_PILOT09_OWNER_INPUT_REQUEST_V1", request_core)}
    audit_core = {
        "schema_name": "batch2-development-pilot09-owner-input-request-audit-v1",
        "schema_version": "1.0.0",
        "owner_input_request_identity": request["owner_input_request_identity"],
        "content_free": True,
        "pilot08_and_constructor_v4_preserved": True,
        "constructor_v5_identity_bound_but_not_released_or_invoked": True,
        "mechanism_neutral": True,
        "blind_material_accessed": False,
        "proposition_evaluation_performed": False,
        "assignment_performed": False,
        "constructor_source_compatibility_or_release_performed": False,
        "source_selection_uses_downstream_target_obligation_constructor_or_marker": False,
        "construction_authority": False,
        "deterministic_blockers": [],
        "external_input_blocker": "OWNER_AUTHORED_SOURCE_BYTES_AND_COMPLETED_DECLARATION_REQUIRED",
        "audit_verdict": "PASS_CONTENT_FREE_STOP_REQUIRED",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT09_OWNER_INPUT_REQUEST_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot09-owner-declaration-template-v1.json", template)
    write("humor-mechanics-batch2-development-pilot09-owner-input-request-v1.json", request)
    write("humor-mechanics-batch2-development-pilot09-owner-input-request-audit-v1.json", audit)
    print(json.dumps({
        "status": request["status"],
        "preparation_verdict": request["preparation_verdict"],
        "owner_input_request_identity": request["owner_input_request_identity"],
        "template_identity": template["template_identity"],
        "audit_identity": audit["audit_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
