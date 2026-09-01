"""Strictly validate Pilot 12 owner inputs without deriving or ingesting objects."""

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
SOURCE = ROOT / "owner-source-pilot12-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot12-v1.json"
REQUEST_COMMIT = "4c06f4fc72b6df26949450c9bbc4b638c1064c48"
SOURCE_SHA256 = "8b87cef6b320d45d7594bc48919bae63442f51f1f7937b599575d435df69ea27"
DECLARATION_SHA256 = "94f573e8aa1bb1789117ebef856da896447ddcfd944f195e17267e7bdf456ab3"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
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
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == REQUEST_COMMIT, "HEAD")
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    require(hashlib.sha256(source_bytes).hexdigest() == SOURCE_SHA256, "source hash")
    require(hashlib.sha256(declaration_bytes).hexdigest() == DECLARATION_SHA256, "declaration hash")
    for name, data in (("source", source_bytes), ("declaration", declaration_bytes)):
        require(not data.startswith(b"\xef\xbb\xbf"), f"{name} BOM")
        require(b"\r" not in data, f"{name} line endings")
        data.decode("utf-8")
        require(data.endswith(b"\n") and not data.endswith(b"\n\n"), f"{name} terminal LF")

    declaration = json.loads(declaration_bytes, object_pairs_hook=unique_object)
    template = json.loads(git_bytes("docs/artifacts/humor-mechanics-batch2-development-pilot12-owner-declaration-template-v1.json"))
    template.pop("template_identity")
    exact_shape(declaration, template)
    require(declaration["schema_name"] == "batch2-internally-owned-owner-input-pilot12-v1", "schema")
    require(declaration["schema_version"] == "1.0.0" and declaration["pilot_id"].endswith("PILOT-12"), "version/pilot")
    metadata = declaration["source"]
    require(metadata["filename"] == SOURCE.name and metadata["declared_encoding"] == "UTF-8" and metadata["bom"] is False, "source format")
    require(metadata["line_endings"] == "LF" and metadata["terminal_lf_count"] == 1, "line format")
    require(metadata["source_version"] == "1.0.0" and metadata["intended_partition"] == "DEVELOPMENT", "version/partition")
    require(metadata["acquisition_channel"] == "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE", "channel")
    require(metadata["world_scope"] == metadata["subject_class"] == "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE", "scope")
    times = [datetime.fromisoformat(metadata[key]) for key in ("capture_timestamp", "acquisition_timestamp")]
    effective = datetime.fromisoformat(declaration["rights_terms"]["effective_at"])
    require(all(item.tzinfo is not None for item in (*times, effective)) and times[0] <= times[1] <= effective, "timestamps")
    ownership = declaration["ownership_declarations"]
    require(all(ownership[key] is True for key in ("original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant")), "ownership")
    require(all(ownership[key] is False for key in ("contains_undisclosed_third_party_material", "contains_private_or_confidential_information",
        "contains_personal_data", "contains_unlawfully_obtained_information", "contains_unattributed_quotation",
        "contains_reputation_sensitive_allegation")), "excluded material")
    grants = declaration["independent_grants"]
    require(all(grants[key] is True for key in ("immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation")), "required grants")
    require(all(grants[key] is False for key in ("model_exposure", "training", "runtime_integration", "production_routing")), "strict noninheritance")
    terms = declaration["rights_terms"]
    require(terms == {"territory": "WORLDWIDE", "effective_at": terms["effective_at"], "expires_at": "NO_EXPIRY",
        "attribution_requirement": "INTERNAL_PROVENANCE_ONLY", "compensation_terms": "NO_COMPENSATION",
        "revocation_terms": "PROSPECTIVE_REVOCATION;COMPLETED_USES_RECORDED;NO_NEW_USE_AFTER_EFFECTIVE_REVOCATION",
        "correction_policy": "NEW_IMMUTABLE_REVISION_ONLY", "supersession_policy": "EXPLICIT_PREDECESSOR_SUCCESSOR_CHAIN",
        "survival_of_completed_uses": "COMPLETED_IMMUTABLE_AUDIT_RECORDS_SURVIVE"}, "rights terms")
    require(all(value is True for value in declaration["source_status_declarations"].values()), "source declarations")
    instruction = declaration["owner_instruction"]
    require(instruction["request_preingestion_validation_only"] is True and instruction["operational_content_access_after_ingestion"] is False, "instruction")
    require(all(instruction[key] is True for key in ("permit_derived_hashes_and_coordinates", "permit_registered_custodial_signing_requests",
        "permit_git_object_archival", "permit_development_partition_seal")), "future permissions")
    contributor = declaration["contributor"]
    require(contributor["identity_disclosure_approved_for_commit"] is False, "identity disclosure")
    require(contributor["legal_identity_commitment"].startswith("urn:pastila:party:") and contributor["legal_identity_verification_reference"].startswith("owner-record:"), "identity")
    require(contributor["rights_holder_relationship"] == "ORIGINAL_AUTHOR_AND_RIGHTS_HOLDER", "rights relation")
    require(declaration["owner_confirmation"]["confirmed"] is True, "confirmation")

    source = source_bytes.decode("utf-8")
    folded = source.casefold()
    paragraphs = [part for part in source.strip().split("\n\n") if part]
    sentences = [part for part in re.split(r"(?<=[.!?])\s+", source.strip()) if part]
    require(len(paragraphs) == 4 and len(sentences) == 8, "eight bindable statement candidates")
    prohibited = ("?", "!", "glum", "poant", "metafor", "parodi", "mecanism", "obliga", "pilot", "instruc",
                  "guvernan", "absurd", "witness", "affordance", "aliniere", "template", "constructor")
    require(not any(token in folded for token in prohibited), "neutrality and shaping")
    required_facts = ("25 septembrie 2026", "60 de volume", "sală de lectură temporară", "cod de inventar",
        "lista de transfer", "raft de destinație", "cutie marcată", "numărul raftului", "toate volumele",
        "același raft de destinație", "depozitul bibliotecii", "rafturi diferite", "pentru reverificare",
        "numai la cele 60 de volume", "nu modifică poziția celorlalte cărți", "nu este cunoscut",
        "nici dacă va fi necesară reverificarea")
    require(all(fact in source for fact in required_facts), "factual scope and known/unknown boundaries")
    authority_scope = metadata["authority_scope"].casefold()
    require(all(token in authority_scope for token in ("university-library", "quantity", "inventory-code", "destination-shelf",
        "transport condition", "reverification condition", "scope limitation", "unknown")), "authority scope")
    prior_sources = [git_bytes(f"docs/artifacts/humor-mechanics-batch2-development-pilot{i:02d}-ingestion-v1/source.utf8.txt") for i in range(1, 12)]
    require(source_bytes not in prior_sources, "prior source equality")
    current_lines = {line for line in source.splitlines() if line}
    prior_lines = {line for raw in prior_sources for line in raw.decode("utf-8").splitlines() if line}
    require(not current_lines.intersection(prior_lines), "prior exact line reuse")

    request = json.loads(git_bytes("docs/artifacts/humor-mechanics-batch2-development-pilot12-owner-input-request-v1.json"))
    require(request["owner_input_request_identity"] == "f9506e7827ce5aa2d5b5386727086511a6dbe69af616731c0899edb64a77c809", "request")
    require(request["declaration_template_identity"] == "508ff3b1137c2121d6b2058d45c6f471b04c0a97c3505450d264de216aa3a014", "template")
    core = {
        "schema_name": "batch2-development-pilot12-strict-preingestion-validation-v1", "schema_version": "1.0.0",
        "owner_input_request_commit": REQUEST_COMMIT, "owner_input_request_identity": request["owner_input_request_identity"],
        "declaration_template_identity": request["declaration_template_identity"],
        "base_governance_identity": request["base_governance_identity"],
        "v5_3_1_alignment_contract_identity": request["v5_3_1_alignment_contract_identity"],
        "constructor_implementation_identity": request["constructor_implementation_identity"],
        "source_sha256": SOURCE_SHA256, "source_byte_length": len(source_bytes),
        "declaration_sha256": DECLARATION_SHA256, "declaration_byte_length": len(declaration_bytes),
        "checks": {"hashes": "PASS", "utf8_no_bom_lf_only_exact_terminal_lf": "PASS", "exact_schema_shape": "PASS",
            "owner_rights_and_independent_grants": "PASS", "downstream_grants_false": "PASS_STRICT_NONINHERITANCE",
            "neutral_owner_authored_synthetic_source": "PASS", "eight_independently_bindable_statement_candidates": "PASS_NOT_YET_BOUND",
            "scope_time_condition_and_known_unknown_boundaries": "PASS", "pilot01_through_11_exact_source_and_line_independence": "PASS",
            "transitive_family_independence": "OWNER_ATTESTED_PENDING_LATER_FAMILY_DERIVATION",
            "mechanism_pool_proposition_assignment_constructor_semantic_role_affordance_realization_witness_alignment_template_marker_and_outcome_shaping": "PASS_ABSENT"},
        "deterministic_blockers": [], "repair_performed": False,
        "repair_reason": "NOT_APPLICABLE_INPUTS_VALIDATED_BYTE_EXACT", "prospective_identities_derived": False,
        "proposition_sufficiency_evaluated": False, "signing_requested_or_packet_created": False,
        "ingestion_or_archive_write_performed": False, "g01_admission_performed": False, "assignment_performed": False,
        "constructor_compatibility_semantic_plan_release_or_invocation_performed": False,
        "realization_candidate_emission_coordinate_conformance_or_semantic_edge_validation_performed": False,
        "fragment_collision_g02_g02c_g03_or_g04b_performed": False,
        "validation_verdict": "PASS_STRICT_PREINGESTION_VALIDATION_ONLY",
        "authority_matrix": {key: False for key in ("prospective_identity_derivation", "proposition_sufficiency_evaluation",
            "signing", "ingestion", "archive_write", "g01a", "g01b", "assignment", "constructor_source_compatibility_evaluation",
            "semantic_plan_evaluation", "constructor_release", "constructor_invocation", "realization", "candidate_emission",
            "coordinate_bound_semantic_conformance", "semantic_edge_validation", "fragment_collision_evaluation", "g02", "g02c",
            "g03", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    artifact = {**core, "validation_identity": seal("B2_DEVELOPMENT_PILOT12_STRICT_PREINGESTION_VALIDATION_V1", core)}
    output = ART / "humor-mechanics-batch2-development-pilot12-strict-preingestion-validation-v1.json"
    require(not output.exists(), "artifact exists")
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"validation_verdict": artifact["validation_verdict"], "validation_identity": artifact["validation_identity"],
                      "deterministic_blockers": artifact["deterministic_blockers"], "repair_performed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
