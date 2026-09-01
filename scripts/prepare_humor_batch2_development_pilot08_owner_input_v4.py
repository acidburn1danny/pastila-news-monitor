"""Freeze content-free metadata-first owner-input preparation for Pilot 08 under Governance V4."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"
GOVERNANCE_COMMIT = "bd5331cf56edbf693d40b272e4fe6d0fc19d9b1d"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_json(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{GOVERNANCE_COMMIT}:{path}"], cwd=ROOT))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def write_json(name: str, value: dict[str, Any]) -> None:
    path = ARTIFACTS / name
    require(not path.exists(), f"artifact already exists: {name}")
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == GOVERNANCE_COMMIT, "HEAD differs from Governance V4 commit")
    analysis = git_json("docs/artifacts/humor-mechanics-batch2-pilot07-cross-pilot-voice-template-root-cause-analysis-v1.json")
    governance = git_json("docs/artifacts/humor-mechanics-batch2-template-diverse-creative-marking-governance-v4.json")
    schema = git_json("docs/artifacts/humor-mechanics-batch2-template-diverse-creative-marking-conformance-schema-v4.json")
    regression = git_json("docs/artifacts/humor-mechanics-batch2-pilot07-cross-pilot-voice-template-regression-v1.json")
    audit = git_json("docs/artifacts/humor-mechanics-batch2-template-diverse-creative-marking-governance-v4-audit-v1.json")
    require(analysis["analysis_identity"] == "c9d0c04ba2217789f8a1b313f4b37b461511efce8f340ad15f3f89299caa2346", "analysis")
    require(governance["governance_identity"] == "cc86204c6f199c80ef7c7bf87a58cf3c62d17acb1fe14bd2666bbf5ba86692f6", "governance")
    require(schema["schema_identity"] == "12c96a72555a26181abd5d0e7fa033a425fdacafb3a7fb197a21b39358da1dbe", "schema")
    require(regression["regression_identity"] == "24a6136e52dc6d86b61fc2ff93bf72b8308bd86ba58f7a3372e855309a3a1f05", "regression")
    require(audit["audit_identity"] == "6b731c0f525140a540d15ff7140cc9937265a651fd39006783317608ef25f6bb", "audit")
    require(audit["verdict"] == "PASS_SOURCE_ONLY_ZERO_CONSTRUCTION", "audit verdict")

    template_core = {
        "schema_name": "batch2-internally-owned-owner-input-pilot08-v1",
        "schema_version": "1.0.0",
        "pilot_id": "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-08",
        "source": {
            "filename": "owner-source-pilot08-v1.txt",
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
        "contributor": {
            key: "OWNER_MUST_SUPPLY_OR_CHOOSE"
            for key in (
                "public_identity",
                "legal_identity_commitment",
                "legal_identity_verification_reference",
                "role",
                "rights_holder_identity",
                "rights_holder_relationship",
                "identity_disclosure_approved_for_commit",
            )
        },
        "ownership_declarations": {
            key: "OWNER_MUST_CHOOSE_BOOLEAN"
            for key in (
                "original_authorship",
                "owns_or_controls_required_rights",
                "has_authority_to_make_each_selected_grant",
                "contains_undisclosed_third_party_material",
                "contains_private_or_confidential_information",
                "contains_personal_data",
                "contains_unlawfully_obtained_information",
                "contains_unattributed_quotation",
                "contains_reputation_sensitive_allegation",
            )
        },
        "independent_grants": {
            key: "OWNER_MUST_CHOOSE_BOOLEAN_INDEPENDENTLY"
            for key in (
                "immutable_archival",
                "factual_annotation_and_authority_binding",
                "internal_discovery",
                "construction_and_evaluation",
                "model_exposure",
                "training",
                "runtime_integration",
                "production_routing",
            )
        },
        "rights_terms": {
            key: "OWNER_MUST_CHOOSE_OR_DECLARE"
            for key in (
                "territory",
                "effective_at",
                "expires_at",
                "attribution_requirement",
                "compensation_terms",
                "revocation_terms",
                "correction_policy",
                "supersession_policy",
                "survival_of_completed_uses",
            )
        },
        "source_status_declarations": {
            "source_is_neutral_factual_authority": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_was_not_selected_or_shaped_for_any_mechanism_pool_target_assignment_obligation_or_creative_marker": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_contains_no_mechanism_obligation_creative_premise_candidate_or_template_marker": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_has_no_revision_sibling_same_event_or_syndication_relationship_with_pilots_01_02_03_04_05_06_07": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_does_not_reuse_pilots_01_02_03_04_05_06_07_wording_entities_events_or_source_structures": "OWNER_MUST_CHOOSE_BOOLEAN",
            "known_and_unknown_boundaries_are_explicit": "OWNER_MUST_CHOOSE_BOOLEAN",
        },
        "owner_instruction": {
            key: "OWNER_MUST_CHOOSE_BOOLEAN"
            for key in (
                "request_preingestion_validation_only",
                "permit_derived_hashes_and_coordinates",
                "permit_registered_custodial_signing_requests",
                "permit_git_object_archival",
                "permit_development_partition_seal",
                "operational_content_access_after_ingestion",
            )
        },
        "owner_confirmation": {
            "owner_identity": "OWNER_MUST_SUPPLY",
            "confirmed": "OWNER_MUST_CHOOSE_BOOLEAN",
            "confirmation_statement": "OWNER_MUST_SUPPLY_EXPLICIT_STATEMENT",
        },
    }
    template = {
        **template_core,
        "template_identity": seal("B2_DEVELOPMENT_PILOT08_OWNER_DECLARATION_TEMPLATE_V1", template_core),
    }

    authority_matrix = {
        key: False
        for key in (
            "source_acquisition",
            "content_access",
            "content_ingestion",
            "archive_write",
            "custodial_signing",
            "g01a_admission",
            "g01b_admission",
            "proposition_sufficiency_evaluation",
            "target_assignment",
            "obligation_assignment",
            "constructor_implementation",
            "constructor_release",
            "construction",
            "generation",
            "g04b_pool_certification",
            "model_exposure",
            "training",
            "runtime_integration",
            "production_routing",
        )
    }
    request_core = {
        "schema_name": "batch2-development-pilot08-owner-input-request-v1",
        "schema_version": "1.0.0",
        "status": "BLOCKED_AWAITING_OWNER_INPUT",
        "preparation_verdict": "PASS_CONTENT_FREE_METADATA_FIRST_OWNER_PACKAGE_GOVERNANCE_V4",
        "bound_governance_commit": GOVERNANCE_COMMIT,
        "root_cause_analysis_identity": analysis["analysis_identity"],
        "governance_identity": governance["governance_identity"],
        "conformance_schema_identity": schema["schema_identity"],
        "pilot07_regression_identity": regression["regression_identity"],
        "remediation_audit_identity": audit["audit_identity"],
        "pilot07_preservation": "IMMUTABLE_NONPOSITIVE_VOICE_REJECTION_UNCHANGED",
        "constructor_v1_preservation": "BYTE_EXACT_HISTORICAL_VERIFICATION_ONLY_NO_FUTURE_RELEASE",
        "content_accessed": False,
        "source_family_created": False,
        "blind_material_accessed": False,
        "owner_files_required": [
            {
                "filename": "owner-source-pilot08-v1.txt",
                "encoding": "UTF-8_NO_BOM",
                "line_endings": "LF_ONLY",
                "terminal_lf_count": 1,
                "content": "OWNER_AUTHORED_BYTE_EXACT_NEUTRAL_FACTUAL_SOURCE",
            },
            {
                "filename": "owner-declaration-pilot08-v1.json",
                "canonical_requirement": "UTF8_JSON_NO_BOM_LF_ONE_TERMINAL_LF",
                "content": "OWNER_COMPLETED_DECLARATION_FROM_TEMPLATE",
            },
        ],
        "source_content_requirements": {
            "minimum_independently_bindable_factual_propositions": 2,
            "must_be_owner_authored": True,
            "must_be_neutral_nonhumorous": True,
            "must_be_fresh_independent_source_event_topic_authority_and_revision_family": True,
            "must_expose_scope_modality_time_and_known_unknown_boundaries_where_applicable": True,
            "must_not_be_optimized_for_post_g01_sufficiency_assignment_obligation_or_creative_marking": True,
            "prohibited": [
                "PILOT01_THROUGH_07_WORDING_ENTITY_EVENT_OR_SOURCE_STRUCTURE_REUSE",
                "REVISION_SIBLING_SYNDICATION_OR_SAME_EVENT_RELATION_TO_PRIOR_PILOTS",
                "HUMOR_MECHANISM_OBLIGATION_OR_CREATIVE_MARKER_SHAPED_FRAMING",
                "GOVERNANCE_OR_INSTRUCTION_STYLE_LANGUAGE",
                "PERSONAL_PRIVATE_CONFIDENTIAL_SENSITIVE_ALLEGATION_OR_THIRD_PARTY_COPYRIGHTED_CONTENT",
                "MECHANISM_OBLIGATION_SUFFICIENCY_WITNESS_CREATIVE_PREMISE_OR_TEMPLATE_METADATA",
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
            "SEPARATELY_AUTHORIZED_FUTURE_CONSTRUCTOR_IMPLEMENTATION_AND_STATIC_AUDIT",
            "SEPARATELY_AUTHORIZED_G02B",
            "SEPARATELY_AUTHORIZED_ONE_ATTEMPT_CONSTRUCTION",
            "MANDATORY_POSTCONSTRUCTION_FRAGMENT_COLLISION_GATE_BEFORE_G02",
        ],
        "post_g01_boundary": {
            "proposition_evaluation_status": "NOT_PERFORMED",
            "assignment_status": "NOT_PERFORMED",
            "constructor_implementation_status": "NOT_PREPARED_V1_PROHIBITED_FOR_FUTURE_RELEASE",
            "fragment_denyset_status": "NOT_DERIVED",
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
    request = {
        **request_core,
        "owner_input_request_identity": seal("B2_DEVELOPMENT_PILOT08_OWNER_INPUT_REQUEST_V1", request_core),
    }
    audit_core = {
        "schema_name": "batch2-development-pilot08-owner-input-request-audit-v1",
        "schema_version": "1.0.0",
        "owner_input_request_identity": request["owner_input_request_identity"],
        "content_free": True,
        "pilot07_preserved": True,
        "constructor_v1_preserved_and_future_release_prohibited": True,
        "mechanism_neutral": True,
        "blind_material_accessed": False,
        "proposition_evaluation_performed": False,
        "assignment_performed": False,
        "constructor_implementation_or_release_performed": False,
        "source_selection_uses_downstream_governance_target_or_marker": False,
        "construction_authority": False,
        "deterministic_blockers": [],
        "external_input_blocker": "OWNER_AUTHORED_SOURCE_BYTES_AND_COMPLETED_DECLARATION_REQUIRED",
        "audit_verdict": "PASS_CONTENT_FREE_STOP_REQUIRED",
    }
    request_audit = {
        **audit_core,
        "audit_identity": seal("B2_DEVELOPMENT_PILOT08_OWNER_INPUT_REQUEST_AUDIT_V1", audit_core),
    }
    write_json("humor-mechanics-batch2-development-pilot08-owner-declaration-template-v1.json", template)
    write_json("humor-mechanics-batch2-development-pilot08-owner-input-request-v1.json", request)
    write_json("humor-mechanics-batch2-development-pilot08-owner-input-request-audit-v1.json", request_audit)
    print(json.dumps({
        "status": request["status"],
        "preparation_verdict": request["preparation_verdict"],
        "owner_input_request_identity": request["owner_input_request_identity"],
        "template_identity": template["template_identity"],
        "audit_identity": request_audit["audit_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
