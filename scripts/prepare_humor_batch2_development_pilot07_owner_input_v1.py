"""Freeze content-free metadata-first owner input preparation for Pilot 07."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "c800455a3c6b6a12724399588ab742c8396de816"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT))


def write(name: str, value: Any) -> None:
    path = ART / name
    if path.exists():
        raise SystemExit("artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() != COMMIT:
        raise SystemExit("HEAD")
    governance = load("docs/artifacts/humor-mechanics-batch2-order-robust-causal-spine-governance-v3.json")
    schema = load("docs/artifacts/humor-mechanics-batch2-order-robust-causal-spine-conformance-schema-v3.json")
    audit = load("docs/artifacts/humor-mechanics-batch2-order-robust-causal-spine-governance-v3-audit-v1.json")
    if governance["governance_identity"] != "4848bd025e43eff6652e4c2024072760d372ca4ac7427e5f21e1d2c4bcdb35dc":
        raise SystemExit("governance")
    if schema["schema_identity"] != "28dfdab8dd9112d0148dad0b513155b5ae14445f5daee359b7a35d1bc5eb1c2c":
        raise SystemExit("schema")
    if audit["audit_identity"] != "284334b375206be7abb483e16cc0e64e5034bd7bbf30f379d4a002bf59770d66" or audit["verdict"] != "PASS_SOURCE_ONLY_ZERO_CONSTRUCTION":
        raise SystemExit("audit")
    template_core = {
        "schema_name": "batch2-internally-owned-owner-input-pilot07-v1", "schema_version": "1.0.0",
        "pilot_id": "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-07",
        "source": {"filename": "owner-source-pilot07-v1.txt", "declared_encoding": "UTF-8", "bom": False,
                   "line_endings": "LF", "terminal_lf_count": 1, "source_version": "OWNER_MUST_SUPPLY_SEMVER",
                   "capture_timestamp": "OWNER_MUST_SUPPLY_ISO8601_WITH_OFFSET", "acquisition_timestamp": "OWNER_MUST_SUPPLY_ISO8601_WITH_OFFSET",
                   "acquisition_channel": "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE", "intended_partition": "DEVELOPMENT",
                   "subject_class": "OWNER_MUST_SUPPLY", "authority_scope": "OWNER_MUST_SUPPLY", "world_scope": "OWNER_MUST_SUPPLY"},
        "contributor": {key: "OWNER_MUST_SUPPLY_OR_CHOOSE" for key in ("public_identity", "legal_identity_commitment", "legal_identity_verification_reference",
                                                                           "role", "rights_holder_identity", "rights_holder_relationship", "identity_disclosure_approved_for_commit")},
        "ownership_declarations": {key: "OWNER_MUST_CHOOSE_BOOLEAN" for key in ("original_authorship", "owns_or_controls_required_rights",
                                                                                   "has_authority_to_make_each_selected_grant", "contains_undisclosed_third_party_material",
                                                                                   "contains_private_or_confidential_information", "contains_personal_data",
                                                                                   "contains_unlawfully_obtained_information", "contains_unattributed_quotation",
                                                                                   "contains_reputation_sensitive_allegation")},
        "independent_grants": {key: "OWNER_MUST_CHOOSE_BOOLEAN_INDEPENDENTLY" for key in ("immutable_archival", "factual_annotation_and_authority_binding",
                                                                                            "internal_discovery", "construction_and_evaluation", "model_exposure",
                                                                                            "training", "runtime_integration", "production_routing")},
        "rights_terms": {key: "OWNER_MUST_CHOOSE_OR_DECLARE" for key in ("territory", "effective_at", "expires_at", "attribution_requirement",
                                                                            "compensation_terms", "revocation_terms", "correction_policy", "supersession_policy",
                                                                            "survival_of_completed_uses")},
        "source_status_declarations": {
            "source_is_neutral_factual_authority": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_was_not_selected_or_shaped_for_any_humor_mechanism_pool_target_assignment_or_obligation": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_contains_no_mechanism_obligation_creative_premise_or_candidate": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_has_no_revision_sibling_same_event_or_syndication_relationship_with_pilots_01_02_03_04_05_06": "OWNER_MUST_CHOOSE_BOOLEAN",
            "source_does_not_reuse_pilots_01_02_03_04_05_06_wording_entities_events_or_creative_structures": "OWNER_MUST_CHOOSE_BOOLEAN",
            "known_and_unknown_boundaries_are_explicit": "OWNER_MUST_CHOOSE_BOOLEAN"},
        "owner_instruction": {key: "OWNER_MUST_CHOOSE_BOOLEAN" for key in ("request_preingestion_validation_only", "permit_derived_hashes_and_coordinates",
                                                                              "permit_registered_custodial_signing_requests", "permit_git_object_archival",
                                                                              "permit_development_partition_seal", "operational_content_access_after_ingestion")},
        "owner_confirmation": {"owner_identity": "OWNER_MUST_SUPPLY", "confirmed": "OWNER_MUST_CHOOSE_BOOLEAN",
                               "confirmation_statement": "OWNER_MUST_SUPPLY_EXPLICIT_STATEMENT"},
    }
    template = {**template_core, "template_identity": seal("B2_DEVELOPMENT_PILOT07_OWNER_DECLARATION_TEMPLATE_V1", template_core)}
    request_core = {
        "schema_name": "batch2-development-pilot07-owner-input-request-v1", "schema_version": "1.0.0",
        "status": "BLOCKED_AWAITING_OWNER_INPUT", "preparation_verdict": "PASS_CONTENT_FREE_METADATA_FIRST_OWNER_PACKAGE_GOVERNANCE_V3",
        "bound_governance_commit": COMMIT, "governance_identity": governance["governance_identity"],
        "conformance_schema_identity": schema["schema_identity"], "remediation_audit_identity": audit["audit_identity"],
        "pilot06_preservation": "IMMUTABLE_NONPOSITIVE_AMBIGUOUS_CONFUSABLE_UNCHANGED",
        "content_accessed": False, "source_family_created": False,
        "owner_files_required": [
            {"filename": "owner-source-pilot07-v1.txt", "encoding": "UTF-8_NO_BOM", "line_endings": "LF_ONLY", "terminal_lf_count": 1,
             "content": "OWNER_AUTHORED_BYTE_EXACT_NEUTRAL_FACTUAL_SOURCE"},
            {"filename": "owner-declaration-pilot07-v1.json", "canonical_requirement": "UTF8_JSON_NO_BOM_LF_ONE_TERMINAL_LF",
             "content": "OWNER_COMPLETED_DECLARATION_FROM_TEMPLATE"}],
        "source_content_requirements": {
            "minimum_independently_bindable_factual_propositions": 2, "must_be_owner_authored": True,
            "must_be_neutral_nonhumorous": True, "must_be_fresh_independent_source_event_topic_and_authority_family": True,
            "must_expose_scope_modality_time_and_known_unknown_boundaries_where_applicable": True,
            "must_not_be_optimized_for_post_g01_sufficiency_assignment_or_obligation": True,
            "prohibited": ["PILOT01_THROUGH_06_WORDING_ENTITY_EVENT_OR_CREATIVE_STRUCTURE_REUSE",
                           "REVISION_SIBLING_SYNDICATION_OR_SAME_EVENT_RELATION_TO_PRIOR_PILOTS",
                           "HUMOR_MECHANISM_OR_OBLIGATION_SHAPED_FRAMING", "GOVERNANCE_OR_INSTRUCTION_STYLE_LANGUAGE",
                           "PERSONAL_PRIVATE_CONFIDENTIAL_SENSITIVE_ALLEGATION_OR_THIRD_PARTY_COPYRIGHTED_CONTENT",
                           "MECHANISM_OBLIGATION_SUFFICIENCY_WITNESS_OR_CREATIVE_PREMISE_METADATA"]},
        "mandatory_phase_order": ["STRICT_PREINGESTION_VALIDATION", "PROSPECTIVE_IDENTITIES_AND_UNSIGNED_SIGNING_PACKET",
                                  "OWNER_OPERATED_CUSTODIAL_SIGNATURES", "ATOMIC_IMMUTABLE_INGESTION", "G01A", "G01B",
                                  "SEPARATELY_AUTHORIZED_PROPOSITION_SUFFICIENCY_GATE", "SEPARATELY_AUTHORIZED_ASSIGNMENT_DESIGN",
                                  "SEPARATELY_AUTHORIZED_G02B", "SEPARATELY_AUTHORIZED_CONSTRUCTION"],
        "post_g01_boundary": {"proposition_evaluation_status": "NOT_PERFORMED", "assignment_status": "NOT_PERFORMED",
                              "earliest_permitted_time": "ONLY_AFTER_G01A_AND_G01B_PASS",
                              "must_not_influence_source_selection_wording_ingestion_or_g01": True},
        "unassigned": {"selected_proposition": "UNASSIGNED", "target_mechanism": "UNASSIGNED",
                       "operational_obligation": "UNASSIGNED", "creative_premise_family_id": "UNASSIGNED"},
        "declaration_template_identity": template["template_identity"],
        "authority_matrix": {key: False for key in ("source_acquisition", "content_ingestion", "archive_write", "custodial_signing", "g01a_admission",
                                                               "g01b_admission", "proposition_sufficiency_evaluation", "target_assignment", "obligation_assignment",
                                                               "constructor_release", "construction", "generation", "g04b_pool_certification", "model_exposure",
                                                               "training", "runtime_integration", "production_routing")},
    }
    request = {**request_core, "owner_input_request_identity": seal("B2_DEVELOPMENT_PILOT07_OWNER_INPUT_REQUEST_V1", request_core)}
    audit_core = {
        "schema_name": "batch2-development-pilot07-owner-input-request-audit-v1", "schema_version": "1.0.0",
        "owner_input_request_identity": request["owner_input_request_identity"], "content_free": True,
        "pilot06_preserved": True, "mechanism_neutral": True, "blind_material_accessed": False,
        "proposition_evaluation_performed": False, "assignment_performed": False,
        "source_selection_uses_downstream_governance_or_target": False, "construction_authority": False,
        "deterministic_blockers": [], "external_input_blocker": "OWNER_AUTHORED_SOURCE_BYTES_AND_COMPLETED_DECLARATION_REQUIRED",
        "audit_verdict": "PASS_CONTENT_FREE_STOP_REQUIRED"}
    request_audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT07_OWNER_INPUT_REQUEST_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot07-owner-declaration-template-v1.json", template)
    write("humor-mechanics-batch2-development-pilot07-owner-input-request-v1.json", request)
    write("humor-mechanics-batch2-development-pilot07-owner-input-request-audit-v1.json", request_audit)
    print(json.dumps({"status": request["status"], "preparation_verdict": request["preparation_verdict"],
                      "owner_input_request_identity": request["owner_input_request_identity"], "template_identity": template["template_identity"],
                      "audit_identity": request_audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
