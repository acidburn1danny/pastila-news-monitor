"""Mechanism-neutral G02C conformance review for Pilot 02 candidate 01."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
G02_COMMIT = "9d3493cad4fc59410f3bbcdd330e16b1da6c5197"
INGESTION_COMMIT = "6220b9d86336ec6bd4a62a1cff528e96f973be2c"
GOVERNANCE_COMMIT = "a444ace2e6eb8bfad006374f266c90269c665565"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-v1.txt"
G02_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-g02-v1.json"
ENVELOPE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot02-ingestion-v1/factual-authority-envelope.json"
GOVERNANCE_PATH = "docs/artifacts/humor-mechanics-batch2-successor-obligation-governance-v1.json"
SCHEMA_PATH = "docs/artifacts/humor-mechanics-batch2-obligation-conformance-schema-v1.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_bytes(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def git_json(commit: str, path: str) -> dict[str, Any]:
    return json.loads(git_bytes(commit, path))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def candidate_span(text: str, start: int, end: int) -> dict[str, Any]:
    raw = text[start:end].encode("utf-8")
    return {
        "character_coordinates": [start, end],
        "utf8_byte_coordinates": [len(text[:start].encode("utf-8")), len(text[:end].encode("utf-8"))],
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def source_span(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "character_coordinates": item["character_coordinates"],
        "utf8_byte_coordinates": item["utf8_byte_coordinates"],
        "sha256": item.get("sha256", item.get("span_sha256")),
    }


def main() -> None:
    receipt_path = ART / "humor-mechanics-batch2-development-pilot02-candidate01-g02c-conformance-receipt-v1.json"
    review_path = ART / "humor-mechanics-batch2-development-pilot02-candidate01-g02c-review-v1.json"
    require(not receipt_path.exists() and not review_path.exists(), "G02C already frozen")
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == G02_COMMIT,
            "HEAD differs from G02 commit")
    candidate = git_bytes(G02_COMMIT, CANDIDATE_PATH)
    g02 = git_json(G02_COMMIT, G02_PATH)
    envelope = git_json(INGESTION_COMMIT, ENVELOPE_PATH)
    governance = git_json(GOVERNANCE_COMMIT, GOVERNANCE_PATH)
    schema = git_json(GOVERNANCE_COMMIT, SCHEMA_PATH)
    require(g02["g02_verdict"] == "PASS" and g02["g02_receipt_identity"] ==
            "adf92833cf079d5df823c9d899618da8f8f8367cab3215f96be5ad6fd0d3c7f2", "G02 binding")
    require(hashlib.sha256(candidate).hexdigest() == "5c50ca8e4ae5ea32301c02ec8ea4104482bbc9c8e3c7e8314516d09aeb591fd3", "candidate hash")
    require(governance["obligation_governance_identity"] == "0cfd22fd43e0be68b5a04f16e45e918ac7bae346c851334817a7af309bad63e5", "governance")
    require(schema["conformance_schema_identity"] == "11bb3e5bc2e6a3b3830c0f751539b5688693f37702d7e13943112a768966e44a", "schema")

    text = candidate.decode("utf-8")
    p7 = next(item for item in envelope["propositions"] if item["proposition_id"] == "P7")
    source_text = git_bytes(INGESTION_COMMIT,
                            "docs/artifacts/humor-mechanics-batch2-development-pilot02-ingestion-v1/source.utf8.txt").decode("utf-8")
    source_start, source_end = p7["supporting_span"]["character_coordinates"]
    p7_surface = source_text[source_start:source_end]
    require(text.startswith(p7_surface + " "), "selected proposition")
    step1_text = "lipsa câștigătorului suspendă mai întâi încheierea testului"
    step2_text = ("fiindcă testul nu se mai poate încheia, momentul în care ar trebui stabilit "
                  "câștigătorul încetează apoi să mai existe")
    step1_start, step2_start = text.index(step1_text), text.index(step2_text)
    step1_end, step2_end = step1_start + len(step1_text), step2_start + len(step2_text)
    require(step1_end < step2_start and text[step1_end:step2_start] == "; ", "ordered distinct steps")

    relation_core = {
        "proposition_id": "P7",
        "subject_span": source_span(p7["subject"]),
        "predicate_span": source_span(p7["predicate"]),
        "object_span": source_span(p7["object"]),
    }
    relation_fingerprint = seal("B2_G02C_CONTINUED_RELATION_V1", relation_core)
    receipt = {
        "candidate_identity": "4cc6bceef84e29d07e19d60dbbb1992b33fcb8af67373647f5fb8fedfce1d98c",
        "obligation_identity": governance["obligation_governance_identity"],
        "selected_proposition": {
            "proposition_id": "P7",
            "source_span": source_span(p7["supporting_span"]),
        },
        "continued_relation": {
            "subject_span": relation_core["subject_span"],
            "predicate_span": relation_core["predicate_span"],
            "object_span": relation_core["object_span"],
            "relation_fingerprint": relation_fingerprint,
        },
        "steps": [
            {"ordinal": 1, "candidate_span": candidate_span(text, step1_start, step1_end),
             "same_relation_operates": True, "locally_understandable": True},
            {"ordinal": 2, "candidate_span": candidate_span(text, step2_start, step2_end),
             "same_relation_operates": True, "locally_understandable": True},
        ],
        "dependency": {
            "step2_requires_step1": True,
            "removal_test": "STEP2_STRUCTURALLY_UNAVAILABLE_WITHOUT_STEP1",
            "unrelated_replacement_possible": False,
        },
        "imported_relation": {"present": False, "primary_connector": False},
        "entity_status": {"unauthorized_attribute_or_role_added": False, "human_agency_supplies_connection": False},
        "neighbor_substitution": {
            "comparison_or_domain_transfer": False,
            "magnitude_only": False,
            "enumeration": False,
            "disconnected_surprise": False,
        },
        "verdict": "PASS",
    }
    errors = sorted(Draft202012Validator(schema).iter_errors(receipt), key=lambda error: list(error.path))
    require(not errors, "schema validation: " + "; ".join(error.message for error in errors))

    candidate_bytes = candidate
    for step in receipt["steps"]:
        span = step["candidate_span"]
        cs, ce = span["character_coordinates"]
        bs, be = span["utf8_byte_coordinates"]
        raw = text[cs:ce].encode("utf-8")
        require(raw == candidate_bytes[bs:be] and hashlib.sha256(raw).hexdigest() == span["sha256"], "step span")
    for key in ("subject_span", "predicate_span", "object_span"):
        span = receipt["continued_relation"][key]
        cs, ce = span["character_coordinates"]
        bs, be = span["utf8_byte_coordinates"]
        raw = source_text[cs:ce].encode("utf-8")
        require(raw == source_text.encode("utf-8")[bs:be] and hashlib.sha256(raw).hexdigest() == span["sha256"], "relation span")
    require(seal("B2_G02C_CONTINUED_RELATION_V1", relation_core) == relation_fingerprint, "relation fingerprint")

    receipt_identity = seal("B2_DEVELOPMENT_PILOT02_G02C_CONFORMANCE_RECEIPT_V1", receipt)
    review_core = {
        "schema_name": "batch2-development-pilot02-candidate-g02c-review-v1",
        "schema_version": "1.0.0",
        "candidate_identity": receipt["candidate_identity"],
        "candidate_raw_sha256": hashlib.sha256(candidate).hexdigest(),
        "creative_premise_family_id": "ccb8ffaa1f8bd4f1cc40042854a76e73c3fb99d08f359da2e7ea952796bd7467",
        "g02_commit": G02_COMMIT,
        "g02_receipt_identity": g02["g02_receipt_identity"],
        "obligation_governance_identity": governance["obligation_governance_identity"],
        "conformance_schema_identity": schema["conformance_schema_identity"],
        "conformance_receipt_identity": receipt_identity,
        "schema_validation": "PASS_DRAFT_2020_12",
        "semantic_verification_rules": "PASS_ALL_FROZEN_RULES",
        "selected_proposition_and_relation": "PASS_EXACT_P7_AUTHORITY_SPANS",
        "two_distinct_changes": "PASS_ORDERED_NONOVERLAPPING",
        "dependency_removal_test": "PASS_STEP2_UNAVAILABLE_WITHOUT_STEP1",
        "entity_status": "PASS_NO_ATTRIBUTE_ROLE_OR_HUMAN_AGENCY_ADDED",
        "imported_relation": "ABSENT",
        "neighbor_substitution": "ABSENT",
        "mechanism_neutrality": "PASS_TARGET_MAPPING_NOT_ACCESSED",
        "reviewer_accessed_artifacts": ["CANDIDATE", "G02_RECEIPT", "AUTHORITY_ENVELOPE", "SOURCE", "OBLIGATION_GOVERNANCE", "CONFORMANCE_SCHEMA"],
        "sealed_mapping_accessed": False,
        "g03_performed": False,
        "candidate_modified": False,
        "g02c_verdict": "PASS",
        "eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_BLIND_G03_MECHANISM_RECOVERY",
        "authority_matrix": {key: False for key in (
            "g03_mechanism_recovery", "repair", "rewrite", "regeneration", "owner_review", "training",
            "runtime_integration", "production_routing")},
    }
    review = {**review_core, "g02c_review_identity": seal("B2_DEVELOPMENT_PILOT02_G02C_REVIEW_V1", review_core)}
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    review_path.write_text(json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "g02c_verdict": "PASS",
        "conformance_receipt_identity": receipt_identity,
        "g02c_review_identity": review["g02c_review_identity"],
        "schema_validation": review["schema_validation"],
        "next_gate": "BLIND_G03_MECHANISM_RECOVERY_SEPARATELY_AUTHORIZED",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
