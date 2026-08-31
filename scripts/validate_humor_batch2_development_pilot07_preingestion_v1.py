"""Strictly validate Pilot 07 owner inputs without deriving or ingesting objects."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot07-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot07-v1.json"
COMMIT = "67faf1bede28efbe4dea6749a70e4cf73ec3f7eb"
SOURCE_SHA = "eaeb78b44b28cc399037892bd31cb82e914573e464ef938dd183736cd03247be"
DECLARATION_SHA = "9c687390c6f34d6bd463e9e59b8b6c9055d7460af7003eaa2fbabe1a57ee2caf"


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
        require(key not in result, f"duplicate key {key}")
        result[key] = value
    return result


def exact_shape(actual: Any, template: Any, path: str = "$") -> None:
    if isinstance(template, dict):
        require(isinstance(actual, dict) and set(actual) == set(template), f"{path} field set")
        for key in template:
            exact_shape(actual[key], template[key], f"{path}.{key}")


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    source_bytes, declaration_bytes = SOURCE.read_bytes(), DECLARATION.read_bytes()
    require(hashlib.sha256(source_bytes).hexdigest() == SOURCE_SHA, "source hash")
    require(hashlib.sha256(declaration_bytes).hexdigest() == DECLARATION_SHA, "declaration hash")
    for name, data in (("source", source_bytes), ("declaration", declaration_bytes)):
        require(not data.startswith(b"\xef\xbb\xbf") and b"\r" not in data, f"{name} encoding")
        require(data.endswith(b"\n") and not data.endswith(b"\n\n"), f"{name} terminal LF")
        data.decode("utf-8")
    declaration = json.loads(declaration_bytes, object_pairs_hook=unique_object)
    template = json.loads(git_bytes("docs/artifacts/humor-mechanics-batch2-development-pilot07-owner-declaration-template-v1.json"))
    template.pop("template_identity")
    exact_shape(declaration, template)
    require(declaration["schema_name"] == "batch2-internally-owned-owner-input-pilot07-v1" and declaration["schema_version"] == "1.0.0", "schema")
    require(declaration["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-07", "pilot")
    meta = declaration["source"]
    require(meta["filename"] == SOURCE.name and meta["declared_encoding"] == "UTF-8" and meta["bom"] is False, "source metadata")
    require(meta["line_endings"] == "LF" and meta["terminal_lf_count"] == 1 and meta["source_version"] == "1.0.0", "format/version")
    require(meta["acquisition_channel"] == "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE" and meta["intended_partition"] == "DEVELOPMENT", "channel")
    require(meta["world_scope"] == meta["subject_class"] == "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE", "scope")
    capture, acquisition = datetime.fromisoformat(meta["capture_timestamp"]), datetime.fromisoformat(meta["acquisition_timestamp"])
    effective = datetime.fromisoformat(declaration["rights_terms"]["effective_at"])
    require(all(value.tzinfo is not None for value in (capture, acquisition, effective)) and capture <= acquisition <= effective, "timestamps")
    ownership = declaration["ownership_declarations"]
    require(all(ownership[key] is True for key in ("original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant")), "ownership")
    require(all(ownership[key] is False for key in ("contains_undisclosed_third_party_material", "contains_private_or_confidential_information",
                                                     "contains_personal_data", "contains_unlawfully_obtained_information",
                                                     "contains_unattributed_quotation", "contains_reputation_sensitive_allegation")), "excluded material")
    grants = declaration["independent_grants"]
    require(all(grants[key] is True for key in ("immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation")), "required grants")
    require(all(grants[key] is False for key in ("model_exposure", "training", "runtime_integration", "production_routing")), "noninheritance")
    require(all(value is True for value in declaration["source_status_declarations"].values()), "source declarations")
    instruction = declaration["owner_instruction"]
    require(instruction["request_preingestion_validation_only"] is True and instruction["operational_content_access_after_ingestion"] is False, "instruction")
    require(all(instruction[key] is True for key in ("permit_derived_hashes_and_coordinates", "permit_registered_custodial_signing_requests",
                                                     "permit_git_object_archival", "permit_development_partition_seal")), "future permissions")
    require(declaration["owner_confirmation"]["confirmed"] is True, "confirmation")
    contributor = declaration["contributor"]
    require(contributor["identity_disclosure_approved_for_commit"] is False, "identity disclosure")
    require(contributor["legal_identity_commitment"].startswith("urn:pastila:party:") and contributor["legal_identity_verification_reference"].startswith("owner-record:"), "identity")
    text = source_bytes.decode(); lines = text.splitlines(); folded = text.casefold()
    require(len(lines) == 6 and all(line.endswith(".") for line in lines), "six statements")
    require(not any(token in folded for token in ("?", "!", "glum", "poant", "metafor", "parodi", "mecanism", "obliga", "pilot", "instruc", "guvernan", "absurd")), "neutrality")
    require("14 septembrie 2026" in text and "08:45" in text and "12 minute" in text, "time/quantity")
    require("proiectorului, a sistemului audio și a iluminării de siguranță" in text, "subsystem scope")
    require("Dacă este observată o problemă tehnică" in text and "pentru analiză ulterioară" in text, "conditional boundary")
    require("nu precizează dacă în urma testului va fi necesară vreo intervenție tehnică" in folded, "unknown boundary")
    prior_paths = [f"docs/artifacts/humor-mechanics-batch2-development-pilot0{i}-ingestion-v1/source.utf8.txt" for i in range(1, 7)]
    priors = [git_bytes(path) for path in prior_paths]
    require(source_bytes not in priors, "prior source equality")
    prior_lines = {line for prior in priors for line in prior.decode().splitlines()}
    require(not (set(lines) & prior_lines), "prior line reuse")
    core = {
        "schema_name": "batch2-development-pilot07-strict-preingestion-validation-v1", "schema_version": "1.0.0",
        "owner_input_request_commit": COMMIT, "owner_input_request_identity": "4ae18b3eddf1c230717f6461875a3dd63a3008a9810b46154d57983599333d4e",
        "governance_identity": "4848bd025e43eff6652e4c2024072760d372ca4ac7427e5f21e1d2c4bcdb35dc",
        "source_sha256": SOURCE_SHA, "source_byte_length": len(source_bytes),
        "declaration_sha256": DECLARATION_SHA, "declaration_byte_length": len(declaration_bytes),
        "checks": {"hashes_encoding_lf_and_exact_shape": "PASS", "owner_rights_and_independent_grants": "PASS",
                   "downstream_grants_false": "PASS", "private_legal_identity_not_disclosed": "PASS_COMMITTABLE_REFERENCE_ONLY",
                   "neutral_owner_authored_synthetic_source": "PASS", "six_independently_bindable_statement_candidates": "PASS_NOT_YET_BOUND",
                   "scope_time_condition_and_unknown_boundaries": "PASS", "pilot01_through_06_exact_source_and_line_independence": "PASS",
                   "transitive_family_independence": "OWNER_ATTESTED_PENDING_LATER_FAMILY_DERIVATION",
                   "mechanism_obligation_selected_proposition_and_creative_premise_unassigned": "PASS"},
        "proposition_sufficiency_evaluated": False, "prospective_identities_derived": False,
        "proposition_envelope_created": False, "family_identities_derived": False,
        "signing_requested_or_packet_created": False, "ingestion_or_archive_write_performed": False,
        "g01_admission_performed": False, "assignment_or_constructor_release_performed": False,
        "g04b_pool_certification_performed": False, "validation_verdict": "PASS_STRICT_PREINGESTION_VALIDATION_ONLY",
        "authority_matrix": {key: False for key in ("proposition_sufficiency_evaluation", "signing", "ingestion", "archive_write", "g01a", "g01b",
                                                               "assignment", "constructor_release", "construction", "g04b_pool_certification", "model_exposure",
                                                               "training", "runtime_integration", "production_routing")},
    }
    artifact = {**core, "validation_identity": seal("B2_DEVELOPMENT_PILOT07_STRICT_PREINGESTION_VALIDATION_V1", core)}
    output = ART / "humor-mechanics-batch2-development-pilot07-strict-preingestion-validation-v1.json"
    require(not output.exists(), "validation exists")
    output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"validation_verdict": artifact["validation_verdict"], "validation_identity": artifact["validation_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
