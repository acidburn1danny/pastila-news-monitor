"""Strictly validate Pilot 03 owner inputs without deriving or ingesting objects."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot03-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot03-v1.json"
REQUEST_COMMIT = "d75d2042ff290b218b75cedc54cf4e613b4610e3"
SOURCE_SHA = "61a5889cb03f72c6f4f72b0f1652b2db43c092f51c91f7d5e59933a99ca2fc30"
DECLARATION_SHA = "5915ee71841ed1a40ae375e0e7c6a4b611c525d0b8690464e61d66e078b14d8d"


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


def load_prior_source(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def main() -> None:
    require(
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == REQUEST_COMMIT,
        "HEAD differs from Pilot 03 owner-input freeze",
    )
    source_bytes = SOURCE.read_bytes()
    declaration_bytes = DECLARATION.read_bytes()
    require(hashlib.sha256(source_bytes).hexdigest() == SOURCE_SHA, "source SHA-256")
    require(hashlib.sha256(declaration_bytes).hexdigest() == DECLARATION_SHA, "declaration SHA-256")
    for name, data in (("source", source_bytes), ("declaration", declaration_bytes)):
        require(not data.startswith(b"\xef\xbb\xbf"), f"{name} BOM")
        require(b"\r" not in data, f"{name} CR")
        require(data.endswith(b"\n") and not data.endswith(b"\n\n"), f"{name} terminal LF")
        data.decode("utf-8")

    declaration = json.loads(declaration_bytes, object_pairs_hook=unique_object)
    template = json.loads(subprocess.check_output([
        "git", "show", f"{REQUEST_COMMIT}:docs/artifacts/humor-mechanics-batch2-development-pilot03-owner-declaration-template-v1.json"
    ], cwd=ROOT))
    template.pop("template_identity")
    assert_exact_shape(declaration, template)
    require(declaration["schema_name"] == "batch2-internally-owned-owner-input-v1", "schema name")
    require(declaration["schema_version"] == "1.0.0", "schema version")
    require(declaration["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-03", "pilot id")
    source_meta = declaration["source"]
    require(source_meta == {
        **source_meta,
        "filename": "owner-source-pilot03-v1.txt",
        "declared_encoding": "UTF-8",
        "bom": False,
        "line_endings": "LF",
        "terminal_lf_count": 1,
        "acquisition_channel": "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE",
        "intended_partition": "DEVELOPMENT",
    }, "source technical metadata")
    require(source_meta["source_version"] == "1.0.0", "source version")
    capture = datetime.fromisoformat(source_meta["capture_timestamp"])
    acquisition = datetime.fromisoformat(source_meta["acquisition_timestamp"])
    effective = datetime.fromisoformat(declaration["rights_terms"]["effective_at"])
    require(capture.tzinfo is not None and acquisition.tzinfo is not None and effective.tzinfo is not None, "timestamps need offsets")
    require(capture <= acquisition <= effective, "timestamp order")

    ownership = declaration["ownership_declarations"]
    require(all(ownership[key] is True for key in (
        "original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant"
    )), "positive ownership declarations")
    require(all(ownership[key] is False for key in (
        "contains_undisclosed_third_party_material", "contains_private_or_confidential_information",
        "contains_personal_data", "contains_unlawfully_obtained_information",
        "contains_unattributed_quotation", "contains_reputation_sensitive_allegation",
    )), "excluded material declarations")
    grants = declaration["independent_grants"]
    require(all(grants[key] is True for key in (
        "immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation"
    )), "required independent grants")
    require(all(grants[key] is False for key in (
        "model_exposure", "training", "runtime_integration", "production_routing"
    )), "downstream grants")
    status = declaration["source_status_declarations"]
    require(all(value is True for value in status.values()), "source status declarations")
    instruction = declaration["owner_instruction"]
    require(instruction["requested_action"] == "PREINGESTION_VALIDATION_ONLY", "requested action")
    require(instruction["operational_content_access_after_ingestion"] is False, "operational access")
    require(all(instruction[key] is True for key in (
        "permit_derived_hashes_and_coordinates", "permit_registered_custodial_signing_requests",
        "permit_git_object_archival", "permit_partition_seal_for_development_only",
    )), "owner permissions")
    require(declaration["owner_confirmation"]["confirmed"] is True, "owner confirmation")
    require(declaration["contributor"]["identity_disclosure_approved_for_commit"] is False, "private legal identity disclosure")
    require(declaration["contributor"]["legal_identity"].startswith("urn:pastila:party:"), "committable legal reference")
    require(declaration["contributor"]["legal_identity_verification_reference"].startswith("owner-record:"), "nonsecret verification reference")

    source = source_bytes.decode("utf-8")
    lines = [line for line in source.splitlines() if line]
    require(len(lines) == 6, "six neutral source statements expected")
    require(all(line.endswith(".") for line in lines), "complete statements")
    neutral_disallowed = (
        "?", "!", "glum", "poant", "metafor", "parodi", "fictiv", "mecanism", "obliga",
        "pilot", "instruc", "guvernan", "absurd", "intenția", "vinovat", "ilegal",
    )
    folded = source.casefold()
    require(not any(token in folded for token in neutral_disallowed), "neutral-source lexical boundary")
    require("6 septembrie 2026" in source and "09:40" in source and "11:00" in source, "time boundaries")
    require("3,2 kilograme" in source and "L-204" in source, "quantity and identifier boundaries")
    require("nu este documentat conținutul exact" in source, "explicit unknown boundary")

    pilot01 = load_prior_source("601ee4812d864301cb55620e3d239515163e9ef8", "docs/artifacts/humor-mechanics-batch2-development-pilot01-ingestion-v1/source.utf8.txt")
    pilot02 = load_prior_source("6220b9d86336ec6bd4a62a1cff528e96f973be2c", "docs/artifacts/humor-mechanics-batch2-development-pilot02-ingestion-v1/source.utf8.txt")
    require(source_bytes not in (pilot01, pilot02), "prior source equality")
    prior_lines = set(pilot01.decode("utf-8").splitlines()) | set(pilot02.decode("utf-8").splitlines())
    require(not (set(lines) & prior_lines), "exact prior-line reuse")

    core = {
        "schema_name": "batch2-development-pilot03-strict-preingestion-validation-v1",
        "schema_version": "1.0.0",
        "governance_commit": "618333a3db484da134904aea004a36e9cb0350d4",
        "owner_input_request_commit": REQUEST_COMMIT,
        "owner_input_request_identity": "60aead240f7a075f8c7c4680a64b61cdc45d3b23cd7536810c0f5622b13cd3e0",
        "source_sha256": SOURCE_SHA,
        "source_byte_length": len(source_bytes),
        "declaration_sha256": DECLARATION_SHA,
        "declaration_byte_length": len(declaration_bytes),
        "checks": {
            "hashes": "PASS",
            "utf8_no_bom_lf_one_terminal_lf": "PASS",
            "declaration_exact_field_set_no_duplicates": "PASS",
            "owner_rights_and_authority": "PASS",
            "independent_grants_noninheritance": "PASS",
            "model_training_runtime_production_grants_false": "PASS",
            "private_legal_identity_not_committed": "PASS_PUBLIC_URN_AND_NONSECRET_OWNER_RECORD_REFERENCE_ONLY",
            "source_declaration_consistency": "PASS",
            "neutral_owner_authored_synthetic_source": "PASS",
            "six_independently_bindable_statement_candidates": "PASS_NOT_YET_BOUND",
            "time_quantity_process_and_unknown_boundaries": "PASS",
            "pilot01_pilot02_exact_source_and_line_independence": "PASS",
            "owner_declared_family_independence": "PASS_PENDING_LATER_FAMILY_DERIVATION",
            "mechanism_obligation_creative_premise_unassigned": "PASS",
        },
        "prospective_identities_derived": False,
        "proposition_envelope_created": False,
        "family_identities_derived": False,
        "signing_requested_or_packet_created": False,
        "ingestion_or_archive_write_performed": False,
        "g01_admission_performed": False,
        "validation_verdict": "PASS_STRICT_PREINGESTION_VALIDATION_ONLY",
        "authority_matrix": {
            key: False for key in (
                "signing_request", "ingestion", "archive_write", "g01a", "g01b", "mechanism_assignment",
                "obligation_assignment", "creative_premise_assignment", "construction", "generation",
                "model_exposure", "training", "runtime_integration", "production_routing",
            )
        },
    }
    artifact = {
        **core,
        "validation_identity": seal("B2_DEVELOPMENT_PILOT03_STRICT_PREINGESTION_VALIDATION_V1", core),
    }
    output = ART / "humor-mechanics-batch2-development-pilot03-strict-preingestion-validation-v1.json"
    require(not output.exists(), "validation artifact already exists")
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "validation_verdict": artifact["validation_verdict"],
        "validation_identity": artifact["validation_identity"],
        "source_sha256": artifact["source_sha256"],
        "declaration_sha256": artifact["declaration_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
