"""Strictly validate Pilot 08 owner inputs without deriving or ingesting objects."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"
SOURCE = ROOT / "owner-source-pilot08-v1.txt"
DECLARATION = ROOT / "owner-declaration-pilot08-v1.json"
REQUEST_COMMIT = "0bc3ccff62ca703a8a5fbce3ed650a5c77b8eacf"
SOURCE_SHA256 = "d2a71300c1d1832f68132e4b824714ec0bc51beecf26f750146befb00a26712a"
DECLARATION_SHA256 = "7a7da131c60d7a2e1aece6804edd5c7256dca15e534cf3cac3205ebdf39b74b4"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
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

    declaration = json.loads(declaration_bytes, object_pairs_hook=unique_object)
    template = json.loads(
        git_bytes("docs/artifacts/humor-mechanics-batch2-development-pilot08-owner-declaration-template-v1.json")
    )
    template.pop("template_identity")
    exact_shape(declaration, template)
    require(declaration["schema_name"] == "batch2-internally-owned-owner-input-pilot08-v1", "schema name")
    require(declaration["schema_version"] == "1.0.0", "schema version")
    require(declaration["pilot_id"] == "BATCH2-INTERNALLY-OWNED-DEVELOPMENT-PILOT-08", "pilot")

    source_meta = declaration["source"]
    require(source_meta["filename"] == SOURCE.name, "source filename")
    require(source_meta["declared_encoding"] == "UTF-8" and source_meta["bom"] is False, "source encoding declaration")
    require(source_meta["line_endings"] == "LF" and source_meta["terminal_lf_count"] == 1, "source format declaration")
    require(source_meta["source_version"] == "1.0.0", "source version")
    require(source_meta["acquisition_channel"] == "INTERNALLY_OWNED_FACTUAL_AUTHORITY_BUNDLE", "channel")
    require(source_meta["intended_partition"] == "DEVELOPMENT", "partition")
    require(source_meta["world_scope"] == source_meta["subject_class"] == "OWNER_AUTHORED_SYNTHETIC_TEST_UNIVERSE", "world scope")
    capture = datetime.fromisoformat(source_meta["capture_timestamp"])
    acquisition = datetime.fromisoformat(source_meta["acquisition_timestamp"])
    effective = datetime.fromisoformat(declaration["rights_terms"]["effective_at"])
    require(all(value.tzinfo is not None for value in (capture, acquisition, effective)), "timezone-aware timestamps")
    require(capture <= acquisition <= effective, "timestamp order")

    ownership = declaration["ownership_declarations"]
    require(all(ownership[key] is True for key in (
        "original_authorship", "owns_or_controls_required_rights", "has_authority_to_make_each_selected_grant"
    )), "ownership")
    require(all(ownership[key] is False for key in (
        "contains_undisclosed_third_party_material",
        "contains_private_or_confidential_information",
        "contains_personal_data",
        "contains_unlawfully_obtained_information",
        "contains_unattributed_quotation",
        "contains_reputation_sensitive_allegation",
    )), "excluded material")
    grants = declaration["independent_grants"]
    require(all(grants[key] is True for key in (
        "immutable_archival", "factual_annotation_and_authority_binding", "internal_discovery", "construction_and_evaluation"
    )), "required grants")
    require(all(grants[key] is False for key in (
        "model_exposure", "training", "runtime_integration", "production_routing"
    )), "strict noninheritance")
    require(all(value is True for value in declaration["source_status_declarations"].values()), "source declarations")
    instruction = declaration["owner_instruction"]
    require(instruction["request_preingestion_validation_only"] is True, "validation-only instruction")
    require(instruction["operational_content_access_after_ingestion"] is False, "operational access")
    require(all(instruction[key] is True for key in (
        "permit_derived_hashes_and_coordinates",
        "permit_registered_custodial_signing_requests",
        "permit_git_object_archival",
        "permit_development_partition_seal",
    )), "future permissions")
    contributor = declaration["contributor"]
    require(contributor["identity_disclosure_approved_for_commit"] is False, "identity disclosure")
    require(contributor["legal_identity_commitment"].startswith("urn:pastila:party:"), "identity commitment")
    require(contributor["legal_identity_verification_reference"].startswith("owner-record:"), "identity reference")
    require(declaration["owner_confirmation"]["confirmed"] is True, "owner confirmation")

    source_text = source_bytes.decode("utf-8")
    folded = source_text.casefold()
    paragraphs = [part for part in source_text.split("\n\n") if part]
    sentences = [part for part in re.split(r"(?<=[.!?])\s+", source_text.strip()) if part]
    require(len(paragraphs) == 3 and len(sentences) == 7, "source proposition candidates")
    require(not any(token in folded for token in (
        "?", "!", "glum", "poant", "metafor", "parodi", "mecanism", "obliga", "pilot", "instruc", "guvernan", "absurd"
    )), "neutrality")
    require("16 septembrie 2026" in source_text and "07:00" in source_text and "11:30" in source_text, "time scope")
    require("șase zone de vegetație" in source_text and "controlate separat" in source_text, "system scope")
    require("O zonă care nu răspunde corect" in source_text and "pentru verificarea ulterioară" in source_text, "conditional boundary")
    require("nu se știe dacă vor fi găsite defecțiuni" in source_text, "unknown defect boundary")
    require("nici dacă va fi necesară înlocuirea vreunei componente" in source_text, "unknown replacement boundary")

    prior_paths = [
        f"docs/artifacts/humor-mechanics-batch2-development-pilot0{index}-ingestion-v1/source.utf8.txt"
        for index in range(1, 8)
    ]
    prior_sources = [git_bytes(path) for path in prior_paths]
    require(source_bytes not in prior_sources, "prior source equality")
    current_nonblank_lines = {line for line in source_text.splitlines() if line}
    prior_nonblank_lines = {
        line
        for prior in prior_sources
        for line in prior.decode("utf-8").splitlines()
        if line
    }
    require(not current_nonblank_lines.intersection(prior_nonblank_lines), "prior exact line reuse")

    require(source_bytes.endswith(b"\n") and not source_bytes.endswith(b"\n\n"), "source terminal LF")
    require(declaration_bytes.endswith(b"\n") and not declaration_bytes.endswith(b"\n\n"), "declaration terminal LF")
    blockers: list[str] = []

    core = {
        "schema_name": "batch2-development-pilot08-strict-preingestion-validation-v1",
        "schema_version": "1.0.0",
        "owner_input_request_commit": REQUEST_COMMIT,
        "owner_input_request_identity": "147457b5be10db0002e1015fe9fd7e34d2b3d3195c8731167467c92614b37138",
        "governance_identity": "cc86204c6f199c80ef7c7bf87a58cf3c62d17acb1fe14bd2666bbf5ba86692f6",
        "source_sha256": SOURCE_SHA256,
        "source_byte_length": len(source_bytes),
        "declaration_sha256": DECLARATION_SHA256,
        "declaration_byte_length": len(declaration_bytes),
        "checks": {
            "hashes": "PASS",
            "utf8_no_bom_lf_only": "PASS",
            "exact_schema_shape": "PASS",
            "owner_rights_and_independent_grants": "PASS",
            "downstream_grants_false": "PASS_STRICT_NONINHERITANCE",
            "private_legal_identity_not_disclosed": "PASS_COMMITTABLE_REFERENCE_ONLY",
            "neutral_owner_authored_synthetic_source": "PASS",
            "seven_independently_bindable_statement_candidates": "PASS_NOT_YET_BOUND",
            "scope_time_condition_and_unknown_boundaries": "PASS",
            "pilot01_through_07_exact_source_and_line_independence": "PASS",
            "transitive_family_independence": "OWNER_ATTESTED_PENDING_LATER_FAMILY_DERIVATION",
            "mechanism_obligation_selected_proposition_creative_premise_and_marker_unassigned": "PASS",
            "source_exactly_one_terminal_lf": "PASS",
            "declaration_exactly_one_terminal_lf": "PASS",
            "declaration_terminal_lf_claim_matches_bytes": "PASS",
        },
        "deterministic_blockers": blockers,
        "repair_performed": False,
        "repair_reason": "NOT_APPLICABLE_INPUTS_VALIDATED_BYTE_EXACT",
        "proposition_sufficiency_evaluated": False,
        "prospective_identities_derived": False,
        "proposition_envelope_created": False,
        "family_identities_derived": False,
        "signing_requested_or_packet_created": False,
        "ingestion_or_archive_write_performed": False,
        "g01_admission_performed": False,
        "assignment_constructor_implementation_or_release_performed": False,
        "fragment_collision_evaluation_performed": False,
        "g04b_pool_certification_performed": False,
        "validation_verdict": "PASS_STRICT_PREINGESTION_VALIDATION_ONLY",
        "authority_matrix": {
            key: False
            for key in (
                "proposition_sufficiency_evaluation",
                "signing",
                "ingestion",
                "archive_write",
                "g01a",
                "g01b",
                "assignment",
                "constructor_implementation",
                "constructor_release",
                "construction",
                "fragment_collision_evaluation",
                "g04b_pool_certification",
                "model_exposure",
                "training",
                "runtime_integration",
                "production_routing",
            )
        },
    }
    artifact = {
        **core,
        "validation_identity": seal("B2_DEVELOPMENT_PILOT08_STRICT_PREINGESTION_VALIDATION_V1", core),
    }
    output = ARTIFACTS / "humor-mechanics-batch2-development-pilot08-strict-preingestion-validation-v1.json"
    require(not output.exists(), "validation artifact already exists")
    output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({
        "validation_verdict": artifact["validation_verdict"],
        "validation_identity": artifact["validation_identity"],
        "deterministic_blockers": artifact["deterministic_blockers"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
