"""Freeze the content-free owner input package for DEVELOPMENT Pilot 03."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
GOVERNANCE_COMMIT = "618333a3db484da134904aea004a36e9cb0350d4"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def write_json(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), f"already exists: {path}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == GOVERNANCE_COMMIT,
        "HEAD differs from Governance V2 commit",
    )
    governance = json.loads(subprocess.check_output([
        "git", "show", f"{GOVERNANCE_COMMIT}:docs/artifacts/humor-mechanics-batch2-successor-obligation-governance-v2.json"
    ], cwd=ROOT))
    schema = json.loads(subprocess.check_output([
        "git", "show", f"{GOVERNANCE_COMMIT}:docs/artifacts/humor-mechanics-batch2-successor-obligation-conformance-schema-v2.json"
    ], cwd=ROOT))
    audit = json.loads(subprocess.check_output([
        "git", "show", f"{GOVERNANCE_COMMIT}:docs/artifacts/humor-mechanics-batch2-successor-obligation-v2-naturalness-leakage-audit-v1.json"
    ], cwd=ROOT))
    require(governance["obligation_governance_identity"] == "874c5d611c5ab955e0f9d82aa5aa086fad98e065f66e20e9e236f48798287024", "governance")
    require(schema["conformance_schema_identity"] == "9470ce435de7ddcfea8dc4b3022b2ad697c2aa85fab44e8b532b4fa9850b0512", "schema")
    require(audit["audit_identity"] == "d1cb506a29a813821c0de844fbf7a702ee34139c086a881c3a1dc9824c7ceafe", "audit")

    template_core = {
        "schema_name": "batch2-internally-owned-owner-input-v1",
        "schema_version": "1.0.0",
        "pilot_id": "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-03",
        "source": {
            "filename": "owner-source-pilot03-v1.txt",
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
            "public_identity": "OWNER_MUST_SUPPLY_URN",
            "legal_identity": "OWNER_MUST_SUPPLY_COMMITTABLE_REFERENCE",
            "legal_identity_verification_reference": "OWNER_MUST_SUPPLY_NONSECRET_REFERENCE",
            "role": "OWNER_MUST_CHOOSE",
            "rights_holder_identity": "OWNER_MUST_SUPPLY_URN",
            "rights_holder_relationship": "OWNER_MUST_DECLARE",
            "identity_disclosure_approved_for_commit": "OWNER_MUST_CHOOSE_BOOLEAN",
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
            key: "OWNER_MUST_CHOOSE_BOOLEAN"
            for key in (
                "source_is_neutral_factual_authority",
                "source_was_not_selected_for_a_humor_mechanism",
                "source_was_not_selected_or_shaped_using_any_operational_obligation",
                "source_contains_no_mechanism_assignment",
                "source_contains_no_operational_obligation_assignment",
                "source_contains_no_creative_premise_assignment",
                "source_contains_no_constructed_humor_candidate",
                "source_has_no_pilot01_revision_sibling_same_event_or_syndication_relationship",
                "source_has_no_pilot02_revision_sibling_same_event_or_syndication_relationship",
                "source_does_not_reuse_pilot01_or_pilot02_wording_entities_or_event",
                "known_boundaries_are_explicit",
                "unknown_boundaries_are_explicit",
            )
        },
        "owner_instruction": {
            "requested_action": "OWNER_MUST_CHOOSE_PREINGESTION_VALIDATION_ONLY",
            "permit_derived_hashes_and_coordinates": "OWNER_MUST_CHOOSE_BOOLEAN",
            "permit_registered_custodial_signing_requests": "OWNER_MUST_CHOOSE_BOOLEAN",
            "permit_git_object_archival": "OWNER_MUST_CHOOSE_BOOLEAN",
            "permit_partition_seal_for_development_only": "OWNER_MUST_CHOOSE_BOOLEAN",
            "operational_content_access_after_ingestion": "OWNER_MUST_CHOOSE_BOOLEAN",
        },
        "owner_confirmation": {
            "owner_identity": "OWNER_MUST_SUPPLY",
            "confirmed": "OWNER_MUST_CHOOSE_BOOLEAN",
            "confirmation_statement": "OWNER_MUST_SUPPLY_EXPLICIT_STATEMENT",
        },
    }
    template = {
        **template_core,
        "template_identity": seal("B2_DEVELOPMENT_PILOT03_OWNER_DECLARATION_TEMPLATE_V1", template_core),
    }
    request_core = {
        "schema_name": "batch2-development-pilot03-owner-input-request-v1",
        "schema_version": "1.0.0",
        "status": "BLOCKED_AWAITING_OWNER_INPUT",
        "preparation_verdict": "PASS_CONTENT_FREE_METADATA_FIRST_OWNER_PACKAGE",
        "content_accessed": False,
        "source_family_created": False,
        "governance_v2": {
            "commit": GOVERNANCE_COMMIT,
            "root_cause_analysis_identity": "60a22bd7759d17bce22695bfdd16459760c5f3b6fc940d8497baf35a6f9dbdd2",
            "obligation_governance_identity": governance["obligation_governance_identity"],
            "conformance_schema_identity": schema["conformance_schema_identity"],
            "leakage_audit_identity": audit["audit_identity"],
            "pilot02_regression_identity": "ef182b817856037ede57c177ef2336f7944d954541772e791fb350ab08273320",
        },
        "owner_files_required": [
            {
                "filename": "owner-source-pilot03-v1.txt",
                "content": "OWNER_AUTHORED_BYTE_EXACT_SOURCE",
                "encoding": "UTF-8_NO_BOM",
                "line_endings": "LF_ONLY",
                "terminal_lf_count": 1,
            },
            {
                "filename": "owner-declaration-pilot03-v1.json",
                "content": "OWNER_COMPLETED_DECLARATION_FROM_TEMPLATE",
                "canonical_requirement": "UTF8_JSON_NO_BOM_LF_ONE_TERMINAL_LF",
            },
        ],
        "source_content_requirements": {
            "minimum_independently_bindable_factual_propositions": 2,
            "must_be_owner_authored": True,
            "must_be_neutral_nonhumorous": True,
            "must_expose_scope_modality_time_and_known_unknown_boundaries_where_applicable": True,
            "must_be_independent_new_event_and_family": True,
            "prohibited": [
                "PILOT01_OR_PILOT02_WORDING_ENTITY_EVENT_CREATIVE_PREMISE_OR_CONSTRUCTION_REUSE",
                "REVISION_SIBLING_SYNDICATION_OR_SAME_EVENT_RELATION_TO_PRIOR_PILOTS",
                "HUMOR_OR_PUNCHLINE",
                "RHETORICAL_QUESTION",
                "PARODY",
                "METAPHOR_HEAVY_OR_ANTHROPOMORPHIC_FRAMING",
                "GOVERNANCE_OR_INSTRUCTION_STYLE_LANGUAGE",
                "PRIVATE_PERSON_OR_PERSONAL_DATA",
                "PROTECTED_OR_VULNERABLE_TARGET",
                "ALLEGATION_OR_WRONGDOING",
                "PRIVATE_OR_CONFIDENTIAL_KNOWLEDGE",
                "SENSITIVE_ADVICE",
                "THIRD_PARTY_COPYRIGHTED_SURFACE",
                "MECHANISM_OBLIGATION_OR_CREATIVE_PREMISE_METADATA",
            ],
            "selection_must_not_use": [
                "GOVERNANCE_V1_OR_V2_CONSTRUCTOR_VISIBLE_OBLIGATION",
                "TARGET_MECHANISM_OR_BATCH2_GAP",
                "PILOT01_OR_PILOT02_CANDIDATE_SURFACE_OR_DIAGNOSTIC",
                "TARGET_FRIENDLY_TOPIC_GRAMMAR_PROPOSITION_TOPOLOGY_OR_SHAPE",
            ],
        },
        "freshness_checks_after_submission": [
            "SOURCE_SHA_AND_GIT_BLOB_DIFFER_FROM_PILOT01_AND_PILOT02",
            "NO_SOURCE_EVENT_AUTHORITY_TOPIC_REVISION_SYNDICATION_OR_SAME_EVENT_FAMILY_RELATION_TO_PRIOR_PILOTS",
            "NO_PRIOR_TARGET_OBLIGATION_OR_CREATIVE_PREMISE_ASSIGNMENT",
            "NO_PRIOR_CONSTRUCTION_MODEL_TRAINING_RUNTIME_OR_PRODUCTION_EXPOSURE",
            "NO_BLIND_FAMILY_ACCESS",
            "CONTAMINATION_LEDGER_COMPLETE",
        ],
        "prospective_gate_path": [
            "OWNER_SUBMISSION",
            "STRICT_PREINGESTION_VALIDATION_SEPARATELY_AUTHORIZED",
            "PROSPECTIVE_IDENTITIES_AND_UNSIGNED_SIGNING_PACKET_SEPARATELY_AUTHORIZED",
            "CUSTODIAL_SIGNATURES_OWNER_OPERATED",
            "ATOMIC_IMMUTABLE_INGESTION_SEPARATELY_AUTHORIZED",
            "G01A_RIGHTS_PROVENANCE_AUTHORITY_SEPARATELY_AUTHORIZED",
            "G01B_FAMILY_DEVELOPMENT_PARTITION_ADMISSION_SEPARATELY_AUTHORIZED",
        ],
        "identity_timing": {
            "source_commitment": "AFTER_EXACT_BYTES",
            "rights_identity": "AFTER_COMPLETED_DECLARATION",
            "authority_envelope": "AFTER_PROPOSITION_BINDING",
            "family_closure": "AFTER_DUPLICATE_REVISION_SYNDICATION_SAME_EVENT_AUDIT",
            "partition_identity": "AFTER_G01B_AND_AUTHORIZED_CUSTODIAL_SEAL",
        },
        "unassigned": {
            "target_mechanism": True,
            "operational_obligation": True,
            "creative_premise_family_id": "UNASSIGNED",
        },
        "content_free_exposure_record": {
            "operation": "PILOT03_OWNER_INPUT_TEMPLATE_PREPARATION",
            "source_or_family_identity": "NOT_YET_EXISTS",
            "blind_material_accessed": False,
            "candidate_or_source_surface_accessed": False,
            "mechanism_reasoning_performed": False,
            "prior_candidate_surfaces_exposed_to_owner_package": False,
        },
        "declaration_template_identity": template["template_identity"],
        "authority_matrix": {
            key: False
            for key in (
                "source_acquisition",
                "content_ingestion",
                "archive_write",
                "custodial_signing",
                "g01a_admission",
                "g01b_admission",
                "family_seal",
                "target_assignment",
                "obligation_assignment",
                "creative_premise_assignment",
                "construction",
                "generation",
                "model_exposure",
                "training",
                "runtime_integration",
                "production_routing",
            )
        },
    }
    request = {
        **request_core,
        "owner_input_request_identity": seal("B2_DEVELOPMENT_PILOT03_OWNER_INPUT_REQUEST_V1", request_core),
    }
    audit_core = {
        "schema_name": "batch2-development-pilot03-owner-input-request-audit-v1",
        "schema_version": "1.0.0",
        "owner_input_request_identity": request["owner_input_request_identity"],
        "declaration_template_identity": template["template_identity"],
        "checks": {
            "governance_v2_exact": True,
            "owner_authority_not_fabricated": True,
            "source_content_not_authored_acquired_or_selected": True,
            "no_prior_candidate_surface_in_package": True,
            "obligation_not_used_for_source_selection": True,
            "freshness_against_both_prior_pilots_required": True,
            "no_family_identity_before_bytes": True,
            "no_g01_verdict_before_validation": True,
            "rights_grants_owner_selected_independently": True,
            "no_blind_access": True,
            "all_operational_authorities_false": True,
        },
        "deterministic_blockers": [],
        "external_input_blocker": "OWNER_AUTHORED_SOURCE_BYTES_AND_COMPLETED_DECLARATION_REQUIRED",
        "audit_verdict": "PASS_CONTENT_FREE_STOP_REQUIRED",
    }
    audit_out = {
        **audit_core,
        "audit_identity": seal("B2_DEVELOPMENT_PILOT03_OWNER_INPUT_REQUEST_AUDIT_V1", audit_core),
    }
    write_json("humor-mechanics-batch2-development-pilot03-owner-declaration-template-v1.json", template)
    write_json("humor-mechanics-batch2-development-pilot03-owner-input-request-v1.json", request)
    write_json("humor-mechanics-batch2-development-pilot03-owner-input-request-audit-v1.json", audit_out)
    print(json.dumps({
        "preparation_verdict": request["preparation_verdict"],
        "status": request["status"],
        "owner_input_request_identity": request["owner_input_request_identity"],
        "declaration_template_identity": template["template_identity"],
        "audit_identity": audit_out["audit_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
