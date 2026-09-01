"""Strictly validate Pilot 10 owner inputs without deriving or ingesting objects."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot10-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot10-v1.json"
REQUEST_COMMIT = "a495969eef8c9f5e5b37dae81c9c29eda83e68c8"
SOURCE_SHA256 = "454a0c568c12a46224407f6c3b378f8197e3f4653cca6d897d1c03b8d94821d7"
DECLARATION_SHA256 = "4bc43e0b03964d50685fe2e5193fafcbfee2c14cd35ebe777fdba64c15540435"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate key: {key}")
        result[key] = value
    return result


def exact_shape(actual: Any, template: Any, path: str = "$") -> None:
    if isinstance(template, dict):
        require(isinstance(actual, dict) and set(actual) == set(template), f"{path} field set")
        for key in template:
            exact_shape(actual[key], template[key], f"{path}.{key}")


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{REQUEST_COMMIT}:{path}"], cwd=ROOT)


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == REQUEST_COMMIT, "HEAD differs from owner-input request commit")
    source_bytes = SOURCE.read_bytes()
    declaration_bytes = DECLARATION.read_bytes()
    require(hashlib.sha256(source_bytes).hexdigest() == SOURCE_SHA256, "source hash")
    require(hashlib.sha256(declaration_bytes).hexdigest() == DECLARATION_SHA256, "declaration hash")
    for name, data in (("source", source_bytes), ("declaration", declaration_bytes)):
        require(not data.startswith(b"\xef\xbb\xbf"), f"{name} BOM")
        require(b"\r" not in data, f"{name} line endings")
        data.decode("utf-8")
        require(data.endswith(b"\n") and not data.endswith(b"\n\n"), f"{name} terminal LF")

    declaration = json.loads(declaration_bytes, object_pairs_hook=unique_object)
    template = json.loads(git_bytes("docs/artifacts/humor-mechanics-batch2-development-pilot10-owner-declaration-template-v1.json"))
    template.pop("template_identity")
    exact_shape(declaration, template)
    require(declaration["schema_name"] == "batch2-internally-owned-owner-input-pilot10-v1", "schema")
    require(declaration["schema_version"] == "1.0.0", "schema version")
    require(declaration["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-10", "pilot")

    source_meta = declaration["source"]
    require(source_meta["filename"] == SOURCE.name, "source filename")
    require(source_meta["declared_encoding"] == "UTF-8" and source_meta["bom"] is False, "encoding")
    require(source_meta["line_endings"] == "LF" and source_meta["terminal_lf_count"] == 1, "format")
    require(source_meta["source_version"] == "1.0.0", "version")
    require(source_meta["acquisition_channel"] == "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE", "channel")
    require(source_meta["intended_partition"] == "DEVELOPMENT", "partition")
    require(source_meta["world_scope"] == source_meta["subject_class"] == "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE", "scope")
    capture = datetime.fromisoformat(source_meta["capture_timestamp"])
    acquisition = datetime.fromisoformat(source_meta["acquisition_timestamp"])
    effective = datetime.fromisoformat(declaration["rights_terms"]["effective_at"])
    require(all(value.tzinfo is not None for value in (capture, acquisition, effective)), "timezone")
    require(capture <= acquisition <= effective, "timestamp order")

    ownership = declaration["ownership_declarations"]
    require(all(ownership[key] is True for key in (
        "original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant",
    )), "ownership")
    require(all(ownership[key] is False for key in (
        "contains_undisclosed_third_party_material", "contains_private_or_confidential_information",
        "contains_personal_data", "contains_unlawfully_obtained_information", "contains_unattributed_quotation",
        "contains_reputation_sensitive_allegation",
    )), "excluded material")
    grants = declaration["independent_grants"]
    require(all(grants[key] is True for key in (
        "immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation",
    )), "required grants")
    require(all(grants[key] is False for key in (
        "model_exposure", "training", "runtime_integration", "production_routing",
    )), "strict noninheritance")
    terms = declaration["rights_terms"]
    require(terms["territory"] == "WORLDWIDE" and terms["expires_at"] == "NO_EXPIRY", "territory expiry")
    require(terms["attribution_requirement"] == "INTERNAL_PROVENANCE_ONLY", "attribution")
    require(terms["compensation_terms"] == "NO_COMPENSATION", "compensation")
    require(terms["correction_policy"] == "NEW_IMMUTABLE_REVISION_ONLY", "correction")
    require(terms["supersession_policy"] == "EXPLICIT_PREDECESSOR_SUCCESSOR_CHAIN", "supersession")
    require(terms["revocation_terms"] == "PROSPECTIVE_REVOCATION;COMPLETED_USES_RECORDED;NO_NEW_USE_AFTER_EFFECTIVE_REVOCATION", "revocation")
    require(terms["survival_of_completed_uses"] == "COMPLETED_IMMUTABLE_AUDIT_RECORDS_SURVIVE", "survival")
    require(all(value is True for value in declaration["source_status_declarations"].values()), "source declarations")
    instruction = declaration["owner_instruction"]
    require(instruction["request_preingestion_validation_only"] is True, "validation-only")
    require(instruction["operational_content_access_after_ingestion"] is False, "operational access")
    require(all(instruction[key] is True for key in (
        "permit_derived_hashes_and_coordinates", "permit_registered_custodial_signing_requests",
        "permit_git_object_archival", "permit_development_partition_seal",
    )), "future permissions")
    contributor = declaration["contributor"]
    require(contributor["identity_disclosure_approved_for_commit"] is False, "identity disclosure")
    require(contributor["legal_identity_commitment"].startswith("urn:pastila:party:"), "identity commitment")
    require(contributor["legal_identity_verification_reference"].startswith("owner-record:"), "identity reference")
    require(contributor["rights_holder_relationship"] == "ORIGINAL_AUTHOR_AND_RIGHTS_HOLDER", "rights holder relationship")
    require(declaration["owner_confirmation"]["confirmed"] is True, "confirmation")

    source_text = source_bytes.decode("utf-8")
    folded = source_text.casefold()
    paragraphs = [part for part in source_text.strip().split("\n\n") if part]
    sentences = [part for part in re.split(r"(?<=[.!?])\s+", source_text.strip()) if part]
    require(len(paragraphs) == 4 and len(sentences) == 7, "statement candidates")
    require(not any(token in folded for token in (
        "?", "!", "glum", "poant", "metafor", "parodi", "mecanism", "obliga", "pilot", "instruc", "guvernan", "absurd", "witness",
    )), "neutrality")
    require("21 septembrie 2026" in source_text and "30 de lăzi cu substrat pentru plante tropicale" in source_text, "event quantity material")
    require("fiecare ladă este cântărită" in source_text and "comparat cu numărul din documentul de livrare" in source_text, "verification procedure")
    require("eticheta APROBAT" in source_text and "zona de depozitare destinată materialelor horticole" in source_text, "approval disposition")
    require("eticheta RESPINS" in source_text and "rămâne în zona de recepție" in source_text, "rejection disposition")
    require("numărul lăzii și tipul diferenței observate" in source_text, "discrepancy record")
    require("numai la această livrare" in source_text and "nu stabilește starea altor materiale" in source_text, "scope boundary")
    require("nu este cunoscut dacă vor exista neconcordanțe" in source_text and "vor necesita verificări suplimentare" in source_text, "unknown boundary")
    authority_scope = source_meta["authority_scope"].casefold()
    require(all(token in authority_scope for token in ("delivery-reception", "quantity", "approval", "rejection", "discrepancy", "unknown")), "authority scope consistency")

    prior_paths = [
        f"docs/artifacts/humor-mechanics-batch2-development-pilot{index:02d}-ingestion-v1/source.utf8.txt"
        for index in range(1, 10)
    ]
    prior_sources = [git_bytes(path) for path in prior_paths]
    require(source_bytes not in prior_sources, "prior source equality")
    current_lines = {line for line in source_text.splitlines() if line}
    prior_lines = {line for prior in prior_sources for line in prior.decode("utf-8").splitlines() if line}
    require(not current_lines.intersection(prior_lines), "prior exact line reuse")

    core = {
        "schema_name": "batch2-development-pilot10-strict-preingestion-validation-v1",
        "schema_version": "1.0.0",
        "owner_input_request_commit": REQUEST_COMMIT,
        "owner_input_request_identity": "0fadef1e02839a570cd61ed128d26114d7ff5042f0dbfa309844a988adc23336",
        "declaration_template_identity": "46209c6c15733e17bd15e92e2088b914df6883d6bdc0d31c88bfa204795e5ae5",
        "governance_identity": "80bbf059956424ce6f20885de51ce900f6116b40a223a107a46a29d3b012efc6",
        "constructor_implementation_identity": "bdf48e9942f097f0259831c0f2f611e50644cdbe7179a2dc7d990bf9ab2b5493",
        "source_sha256": SOURCE_SHA256,
        "source_byte_length": len(source_bytes),
        "declaration_sha256": DECLARATION_SHA256,
        "declaration_byte_length": len(declaration_bytes),
        "checks": {
            "hashes": "PASS",
            "utf8_no_bom_lf_only_exact_terminal_lf": "PASS",
            "exact_schema_shape": "PASS",
            "owner_rights_and_independent_grants": "PASS",
            "downstream_grants_false": "PASS_STRICT_NONINHERITANCE",
            "private_legal_identity_not_disclosed": "PASS_COMMITTABLE_REFERENCE_ONLY",
            "neutral_owner_authored_synthetic_source": "PASS",
            "seven_independently_bindable_statement_candidates": "PASS_NOT_YET_BOUND",
            "scope_time_condition_and_unknown_boundaries": "PASS",
            "pilot01_through_09_exact_source_and_line_independence": "PASS",
            "transitive_family_independence": "OWNER_ATTESTED_PENDING_LATER_FAMILY_DERIVATION",
            "mechanism_pool_target_proposition_result_assignment_obligation_constructor_compatibility_realization_plan_witness_topology_creative_marker_and_expected_outcome_unassigned": "PASS",
        },
        "deterministic_blockers": [],
        "repair_performed": False,
        "repair_reason": "NOT_APPLICABLE_INPUTS_VALIDATED_BYTE_EXACT",
        "proposition_sufficiency_evaluated": False,
        "prospective_identities_derived": False,
        "proposition_envelope_created": False,
        "family_identities_derived": False,
        "signing_requested_or_packet_created": False,
        "ingestion_or_archive_write_performed": False,
        "g01_admission_performed": False,
        "assignment_performed": False,
        "constructor_source_compatibility_release_or_invocation_performed": False,
        "realization_candidate_emission_or_preemission_conformance_performed": False,
        "fragment_collision_evaluation_performed": False,
        "g02_g02c_g03_or_g04b_performed": False,
        "validation_verdict": "PASS_STRICT_PREINGESTION_VALIDATION_ONLY",
        "authority_matrix": {key: False for key in (
            "proposition_sufficiency_evaluation", "prospective_signing_preparation", "signing", "ingestion",
            "archive_write", "g01a", "g01b", "assignment", "constructor_source_compatibility_evaluation",
            "constructor_release", "constructor_invocation", "realization", "candidate_emission",
            "post_realization_pre_emission_conformance", "fragment_collision_evaluation", "g02", "g02c", "g03",
            "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing",
        )},
    }
    artifact = {**core, "validation_identity": seal("B2_DEVELOPMENT_PILOT10_STRICT_PREINGESTION_VALIDATION_V1", core)}
    output = ART / "humor-mechanics-batch2-development-pilot10-strict-preingestion-validation-v1.json"
    require(not output.exists(), "validation artifact exists")
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"validation_verdict": artifact["validation_verdict"], "validation_identity": artifact["validation_identity"],
                      "deterministic_blockers": artifact["deterministic_blockers"]}, sort_keys=True))


if __name__ == "__main__":
    main()
