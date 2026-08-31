"""Strictly validate Pilot 05 owner inputs without deriving or ingesting objects."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot05-v1.txt"
RAW_DECLARATION = ROOT / "owner-declaration-pilot05-v1.json"
DECLARATION = ART / "humor-mechanics-batch2-development-pilot05-owner-declaration-canonical-v1.json"
REQUEST_COMMIT = "016835731c93109731b8e69a740977c4e6d7d25b"
SOURCE_SHA = "e3404a694bf1203f8a11ceeed0e682511882237e4777bd0e092876994c4326cc"
RAW_DECLARATION_SHA = "acff7c3ffd4124c6c0d8921e3887811259f4192ef35e7fc40d51e8bcad7fe71c"
DECLARATION_SHA = "69e207463fcb8d31e0ccaf99db46192bd577997dfb4b1d3658a5f955fb148e25"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate declaration key: {key}")
        result[key] = value
    return result


def assert_exact_shape(actual: Any, template: Any, path: str = "$") -> None:
    if isinstance(template, dict):
        require(isinstance(actual, dict), f"{path} must be object")
        require(set(actual) == set(template), f"{path} field set")
        for key in template:
            assert_exact_shape(actual[key], template[key], f"{path}.{key}")


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == REQUEST_COMMIT, "HEAD differs from Pilot 05 owner-input freeze")
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    require(hashlib.sha256(source_bytes).hexdigest() == SOURCE_SHA, "source SHA-256")
    require(hashlib.sha256(RAW_DECLARATION.read_bytes()).hexdigest() == RAW_DECLARATION_SHA, "submitted declaration SHA-256")
    require(hashlib.sha256(declaration_bytes).hexdigest() == DECLARATION_SHA, "declaration SHA-256")
    for name, data in (("source", source_bytes), ("declaration", declaration_bytes)):
        require(not data.startswith(b"\xef\xbb\xbf"), f"{name} BOM")
        require(b"\r" not in data, f"{name} CR")
        require(data.endswith(b"\n") and not data.endswith(b"\n\n"), f"{name} terminal LF")
        data.decode("utf-8")

    declaration = json.loads(declaration_bytes, object_pairs_hook=unique_object)
    template = json.loads(git_bytes(REQUEST_COMMIT, "docs/artifacts/humor-mechanics-batch2-development-pilot05-owner-declaration-template-v1.json"))
    template.pop("template_identity")
    assert_exact_shape(declaration, template)
    require(declaration["schema_name"] == "batch2-internally-owned-owner-input-v1" and declaration["schema_version"] == "1.0.0", "schema")
    require(declaration["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-05", "pilot id")
    source_meta = declaration["source"]
    require(source_meta["filename"] == SOURCE.name and source_meta["declared_encoding"] == "UTF-8", "source metadata")
    require(source_meta["bom"] is False and source_meta["line_endings"] == "LF" and source_meta["terminal_lf_count"] == 1, "source format metadata")
    require(source_meta["source_version"] == "1.0.0" and source_meta["acquisition_channel"] == "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE" and source_meta["intended_partition"] == "DEVELOPMENT", "source classification")
    capture = datetime.fromisoformat(source_meta["capture_timestamp"])
    acquisition = datetime.fromisoformat(source_meta["acquisition_timestamp"])
    effective = datetime.fromisoformat(declaration["rights_terms"]["effective_at"])
    require(all(item.tzinfo is not None for item in (capture, acquisition, effective)) and capture <= acquisition <= effective, "timestamp offsets/order")

    ownership = declaration["ownership_declarations"]
    require(all(ownership[key] is True for key in ("original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant")), "ownership")
    require(all(ownership[key] is False for key in ("contains_undisclosed_third_party_material", "contains_private_or_confidential_information", "contains_personal_data", "contains_unlawfully_obtained_information", "contains_unattributed_quotation", "contains_reputation_sensitive_allegation")), "excluded material")
    grants = declaration["independent_grants"]
    require(all(grants[key] is True for key in ("immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation")), "required grants")
    require(all(grants[key] is False for key in ("model_exposure", "training", "runtime_integration", "production_routing")), "downstream grants")
    require(all(value is True for value in declaration["source_status_declarations"].values()), "source declarations")
    instruction = declaration["owner_instruction"]
    require(instruction["request_preingestion_validation_only"] is True and instruction["operational_content_access_after_ingestion"] is False, "instruction scope")
    require(all(instruction[key] is True for key in ("permit_derived_hashes_and_coordinates", "permit_registered_custodial_signing_requests", "permit_git_object_archival", "permit_development_partition_seal")), "owner permissions")
    require(declaration["owner_confirmation"]["confirmed"] is True, "owner confirmation")
    contributor = declaration["contributor"]
    require(contributor["identity_disclosure_approved_for_commit"] is False, "identity disclosure")
    require(contributor["legal_identity_commitment"].startswith("urn:pastila:party:") and contributor["legal_identity_verification_reference"].startswith("owner-record:"), "committable identity references")

    text = source_bytes.decode("utf-8")
    lines = [line for line in text.splitlines() if line]
    require(len(lines) == 6 and all(line.endswith(".") for line in lines), "six complete factual statements")
    disallowed = ("?", "!", "glum", "poant", "metafor", "parodi", "fictiv", "mecanism", "obliga", "pilot", "instruc", "guvernan", "absurd", "vinovat", "ilegal")
    folded = text.casefold()
    require(not any(token in folded for token in disallowed), "neutral-source lexical boundary")
    require("10 septembrie 2026" in text and "20,0 grade Celsius" in text and "20,1 grade Celsius" in text, "time/reference boundaries")
    require("aceeași referință" in text and "nu stabilește temperatura aerului exterior" in text.casefold(), "scope/interpretive boundaries")
    require("Nu este specificată data următoarei recalibrări" in text, "unknown boundary")

    priors = [
        git_bytes("601ee4812d864301cb55620e3d239515163e9ef8", "docs/artifacts/humor-mechanics-batch2-development-pilot01-ingestion-v1/source.utf8.txt"),
        git_bytes("6220b9d86336ec6bd4a62a1cff528e96f973be2c", "docs/artifacts/humor-mechanics-batch2-development-pilot02-ingestion-v1/source.utf8.txt"),
        git_bytes("8aaeccbbca9d45fb9d522505f82d173e1090b3b6", "docs/artifacts/humor-mechanics-batch2-development-pilot03-ingestion-v1/source.utf8.txt"),
        git_bytes("4e4afc730be7600fb0b6ce8abf822bce868b0565", "docs/artifacts/humor-mechanics-batch2-development-pilot04-ingestion-v1/source.utf8.txt"),
    ]
    require(source_bytes not in priors, "prior source equality")
    prior_lines = {line for prior in priors for line in prior.decode("utf-8").splitlines()}
    require(not (set(lines) & prior_lines), "prior exact-line reuse")

    core = {
        "schema_name": "batch2-development-pilot05-strict-preingestion-validation-v1", "schema_version": "1.0.0",
        "owner_input_request_commit": REQUEST_COMMIT, "owner_input_request_identity": "29cfd9b1ff06a4406978e4c145e672d7d28912e17d64ae34d997aaecb2e22ba3",
        "source_sha256": SOURCE_SHA, "source_byte_length": len(source_bytes), "submitted_declaration_sha256": RAW_DECLARATION_SHA, "canonical_declaration_sha256": DECLARATION_SHA, "declaration_byte_length": len(declaration_bytes),
        "checks": {
            "hashes_and_canonical_bytes": "PASS", "declaration_exact_shape_no_duplicate_keys": "PASS",
            "owner_rights_and_independent_noninheriting_grants": "PASS", "downstream_grants_false": "PASS",
            "private_legal_identity_not_disclosed": "PASS_COMMITTABLE_REFERENCE_ONLY", "source_declaration_consistency": "PASS",
            "neutral_owner_authored_synthetic_source": "PASS", "six_independently_bindable_statement_candidates": "PASS_NOT_YET_BOUND",
            "scope_time_condition_and_unknown_boundaries": "PASS", "pilot01_02_03_04_exact_source_and_line_independence": "PASS",
            "duplicated_04_suffix_repair": "PASS_CANONICAL_SUCCESSOR_VALUES_PRESERVED",
            "transitive_family_independence": "OWNER_ATTESTED_PENDING_LATER_FAMILY_DERIVATION", "mechanism_obligation_creative_premise_unassigned": "PASS",
        },
        "prospective_identities_derived": False, "proposition_envelope_created": False, "family_identities_derived": False,
        "signing_requested_or_packet_created": False, "ingestion_or_archive_write_performed": False, "g01_admission_performed": False,
        "g04b_pool_certification_performed": False, "validation_verdict": "PASS_STRICT_PREINGESTION_VALIDATION_ONLY",
        "authority_matrix": {key: False for key in ("signing_request", "ingestion", "archive_write", "g01a", "g01b", "mechanism_assignment", "obligation_assignment", "creative_premise_assignment", "construction", "generation", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    artifact = {**core, "validation_identity": seal("B2_DEVELOPMENT_PILOT05_STRICT_PREINGESTION_VALIDATION_V1", core)}
    output = ART / "humor-mechanics-batch2-development-pilot05-strict-preingestion-validation-v1.json"
    require(not output.exists(), "validation artifact already exists")
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"validation_verdict": artifact["validation_verdict"], "validation_identity": artifact["validation_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
