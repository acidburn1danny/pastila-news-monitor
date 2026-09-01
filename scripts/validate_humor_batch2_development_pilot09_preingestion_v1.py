"""Strictly validate Pilot 09 owner inputs without deriving or ingesting objects."""

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
SOURCE = ROOT / "owner-source-pilot09-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot09-v1.json"
REQUEST_COMMIT = "947e4710c34e6b13d57e5b23bc49489de8b208c7"
SOURCE_SHA256 = "608f26b4588c347707ae5eccb08194d498fb3b3e9e7a6402be63ad2bc7c77c77"
DECLARATION_SHA256 = "8c68d5bf2a711fc518879fcddfba9ea44d7c232fb962fdecc816bf97d249b41b"


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
    template = json.loads(git_bytes("docs/artifacts/humor-mechanics-batch2-development-pilot09-owner-declaration-template-v1.json"))
    template.pop("template_identity")
    exact_shape(declaration, template)
    require(declaration["schema_name"] == "batch2-internally-owned-owner-input-pilot09-v1", "schema")
    require(declaration["schema_version"] == "1.0.0", "schema version")
    require(declaration["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-09", "pilot")

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
    require(declaration["owner_confirmation"]["confirmed"] is True, "confirmation")

    source_text = source_bytes.decode("utf-8")
    folded = source_text.casefold()
    paragraphs = [part for part in source_text.strip().split("\n\n") if part]
    sentences = [part for part in re.split(r"(?<=[.!?])\s+", source_text.strip()) if part]
    require(len(paragraphs) == 4 and len(sentences) == 8, "statement candidates")
    require(not any(token in folded for token in (
        "?", "!", "glum", "poant", "metafor", "parodi", "mecanism", "obliga", "pilot", "instruc", "guvernan", "absurd",
    )), "neutrality")
    require("18 septembrie 2026" in source_text and "înainte de începerea programului" in source_text, "time scope")
    require("un senzor detectează prezența coletului" in source_text and "transmite un semnal către unitatea de control" in source_text, "sensor relation")
    require("unitatea de control comandă pornirea benzii" in source_text, "control relation")
    require("Dacă senzorul nu detectează coletul" in source_text and "banda nu pornește automat" in source_text, "conditional boundary")
    require("consemnează separat răspunsul senzorului" in source_text, "recording scope")
    require("nu stabilește starea celorlalte echipamente" in source_text, "equipment boundary")
    require("nu este cunoscut dacă sistemul va funcționa fără abatere" in source_text, "unknown operation")
    require("nici dacă va fi necesară o intervenție tehnică" in source_text, "unknown intervention")

    prior_paths = [
        f"docs/artifacts/humor-mechanics-batch2-development-pilot{index:02d}-ingestion-v1/source.utf8.txt"
        for index in range(1, 9)
    ]
    prior_sources = [git_bytes(path) for path in prior_paths]
    require(source_bytes not in prior_sources, "prior source equality")
    current_lines = {line for line in source_text.splitlines() if line}
    prior_lines = {line for prior in prior_sources for line in prior.decode("utf-8").splitlines() if line}
    require(not current_lines.intersection(prior_lines), "prior exact line reuse")

    core = {
        "schema_name": "batch2-development-pilot09-strict-preingestion-validation-v1",
        "schema_version": "1.0.0",
        "owner_input_request_commit": REQUEST_COMMIT,
        "owner_input_request_identity": "868318c6a152e72ddd594d779db8257bb81f0b00d6513839abb0a710b0b1e1cc",
        "governance_identity": "e81ee4eff9044ee16180ef36a7508fe9f1e7c784fa6830299588cea16c2d3a3e",
        "constructor_implementation_identity": "caf85ada6fcd296d3798b5d47838d7b8a39d029dac5f6ecae68ace58712b9d61",
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
            "eight_independently_bindable_statement_candidates": "PASS_NOT_YET_BOUND",
            "scope_time_condition_and_unknown_boundaries": "PASS",
            "pilot01_through_08_exact_source_and_line_independence": "PASS",
            "transitive_family_independence": "OWNER_ATTESTED_PENDING_LATER_FAMILY_DERIVATION",
            "mechanism_obligation_selected_proposition_constructor_compatibility_and_creative_lineage_unassigned": "PASS",
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
        "constructor_source_compatibility_or_release_performed": False,
        "fragment_collision_evaluation_performed": False,
        "g04b_pool_certification_performed": False,
        "validation_verdict": "PASS_STRICT_PREINGESTION_VALIDATION_ONLY",
        "authority_matrix": {key: False for key in (
            "proposition_sufficiency_evaluation", "prospective_signing_preparation", "signing", "ingestion",
            "archive_write", "g01a", "g01b", "assignment", "constructor_source_compatibility_evaluation",
            "constructor_release", "construction", "fragment_collision_evaluation", "g04b_pool_certification",
            "model_exposure", "training", "runtime_integration", "production_routing",
        )},
    }
    artifact = {**core, "validation_identity": seal("B2_DEVELOPMENT_PILOT09_STRICT_PREINGESTION_VALIDATION_V1", core)}
    output = ART / "humor-mechanics-batch2-development-pilot09-strict-preingestion-validation-v1.json"
    require(not output.exists(), "validation artifact exists")
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "validation_verdict": artifact["validation_verdict"],
        "validation_identity": artifact["validation_identity"],
        "deterministic_blockers": artifact["deterministic_blockers"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
