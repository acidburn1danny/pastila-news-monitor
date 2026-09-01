"""Freeze Pilot 08 as non-positive DEVELOPMENT G02C-rejection evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
G02C_COMMIT = "e9fb6c5fab4e23141ef0d79efc1afb4f7ef6e6c9"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-candidate01-v1.txt"
RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-candidate01-g02c-conformance-receipt-v4.json"
REVIEW_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot08-candidate01-g02c-review-v4.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot08-candidate01-g02c-rejection-disposition-v1.json"


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
    require(hashlib.sha256(candidate).hexdigest() == "bc71da32026e9173440a494279fd4dca752cfc8c5547abcaa1ad922bdda0368a", "candidate")
    require(hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest() == "679ad8c85f55f002523657baf531587694f5f607", "candidate blob")
    require(receipt["verdict"] == "FAIL_UNBOUND_OPERAND_AND_INCOMPLETE_MULTI_LINK_CAUSAL_SPINE", "verdict")
    require(receipt["failure"]["earliest_failed_link"] == "FIRST_INVENTED_RELATION_TO_CONTROL_RETURN", "failed link")
    require(receipt["conformance_receipt_identity"] == "60fa16dd8d530ab34a1de89413bf3b37a16cf9b2536d981df0735a7812b1e733", "receipt")
    require(review["g02c_review_identity"] == "f87491eb48e08e8b3f1212857e97c2f619254fa1584a677b5b240218eada0583", "review")
    require(review["eligibility"] == "NOT_ELIGIBLE_FOR_G03_OR_POSITIVE_POOL", "eligibility")
    core = {
        "schema_name": "batch2-development-pilot08-g02c-rejection-disposition-v1",
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
        "stable_rejection_reason": "FIRST_DISTINCT_INVENTED_LINK_USES_A_PREPOSITIONAL_LOCATION_AS_THE_APPARENT_MOVER_WITHOUT_A_BOUND_ACTOR_OR_HEAD_SO_THE_MULTI_LINK_CHAIN_IS_NOT_LOCALLY_RECOVERABLE",
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
        "visibility": "NON_MODEL_VISIBLE",
        "training_eligible": False,
        "runtime_eligible": False,
        "production_eligible": False,
        "permitted_future_source_only_diagnostics": [
            "OPERAND_CLOSURE_ROOT_CAUSE_ANALYSIS",
            "CONSTRUCTOR_V4_COMPONENT_COMPOSITION_ANALYSIS",
            "OBLIGATION_CONFORMANCE_GOVERNANCE_ANALYSIS",
        ],
        "authority_matrix": {key: False for key in (
            "candidate_repair", "candidate_rewrite", "candidate_regeneration",
            "additional_construction_under_consumed_capability", "g03_mechanism_recovery",
            "romanian_naturalness_review", "voice_review", "g04b_pool_certification",
            "owner_positive_review", "model_exposure", "training", "runtime_integration",
            "production_routing",
        )},
    }
    disposition = {
        **core,
        "disposition_identity": seal("B2_DEVELOPMENT_PILOT08_G02C_REJECTION_DISPOSITION_V1", core),
    }
    OUTPUT.write_text(json.dumps(disposition, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({
        "disposition": disposition["disposition"],
        "disposition_identity": disposition["disposition_identity"],
        "next_action": "SOURCE_ONLY_OPERAND_CLOSURE_AND_CONSTRUCTOR_V4_ROOT_CAUSE_ANALYSIS_SEPARATELY_AUTHORIZED",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
