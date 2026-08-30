"""Freeze the content-free owner intake package for DEVELOPMENT Pilot 02."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
DOC = ROOT / "docs"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def write_json(path: Path, value: dict[str, Any]) -> None:
    if path.exists():
        raise SystemExit(f"already exists: {path}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    template = {
        "schema_name": "batch2-internally-owned-owner-input-v1",
        "schema_version": "1.0.0",
        "pilot_id": "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-02",
        "source": {
            "filename": "owner-source-pilot02-v1.txt", "declared_encoding": "UTF-8", "bom": False,
            "line_endings": "LF", "terminal_lf_count": 1,
            "source_version": "OWNER_MUST_SUPPLY_SEMVER", "capture_timestamp": "OWNER_MUST_SUPPLY_ISO8601_WITH_OFFSET",
            "acquisition_timestamp": "OWNER_MUST_SUPPLY_ISO8601_WITH_OFFSET",
            "acquisition_channel": "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE",
            "intended_partition": "DEVELOPMENT", "subject_class": "OWNER_MUST_SUPPLY",
            "authority_scope": "OWNER_MUST_SUPPLY", "world_scope": "OWNER_MUST_SUPPLY",
        },
        "contributor": {
            "public_identity": "OWNER_MUST_SUPPLY_URN", "legal_identity": "OWNER_MUST_SUPPLY_COMMITTABLE_REFERENCE",
            "legal_identity_verification_reference": "OWNER_MUST_SUPPLY_NONSECRET_REFERENCE", "role": "OWNER_MUST_CHOOSE",
            "rights_holder_identity": "OWNER_MUST_SUPPLY_URN", "rights_holder_relationship": "OWNER_MUST_DECLARE",
            "identity_disclosure_approved_for_commit": "OWNER_MUST_CHOOSE_BOOLEAN",
        },
        "ownership_declarations": {key: "OWNER_MUST_CHOOSE_BOOLEAN" for key in (
            "original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant",
            "contains_undisclosed_third_party_material", "contains_private_or_confidential_information",
            "contains_personal_data", "contains_unlawfully_obtained_information", "contains_unattributed_quotation",
            "contains_reputation_sensitive_allegation")},
        "independent_grants": {key: "OWNER_MUST_CHOOSE_BOOLEAN_INDEPENDENTLY" for key in (
            "immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery",
            "construction_and_evaluation", "model_exposure", "training", "runtime_integration", "production_routing")},
        "rights_terms": {key: "OWNER_MUST_CHOOSE_OR_DECLARE" for key in (
            "territory", "effective_at", "expires_at", "attribution_requirement", "compensation_terms",
            "revocation_terms", "correction_policy", "supersession_policy", "survival_of_completed_uses")},
        "source_status_declarations": {key: "OWNER_MUST_CHOOSE_BOOLEAN" for key in (
            "source_is_neutral_factual_authority", "source_was_not_selected_for_a_humor_mechanism",
            "source_contains_no_mechanism_assignment", "source_contains_no_operational_obligation_assignment",
            "source_contains_no_creative_premise_assignment", "source_contains_no_constructed_humor_candidate",
            "source_has_no_pilot01_revision_sibling_or_same_event_relationship", "known_boundaries_are_explicit",
            "unknown_boundaries_are_explicit")},
        "owner_instruction": {
            "requested_action": "OWNER_MUST_CHOOSE_PREINGESTION_VALIDATION_ONLY",
            "permit_derived_hashes_and_coordinates": "OWNER_MUST_CHOOSE_BOOLEAN",
            "permit_registered_custodial_signing_requests": "OWNER_MUST_CHOOSE_BOOLEAN",
            "permit_git_object_archival": "OWNER_MUST_CHOOSE_BOOLEAN",
            "permit_partition_seal_for_development_only": "OWNER_MUST_CHOOSE_BOOLEAN",
            "operational_content_access_after_ingestion": "OWNER_MUST_CHOOSE_BOOLEAN",
        },
        "owner_confirmation": {"owner_identity": "OWNER_MUST_SUPPLY", "confirmed": "OWNER_MUST_CHOOSE_BOOLEAN", "confirmation_statement": "OWNER_MUST_SUPPLY_EXPLICIT_STATEMENT"},
    }
    template_identity = seal("B2_DEVELOPMENT_PILOT02_OWNER_DECLARATION_TEMPLATE_V1", template)
    request_core = {
        "schema_name": "batch2-development-pilot02-owner-input-request-v1", "schema_version": "1.0.0",
        "status": "BLOCKED_AWAITING_OWNER_INPUT", "content_accessed": False, "source_family_created": False,
        "successor_governance": {"commit": "a444ace2e6eb8bfad006374f266c90269c665565", "obligation_governance_identity": "0cfd22fd43e0be68b5a04f16e45e918ac7bae346c851334817a7af309bad63e5", "conformance_schema_identity": "11bb3e5bc2e6a3b3830c0f751539b5688693f37702d7e13943112a768966e44a", "pilot01_regression_identity": "627aabc7a40bca73f06f4a357ffcf52b267d5d10a51bb68de1ca6601840369cb", "leakage_audit_identity": "3f4bd4c64b447340b0ab7af45af8b227740156f78eb1b9033a2a5c2cd9d2f693"},
        "owner_files_required": [
            {"filename": "owner-source-pilot02-v1.txt", "content": "OWNER_AUTHORED_BYTE_EXACT_SOURCE", "encoding": "UTF-8_NO_BOM", "line_endings": "LF_ONLY", "terminal_lf_count": 1},
            {"filename": "owner-declaration-pilot02-v1.json", "content": "OWNER_COMPLETED_DECLARATION_FROM_TEMPLATE", "canonical_requirement": "UTF8_JSON_NO_BOM_LF_ONE_TERMINAL_LF"},
        ],
        "source_content_requirements": {
            "minimum_independently_bindable_factual_propositions": 2,
            "must_be_owner_authored": True, "must_be_neutral_nonhumorous": True,
            "must_expose_scope_modality_time_and_known_unknown_boundaries_where_applicable": True,
            "prohibited": ["PILOT01_WORDING_ENTITY_EVENT_OR_STRUCTURE_REUSE", "HUMOR_OR_PUNCHLINE", "RHETORICAL_QUESTION", "PARODY", "METAPHOR_HEAVY_OR_ANTHROPOMORPHIC_FRAMING", "PRIVATE_PERSON_OR_PERSONAL_DATA", "PROTECTED_OR_VULNERABLE_TARGET", "ALLEGATION_OR_WRONGDOING", "PRIVATE_OR_CONFIDENTIAL_KNOWLEDGE", "SENSITIVE_ADVICE", "THIRD_PARTY_COPYRIGHTED_SURFACE", "MECHANISM_OR_OBLIGATION_METADATA"],
            "selection_must_not_use": ["SUCCESSOR_OBLIGATION", "TARGET_MECHANISM", "BATCH2_GAP", "TARGET_FRIENDLY_TOPIC_GRAMMAR_TOPOLOGY_OR_SHAPE"],
        },
        "freshness_checks_after_submission": ["SOURCE_SHA_AND_GIT_BLOB_NOT_PILOT01", "NO_SOURCE_EVENT_AUTHORITY_TOPIC_REVISION_SYNDICATION_OR_SAME_EVENT_FAMILY_RELATION_TO_PILOT01", "NO_PRIOR_TARGET_OR_OBLIGATION_ASSIGNMENT", "NO_PRIOR_CONSTRUCTION_OR_MODEL_EXPOSURE", "NO_BLIND_FAMILY_ACCESS", "CONTAMINATION_LEDGER_COMPLETE"],
        "prospective_gate_path": ["OWNER_SUBMISSION", "STRICT_PREINGESTION_VALIDATION", "G01A_RIGHTS_PROVENANCE_AUTHORITY", "CUSTODIAL_SIGNATURES_SEPARATELY_AUTHORIZED", "ATOMIC_IMMUTABLE_INGESTION_SEPARATELY_AUTHORIZED", "G01B_FAMILY_PARTITION_ADMISSION", "DEVELOPMENT_SEAL"],
        "identity_timing": {"source_commitment": "AFTER_EXACT_BYTES", "rights_identity": "AFTER_COMPLETED_DECLARATION", "authority_envelope": "AFTER_PROPOSITION_BINDING", "family_closure": "AFTER_DUPLICATE_REVISION_SAME_EVENT_AUDIT", "partition_identity": "AFTER_G01B_AND_AUTHORIZED_CUSTODIAL_SEAL"},
        "unassigned": {"target_mechanism": True, "operational_obligation": True, "creative_premise_family_id": "UNASSIGNED"},
        "content_free_exposure_record": {"operation": "PILOT02_OWNER_INPUT_TEMPLATE_PREPARATION", "source_or_family_identity": "NOT_YET_EXISTS", "blind_material_accessed": False, "candidate_or_source_surface_accessed": False, "mechanism_reasoning_performed": False},
        "declaration_template_identity": template_identity,
        "authority_matrix": {key: False for key in ("source_acquisition", "content_ingestion", "archive_write", "custodial_signing", "g01a_admission", "g01b_admission", "family_seal", "target_assignment", "obligation_assignment", "creative_premise_assignment", "construction", "generation", "g02", "g02c", "g03", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    request = {**request_core, "owner_input_request_identity": seal("B2_DEVELOPMENT_PILOT02_OWNER_INPUT_REQUEST_V1", request_core)}
    audit_core = {
        "schema_name": "batch2-development-pilot02-owner-input-request-audit-v1", "schema_version": "1.0.0",
        "owner_input_request_identity": request["owner_input_request_identity"], "declaration_template_identity": template_identity,
        "verdict": "PASS_CONTENT_FREE_STOP_REQUIRED",
        "checks": {"owner_authority_not_fabricated": True, "source_content_not_authored_or_selected": True, "successor_obligation_not_used_for_source_selection": True, "pilot01_not_reused": True, "no_family_identity_before_bytes": True, "no_g01_verdict_before_validation": True, "rights_grants_owner_selected_independently": True, "no_blind_access": True, "all_operational_authorities_false": True},
        "blocker": "OWNER_AUTHORED_SOURCE_BYTES_AND_COMPLETED_DECLARATION_REQUIRED",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT02_OWNER_INPUT_REQUEST_AUDIT_V1", audit_core)}
    write_json(ART / "humor-mechanics-batch2-development-pilot02-owner-declaration-template-v1.json", {**template, "template_identity": template_identity})
    write_json(ART / "humor-mechanics-batch2-development-pilot02-owner-input-request-v1.json", request)
    write_json(ART / "humor-mechanics-batch2-development-pilot02-owner-input-request-audit-v1.json", audit)
    print(json.dumps({"verdict": request["status"], "request_identity": request["owner_input_request_identity"], "template_identity": template_identity, "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
