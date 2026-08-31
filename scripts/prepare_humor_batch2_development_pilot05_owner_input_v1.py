"""Freeze the content-free owner-input package for DEVELOPMENT Pilot 05."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G04B_AUDIT_COMMIT = "9a5eddc8442a9119e22049b2221e34e56556588f"
GOVERNANCE_COMMIT = "618333a3db484da134904aea004a36e9cb0350d4"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), f"already exists: {path}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == G04B_AUDIT_COMMIT, "HEAD differs from the bound G04B audit commit")
    pool_audit = json.loads(subprocess.check_output(["git", "show", f"{G04B_AUDIT_COMMIT}:docs/artifacts/humor-mechanics-batch2-g04b-pilot03-pilot04-pool-audit-v1.json"], cwd=ROOT))
    governance = json.loads(subprocess.check_output(["git", "show", f"{GOVERNANCE_COMMIT}:docs/artifacts/humor-mechanics-batch2-successor-obligation-governance-v2.json"], cwd=ROOT))
    require(pool_audit["g04b_pool_audit_identity"] == "75b7644656e1e111f38998de07034aacca74c6eee0eccd813acbb201c0a433b7", "G04B audit identity")
    require(pool_audit["g04b_verdict"] == "POOL_REBALANCING_REQUIRED_NO_CERTIFICATION", "G04B verdict")
    require(governance["obligation_governance_identity"] == "874c5d611c5ab955e0f9d82aa5aa086fad98e065f66e20e9e236f48798287024", "Governance V2")

    template_core = {
        "schema_name": "batch2-internally-owned-owner-input-v1",
        "schema_version": "1.0.0",
        "pilot_id": "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-05",
        "source": {
            "filename": "owner-source-pilot05-v1.txt", "declared_encoding": "UTF-8", "bom": False,
            "line_endings": "LF", "terminal_lf_count": 1, "source_version": "OWNER_MUST_SUPPLY_SEMVER",
            "capture_timestamp": "OWNER_MUST_SUPPLY_ISO8601_WITH_OFFSET", "acquisition_timestamp": "OWNER_MUST_SUPPLY_ISO8601_WITH_OFFSET",
            "acquisition_channel": "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE", "intended_partition": "DEVELOPMENT",
            "subject_class": "OWNER_MUST_SUPPLY", "authority_scope": "OWNER_MUST_SUPPLY", "world_scope": "OWNER_MUST_SUPPLY",
        },
        "contributor": {key: "OWNER_MUST_SUPPLY_OR_CHOOSE" for key in ("public_identity", "legal_identity_commitment", "legal_identity_verification_reference", "role", "rights_holder_identity", "rights_holder_relationship", "identity_disclosure_approved_for_commit")},
        "ownership_declarations": {key: "OWNER_MUST_CHOOSE_BOOLEAN" for key in ("original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant", "contains_undisclosed_third_party_material", "contains_private_or_confidential_information", "contains_personal_data", "contains_unlawfully_obtained_information", "contains_unattributed_quotation", "contains_reputation_sensitive_allegation")},
        "independent_grants": {key: "OWNER_MUST_CHOOSE_BOOLEAN_INDEPENDENTLY" for key in ("immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation", "model_exposure", "training", "runtime_integration", "production_routing")},
        "rights_terms": {key: "OWNER_MUST_CHOOSE_OR_DECLARE" for key in ("territory", "effective_at", "expires_at", "attribution_requirement", "compensation_terms", "revocation_terms", "correction_policy", "supersession_policy", "survival_of_completed_uses")},
        "source_status_declarations": {
            "source_is_neutral_factual_authority": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_was_not_selected_for_a_humor_mechanism_or_pool_target": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_was_not_selected_or_shaped_using_any_operational_obligation": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_contains_no_mechanism_obligation_creative_premise_or_candidate": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_has_no_revision_sibling_same_event_or_syndication_relationship_with_pilots_01_02_03_04": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_does_not_reuse_pilots_01_02_03_04_wording_entities_events_or_creative_structures": "OWNER_MUST_CHOOSE_BOOLEAN",
            "known_and_unknown_boundaries_are_explicit": "OWNER_MUST_CHOOSE_BOOLEAN",
        },
        "owner_instruction": {key: "OWNER_MUST_CHOOSE_BOOLEAN" for key in ("request_preingestion_validation_only", "permit_derived_hashes_and_coordinates", "permit_registered_custodial_signing_requests", "permit_git_object_archival", "permit_development_partition_seal", "operational_content_access_after_ingestion")},
        "owner_confirmation": {"owner_identity": "OWNER_MUST_SUPPLY", "confirmed": "OWNER_MUST_CHOOSE_BOOLEAN", "confirmation_statement": "OWNER_MUST_SUPPLY_EXPLICIT_STATEMENT"},
    }
    template = {**template_core, "template_identity": seal("B2_DEVELOPMENT_PILOT05_OWNER_DECLARATION_TEMPLATE_V1", template_core)}
    request_core = {
        "schema_name": "batch2-development-pilot05-owner-input-request-v1", "schema_version": "1.0.0",
        "status": "BLOCKED_AWAITING_OWNER_INPUT", "preparation_verdict": "PASS_CONTENT_FREE_METADATA_FIRST_OWNER_PACKAGE",
        "bound_g04b_pool_audit_identity": pool_audit["g04b_pool_audit_identity"],
        "bound_g04b_receipt_identity": "17ef281ba9efab95268717dc0598db1b7f7ab052132f2cd18112908b07972e2b",
        "pool_status_preserved": "POOL_REBALANCING_REQUIRED_NO_CERTIFICATION",
        "governance_v2_identity": governance["obligation_governance_identity"], "content_accessed": False, "source_family_created": False,
        "owner_files_required": [
            {"filename": "owner-source-pilot05-v1.txt", "encoding": "UTF-8_NO_BOM", "line_endings": "LF_ONLY", "terminal_lf_count": 1, "content": "OWNER_AUTHORED_BYTE_EXACT_NEUTRAL_FACTUAL_SOURCE"},
            {"filename": "owner-declaration-pilot05-v1.json", "canonical_requirement": "UTF8_JSON_NO_BOM_LF_ONE_TERMINAL_LF", "content": "OWNER_COMPLETED_DECLARATION_FROM_TEMPLATE"},
        ],
        "source_content_requirements": {
            "minimum_independently_bindable_factual_propositions": 2, "must_be_owner_authored": True,
            "must_be_neutral_nonhumorous": True, "must_be_fresh_independent_source_event_topic_and_authority_family": True,
            "must_expose_scope_modality_time_and_known_unknown_boundaries_where_applicable": True,
            "prohibited": ["PILOT01_02_03_04_WORDING_ENTITY_EVENT_CREATIVE_PREMISE_OR_CONSTRUCTION_REUSE", "REVISION_SIBLING_SYNDICATION_OR_SAME_EVENT_RELATION_TO_PRIOR_PILOTS", "HUMOR_PUNCHLINE_RHETORICAL_QUESTION_PARODY", "METAPHOR_HEAVY_ANTHROPOMORPHIC_OR_MECHANISM_SHAPED_FRAMING", "GOVERNANCE_OR_INSTRUCTION_STYLE_LANGUAGE", "PERSONAL_PRIVATE_CONFIDENTIAL_SENSITIVE_OR_ALLEGATION_CONTENT", "THIRD_PARTY_COPYRIGHTED_SURFACE", "MECHANISM_OBLIGATION_OR_CREATIVE_PREMISE_METADATA"],
            "selection_must_not_use": ["TARGET_MECHANISM_OR_BATCH2_GAP", "POOL_SHORTCUT_CLOSURE_FRIENDLY_SOURCE_SHAPE", "GOVERNANCE_V2_CONSTRUCTOR_OBLIGATION", "PILOT01_02_03_04_SURFACES_OR_DIAGNOSTICS", "TARGET_FRIENDLY_TOPIC_GRAMMAR_PROPOSITION_TOPOLOGY_OR_SHAPE"],
        },
        "freshness_checks_after_submission": ["BYTE_HASH_AND_GIT_BLOB_DISTINCT_FROM_PILOTS_01_02_03_04", "NO_TRANSITIVE_SOURCE_EVENT_AUTHORITY_TOPIC_REVISION_SYNDICATION_OR_CREATIVE_FAMILY_RELATION", "NO_PRIOR_ASSIGNMENT_CONSTRUCTION_OR_DOWNSTREAM_EXPOSURE", "NO_BLIND_FAMILY_ACCESS", "CONTAMINATION_LEDGER_COMPLETE"],
        "post_g01_rebalancing_gate": {
            "timing": "ONLY_AFTER_G01A_AND_G01B_PASS",
            "different_label_blind_realization_obligation_family_required": True,
            "different_close_alternative_profile_required": True,
            "must_not_influence_source_selection_or_wording": True,
            "failure_disposition": "NO_SAFE_REBALANCING_ASSIGNMENT",
            "construction_forbidden_on_failure": True,
        },
        "prospective_path": ["STRICT_PREINGESTION_VALIDATION", "PROSPECTIVE_IDENTITIES_AND_UNSIGNED_SIGNING_PACKET", "OWNER_OPERATED_CUSTODIAL_SIGNATURES", "ATOMIC_IMMUTABLE_INGESTION", "G01A", "G01B", "POST_G01_REBALANCING_ASSIGNMENT_GATE", "SEPARATE_CONSTRUCTION_DECISION_IF_SAFE"],
        "unassigned": {"target_mechanism": True, "operational_obligation": True, "creative_premise_family_id": "UNASSIGNED"},
        "g04b_pool_certification_performed": False,
        "declaration_template_identity": template["template_identity"],
        "authority_matrix": {key: False for key in ("source_acquisition", "content_ingestion", "archive_write", "custodial_signing", "g01a_admission", "g01b_admission", "target_assignment", "obligation_assignment", "creative_premise_assignment", "construction", "generation", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    request = {**request_core, "owner_input_request_identity": seal("B2_DEVELOPMENT_PILOT05_OWNER_INPUT_REQUEST_V1", request_core)}
    audit_core = {"schema_name": "batch2-development-pilot05-owner-input-request-audit-v1", "schema_version": "1.0.0", "owner_input_request_identity": request["owner_input_request_identity"], "content_free": True, "prior_pilots_preserved": True, "mechanism_neutral": True, "blind_material_accessed": False, "g04b_performed": False, "rebalancing_requirement_deferred_until_post_g01": True, "source_selection_uses_rebalancing_target": False, "deterministic_blockers": [], "external_input_blocker": "OWNER_AUTHORED_SOURCE_BYTES_AND_COMPLETED_DECLARATION_REQUIRED", "audit_verdict": "PASS_CONTENT_FREE_STOP_REQUIRED"}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT05_OWNER_INPUT_REQUEST_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot05-owner-declaration-template-v1.json", template)
    write("humor-mechanics-batch2-development-pilot05-owner-input-request-v1.json", request)
    write("humor-mechanics-batch2-development-pilot05-owner-input-request-audit-v1.json", audit)
    print(json.dumps({"status": request["status"], "owner_input_request_identity": request["owner_input_request_identity"], "template_identity": template["template_identity"], "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
