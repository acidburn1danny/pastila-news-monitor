"""Freeze Pilot 05 as non-positive DEVELOPMENT G02C-rejection evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
G02C_COMMIT = "418b83213bde467396292c01dc497c45bdfd6809"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot05-candidate01-v1.txt"
RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot05-candidate01-g02c-conformance-receipt-v1.json"
REVIEW_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot05-candidate01-g02c-review-v1.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot05-candidate01-g02c-rejection-disposition-v1.json"


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{G02C_COMMIT}:{path}"], cwd=ROOT)


def git_json(path: str) -> dict[str, Any]:
    return json.loads(git_bytes(path))


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    require(not OUTPUT.exists(), "disposition already frozen")
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == G02C_COMMIT, "HEAD")
    candidate = git_bytes(CANDIDATE_PATH)
    receipt = git_json(RECEIPT_PATH)
    review = git_json(REVIEW_PATH)
    require(hashlib.sha256(candidate).hexdigest() == "8030222614461de66246eb9f2a14d1230e271b327007092f30f216f55a0d7166", "candidate")
    require(receipt["verdict"] == "FAIL_INCOMPLETE_RECOVERABLE_REVERSE_DEPENDENCY", "verdict")
    require(receipt["failure"]["earliest_failed_link"] == "STEP2_TO_SELECTED_FACTUAL_RELATION", "failed link")
    require(receipt["conformance_receipt_identity"] == "90d60b54f043f11efef7b3ca69b7ea1c3a1b8356003d4d1c95f4a57b0fe9201e", "receipt")
    require(review["g02c_review_identity"] == "d2da8e5b1c79afbb32810c015df480f8647a25162fe12425852ad839ca331ef3", "review")
    require(review["eligibility"] == "NOT_ELIGIBLE_FOR_G03_OR_POSITIVE_POOL", "eligibility")
    core = {
        "schema_name": "batch2-development-pilot05-g02c-rejection-disposition-v1", "schema_version": "1.0.0",
        "candidate_identity": review["candidate_identity"], "candidate_raw_sha256": review["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": receipt["candidate_git_blob_oid_sha1"],
        "creative_premise_family_id": review["creative_premise_family_id"],
        "g02c_commit": G02C_COMMIT, "g02c_verdict": receipt["verdict"],
        "earliest_failed_link": receipt["failure"]["earliest_failed_link"],
        "conformance_receipt_identity": receipt["conformance_receipt_identity"],
        "g02c_review_identity": review["g02c_review_identity"],
        "stable_rejection_reason": "SELECTED_P3_DOES_NOT_SUPPLY_A_NUMERIC_REFERENCE_OR_RELATION_FROM_WHICH_THE_INVENTED_0_1_DIFFERENCE_IS_RECOVERABLE",
        "disposition": "DEVELOPMENT_NONPOSITIVE_G02C_REJECTION_EVIDENCE",
        "partition": "DEVELOPMENT", "evidence_role": "NONPOSITIVE_OBLIGATION_CONFORMANCE_FAILURE",
        "positive_coverage_eligible": False, "g03_eligible": False, "g04b_pool_certification_eligible": False,
        "capability_state": "CONSUMED_1_OF_1_NO_FURTHER_CONSTRUCTION",
        "candidate_bytes_modified": False, "existing_identities_modified": False,
        "visibility": "NON_MODEL_VISIBLE", "training_eligible": False, "runtime_eligible": False,
        "production_eligible": False,
        "permitted_future_source_only_diagnostics": [
            "REVERSE_DEPENDENCY_OBLIGATION_ROOT_CAUSE_ANALYSIS",
            "SELECTED_PROPOSITION_SUFFICIENCY_ANALYSIS",
            "REBALANCING_ASSIGNMENT_GOVERNANCE_ANALYSIS",
        ],
        "authority_matrix": {key: False for key in (
            "candidate_repair", "candidate_rewrite", "candidate_regeneration", "additional_construction_under_consumed_capability",
            "g03_mechanism_recovery", "g04b_pool_certification", "owner_positive_review", "model_exposure", "training",
            "runtime_integration", "production_routing")},
    }
    disposition = {**core, "disposition_identity": seal("B2_DEVELOPMENT_PILOT05_G02C_REJECTION_DISPOSITION_V1", core)}
    OUTPUT.write_text(json.dumps(disposition, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"disposition": disposition["disposition"], "disposition_identity": disposition["disposition_identity"],
                      "next_action": "SOURCE_ONLY_REVERSE_DEPENDENCY_ROOT_CAUSE_ANALYSIS_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
