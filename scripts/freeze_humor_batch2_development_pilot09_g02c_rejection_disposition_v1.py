"""Freeze Pilot 09 as non-positive DEVELOPMENT G02C-rejection evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
G02C_COMMIT = "759b093214a0270bc0d849366fb4f919eb4c55b0"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot09-candidate01-v1.txt"
RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot09-candidate01-g02c-conformance-receipt-v5-1.json"
REVIEW_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot09-candidate01-g02c-review-v5-1.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot09-candidate01-g02c-rejection-disposition-v1.json"


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
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    require(head == G02C_COMMIT, "HEAD")
    candidate = git_bytes(CANDIDATE_PATH)
    receipt = git_json(RECEIPT_PATH)
    review = git_json(REVIEW_PATH)
    require(hashlib.sha256(candidate).hexdigest() == "3249775af5b93a68f00ab1e8217652a1411db03d61a40dfbe1e1fa3f7cd7e307", "candidate")
    require(hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest() == "fd1c7c024523faf63efe610849620364638a48b3", "candidate blob")
    require(receipt["verdict"] == "FAIL_INCOMPLETE_CAUSAL_SPINE", "verdict")
    require(receipt["failure"]["earliest_failed_link"] == "SELECTED_FACT_TO_FIRST_INVENTED_CONSEQUENCE", "failed link")
    require(receipt["conformance_receipt_identity"] == "a2ba3529a489e23a6c70b8405ab585eedd6158882132ad539d411a9f61e6f7e4", "receipt")
    require(review["g02c_review_identity"] == "79e86bd7dfc1684cf02128481e91993621b41b37dc5efa7dc639921f7d0b95f0", "review")
    require(review["eligibility"] == "NOT_ELIGIBLE_FOR_G03_OR_POSITIVE_POOL" and review["g03_eligibility"] is False, "eligibility")
    core = {
        "schema_name": "batch2-development-pilot09-g02c-rejection-disposition-v1",
        "schema_version": "1.0.0",
        "candidate_identity": review["candidate_identity"],
        "candidate_raw_sha256": review["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": receipt["candidate_git_blob_oid_sha1"],
        "creative_premise_family_id": review["creative_premise_family_id"],
        "creative_marker_family_id": review["creative_marker_family_id"],
        "g02c_commit": G02C_COMMIT,
        "g02c_verdict": receipt["verdict"],
        "earliest_failed_link": receipt["failure"]["earliest_failed_link"],
        "conformance_receipt_identity": receipt["conformance_receipt_identity"],
        "g02c_review_identity": review["g02c_review_identity"],
        "stable_rejection_reason": "SURFACE_ASSERTS_TWO_CONSEQUENCES_AND_A_COMPLETE_PATH_WITHOUT_INSTANTIATING_EITHER_CONSEQUENCE_ANY_LINK_OPERAND_OR_A_TERMINAL_RESULT",
        "typed_static_plan_status": "PRESERVED_BUT_INSUFFICIENT_AS_SURFACE_EVIDENCE",
        "disposition": "DEVELOPMENT_NONPOSITIVE_G02C_REJECTION_EVIDENCE",
        "partition": "DEVELOPMENT",
        "evidence_role": "NONPOSITIVE_OBLIGATION_CONFORMANCE_FAILURE",
        "positive_coverage_eligible": False,
        "g03_eligible": False,
        "romanian_naturalness_review_eligible": False,
        "voice_review_eligible": False,
        "g04b_pool_certification_eligible": False,
        "capability_state": "CONSUMED_1_OF_1_NO_FURTHER_CONSTRUCTION",
        "candidate_bytes_modified": False,
        "existing_identities_modified": False,
        "sealed_mapping_accessed": False,
        "visibility": "NON_MODEL_VISIBLE",
        "training_eligible": False,
        "runtime_eligible": False,
        "production_eligible": False,
        "permitted_future_source_only_diagnostics": [
            "CONSTRUCTOR_V5_1_PLAN_TO_SURFACE_REALIZATION_ROOT_CAUSE_ANALYSIS",
            "LINK_INSTANTIATION_STATIC_VALIDATION_ANALYSIS",
            "INSTRUCTION_LANGUAGE_TRANSFER_GOVERNANCE_ANALYSIS",
        ],
        "authority_matrix": {key: False for key in (
            "candidate_repair", "candidate_rewrite", "candidate_regeneration",
            "additional_construction_under_consumed_capability", "g03_mechanism_recovery",
            "romanian_naturalness_review", "voice_review", "g04b_pool_certification",
            "owner_positive_review", "model_exposure", "training", "runtime_integration",
            "production_routing",
        )},
    }
    disposition = {**core, "disposition_identity": seal("B2_DEVELOPMENT_PILOT09_G02C_REJECTION_DISPOSITION_V1", core)}
    OUTPUT.write_text(json.dumps(disposition, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"disposition": disposition["disposition"], "disposition_identity": disposition["disposition_identity"],
                      "next_action": "SOURCE_ONLY_CONSTRUCTOR_V5_1_PLAN_TO_SURFACE_ROOT_CAUSE_ANALYSIS_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
