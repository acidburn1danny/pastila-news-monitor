"""Strictly validate Pilot 06 owner inputs without deriving or ingesting objects."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot06-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot06-v1.json"
REQUEST_COMMIT = "325716e3f1a7f9ee0d324bb51361bd2cc6802407"
SOURCE_SHA = "eb97e6bdffc809d0902f90bb26b95c3c4a6047476b27eec7ac46b613dba030ad"
DECLARATION_SHA = "9612cd4e0b58b752636b83dfcab28f2e0c4eb208981f52b6b34f9295526050c4"


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
        require(key not in result, f"duplicate declaration key: {key}")
        result[key] = value
    return result


def assert_exact_shape(actual: Any, template: Any, path: str = "$") -> None:
    if isinstance(template, dict):
        require(isinstance(actual, dict), f"{path} must be object")
        require(set(actual) == set(template), f"{path} field set")
        for key in template:
            assert_exact_shape(actual[key], template[key], f"{path}.{key}")


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{REQUEST_COMMIT}:{path}"], cwd=ROOT)


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == REQUEST_COMMIT, "HEAD")
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    require(hashlib.sha256(source_bytes).hexdigest() == SOURCE_SHA, "source SHA-256")
    require(hashlib.sha256(declaration_bytes).hexdigest() == DECLARATION_SHA, "declaration SHA-256")
    for name, data in (("source", source_bytes), ("declaration", declaration_bytes)):
        require(not data.startswith(b"\xef\xbb\xbf"), f"{name} BOM")
        require(b"\r" not in data, f"{name} CR")
        require(data.endswith(b"\n") and not data.endswith(b"\n\n"), f"{name} terminal LF")
        data.decode("utf-8")

    declaration = json.loads(declaration_bytes, object_pairs_hook=unique_object)
    template = json.loads(git_bytes("docs/artifacts/humor-mechanics-batch2-development-pilot06-owner-declaration-template-v1.json"))
    template.pop("template_identity")
    assert_exact_shape(declaration, template)
    require(declaration["schema_name"] == "batch2-internally-owned-owner-input-pilot06-v1" and declaration["schema_version"] == "1.0.0", "schema")
    require(declaration["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-06", "pilot")
    source_meta = declaration["source"]
    require(source_meta["filename"] == SOURCE.name and source_meta["declared_encoding"] == "UTF-8", "source metadata")
    require(source_meta["bom"] is False and source_meta["line_endings"] == "LF" and source_meta["terminal_lf_count"] == 1, "format metadata")
    require(source_meta["source_version"] == "1.0.0" and source_meta["acquisition_channel"] == "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE", "channel")
    require(source_meta["intended_partition"] == "DEVELOPMENT" and source_meta["world_scope"] == "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE", "scope")
    capture = datetime.fromisoformat(source_meta["capture_timestamp"])
    acquisition = datetime.fromisoformat(source_meta["acquisition_timestamp"])
    effective = datetime.fromisoformat(declaration["rights_terms"]["effective_at"])
    require(all(value.tzinfo is not None for value in (capture, acquisition, effective)) and capture <= acquisition <= effective, "timestamps")

    ownership = declaration["ownership_declarations"]
    require(all(ownership[key] is True for key in ("original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant")), "ownership")
    require(all(ownership[key] is False for key in ("contains_undisclosed_third_party_material", "contains_private_or_confidential_information",
                                                     "contains_personal_data", "contains_unlawfully_obtained_information",
                                                     "contains_unattributed_quotation", "contains_reputation_sensitive_allegation")), "excluded material")
    grants = declaration["independent_grants"]
    require(all(grants[key] is True for key in ("immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation")), "required grants")
    require(all(grants[key] is False for key in ("model_exposure", "training", "runtime_integration", "production_routing")), "downstream grants")
    require(all(value is True for value in declaration["source_status_declarations"].values()), "source declarations")
    instruction = declaration["owner_instruction"]
    require(instruction["request_preingestion_validation_only"] is True and instruction["operational_content_access_after_ingestion"] is False, "instruction")
    require(all(instruction[key] is True for key in ("permit_derived_hashes_and_coordinates", "permit_registered_custodial_signing_requests",
                                                     "permit_git_object_archival", "permit_development_partition_seal")), "future permissions")
    require(declaration["owner_confirmation"]["confirmed"] is True, "confirmation")
    contributor = declaration["contributor"]
    require(contributor["identity_disclosure_approved_for_commit"] is False, "identity disclosure")
    require(contributor["legal_identity_commitment"].startswith("urn:pastila:party:") and contributor["legal_identity_verification_reference"].startswith("owner-record:"), "identity references")

    text = source_bytes.decode("utf-8")
    lines = text.splitlines()
    require(len(lines) == 6 and all(line.endswith(".") for line in lines), "six factual statements")
    folded = text.casefold()
    disallowed = ("?", "!", "glum", "poant", "metafor", "parodi", "mecanism", "obliga", "pilot", "instruc", "guvernan", "absurd")
    require(not any(token in folded for token in disallowed), "neutral lexical boundary")
    require("12 septembrie 2026" in text and "09:30" in text and "14:00" in text, "time boundaries")
    require("nu include colecția de fotografii sau arhiva de presă" in folded, "scope exclusion")
    require("nu este stabilită data următoarei inventarieri" in folded, "unknown boundary")
    require("„verificat”" in text, "owner-authored register label")

    prior_paths = [f"docs/artifacts/humor-mechanics-batch2-development-pilot0{i}-ingestion-v1/source.utf8.txt" for i in range(1, 6)]
    priors = [git_bytes(path) for path in prior_paths]
    require(source_bytes not in priors, "prior source equality")
    prior_lines = {line for prior in priors for line in prior.decode("utf-8").splitlines()}
    require(not (set(lines) & prior_lines), "prior exact-line reuse")

    core = {
        "schema_name": "batch2-development-pilot06-strict-preingestion-validation-v1", "schema_version": "1.0.0",
        "owner_input_request_commit": REQUEST_COMMIT,
        "owner_input_request_identity": "607cc62af2313130dd30637e6854eedf0252f5e5f4bb83245e2f50873f74e02e",
        "source_sha256": SOURCE_SHA, "source_byte_length": len(source_bytes),
        "declaration_sha256": DECLARATION_SHA, "declaration_byte_length": len(declaration_bytes),
        "checks": {"hashes_encoding_lf_and_exact_shape": "PASS", "owner_rights_and_independent_grants": "PASS",
                   "downstream_grants_false": "PASS", "private_legal_identity_not_disclosed": "PASS_COMMITTABLE_REFERENCE_ONLY",
                   "neutral_owner_authored_synthetic_source": "PASS", "six_independently_bindable_statement_candidates": "PASS_NOT_YET_BOUND",
                   "scope_time_and_unknown_boundaries": "PASS", "owner_authored_register_label_not_third_party_quotation": "PASS",
                   "pilot01_through_05_exact_source_and_line_independence": "PASS",
                   "transitive_family_independence": "OWNER_ATTESTED_PENDING_LATER_FAMILY_DERIVATION",
                   "mechanism_obligation_selected_proposition_and_creative_premise_unassigned": "PASS"},
        "proposition_sufficiency_evaluated": False, "prospective_identities_derived": False,
        "proposition_envelope_created": False, "family_identities_derived": False,
        "signing_requested_or_packet_created": False, "ingestion_or_archive_write_performed": False,
        "g01_admission_performed": False, "assignment_or_constructor_release_performed": False,
        "g04b_pool_certification_performed": False, "validation_verdict": "PASS_STRICT_PREINGESTION_VALIDATION_ONLY",
        "authority_matrix": {key: False for key in ("proposition_sufficiency_evaluation", "signing", "ingestion", "archive_write",
                                                     "g01a", "g01b", "assignment", "constructor_release", "construction",
                                                     "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    artifact = {**core, "validation_identity": seal("B2_DEVELOPMENT_PILOT06_STRICT_PREINGESTION_VALIDATION_V1", core)}
    output = ART / "humor-mechanics-batch2-development-pilot06-strict-preingestion-validation-v1.json"
    require(not output.exists(), "validation already exists")
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"validation_verdict": artifact["validation_verdict"], "validation_identity": artifact["validation_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
