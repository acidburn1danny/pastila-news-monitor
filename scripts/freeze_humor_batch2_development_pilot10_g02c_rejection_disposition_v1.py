"""Freeze Pilot 10 as non-positive DEVELOPMENT G02C-rejection evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
G02C_COMMIT = "874821daf9b9aeac6cc368468ea8ea68c620be4a"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-candidate01-v1.txt"
RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-candidate01-g02c-conformance-receipt-v5-2.json"
REVIEW_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-candidate01-g02c-review-v5-2.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot10-candidate01-g02c-rejection-disposition-v1.json"


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
    receipt, review = git_json(RECEIPT_PATH), git_json(REVIEW_PATH)
    require(hashlib.sha256(candidate).hexdigest() == "013c70e3c15833e789592915f5f31b62eeaed5c1148ff6b6f78607cb0c907464", "candidate")
    require(hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest() == "8dfbc43c94190e5b0fca48d6bcd28adf55c21391", "candidate blob")
    require(receipt["verdict"] == "FAIL_TERMINAL_EDGE_NON_ARBITRARY_CAUSAL_CONTINUITY", "verdict")
    require(receipt["failure"]["earliest_failed_link"] == "L2_TO_TERMINAL_RESULT", "failed link")
    require(receipt["conformance_receipt_identity"] == "b35eda9ac8e9ba4869a6d75683b8c8e2ac0cbd5e1f7db6a0f97279e65f07c0f6", "receipt")
    require(review["g02c_review_identity"] == "06e6c7b5d3d894af3155ca92dd4a83005c80df622cd9a8e6b6d24d89d0ac0238", "review")
    require(review["eligibility"] == "NOT_ELIGIBLE_FOR_G03_OR_POSITIVE_POOL" and review["g03_eligibility"] is False, "eligibility")
    require(receipt["required_predicates"]["EVERY_REQUIRED_CAUSAL_NODE_MATERIALLY_INSTANTIATED"] is True, "nodes")
    require(receipt["required_predicates"]["EVERY_REQUIRED_CAUSAL_EDGE_MATERIALLY_INSTANTIATED"] is True, "edges")
    require(receipt["independently_recovered_edges"]["L2_TO_RESULT"]["non_arbitrary"] is False, "semantic edge")
    core = {
        "schema_name": "batch2-development-pilot10-g02c-rejection-disposition-v1", "schema_version": "1.0.0",
        "candidate_identity": review["candidate_identity"], "candidate_raw_sha256": review["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": receipt["candidate_git_blob_oid_sha1"],
        "creative_premise_family_id": review["creative_premise_family_id"],
        "creative_marker_family_id": review["creative_marker_family_id"],
        "g02c_commit": G02C_COMMIT, "g02c_verdict": receipt["verdict"],
        "earliest_failed_link": receipt["failure"]["earliest_failed_link"],
        "conformance_receipt_identity": receipt["conformance_receipt_identity"],
        "g02c_review_identity": review["g02c_review_identity"],
        "stable_rejection_reason": "TERMINAL_EDGE_CHANGES_A_CLASSIFIED_NONHUMAN_PATIENT_INTO_AN_AGENTIVE_PROCEDURE_APPLIER_WITHOUT_A_PRODUCING_RULE",
        "material_realization": {"nodes": "3_OF_3", "edges": "2_OF_2", "terminal_result_witnesses": 1},
        "semantic_necessity": {"valid_necessary_edges": "2_OF_3", "failed_edge": "L2_TO_TERMINAL_RESULT",
                               "typed_operand_continuity": "FAIL_LEXICALLY_PRESENT_ROLE_INCOMPATIBLE"},
        "formal_pre_emission_conformance_status": "PRESERVED_BUT_INSUFFICIENT_AS_INDEPENDENT_SEMANTIC_CONFORMANCE_EVIDENCE",
        "placeholder_summary_meta_assertion_or_instruction_transfer": "ABSENT",
        "qualification_and_fictional_marking": "PASS",
        "disposition": "DEVELOPMENT_NONPOSITIVE_G02C_REJECTION_EVIDENCE",
        "partition": "DEVELOPMENT", "evidence_role": "NONPOSITIVE_OBLIGATION_CONFORMANCE_FAILURE",
        "positive_coverage_eligible": False, "g03_eligible": False,
        "romanian_naturalness_review_eligible": False, "voice_review_eligible": False,
        "g04b_pool_certification_eligible": False,
        "capability_state": "CONSUMED_1_OF_1_NO_FURTHER_CONSTRUCTION",
        "candidate_bytes_modified": False, "existing_identities_modified": False,
        "sealed_mapping_accessed": False, "visibility": "NON_MODEL_VISIBLE",
        "training_eligible": False, "runtime_eligible": False, "production_eligible": False,
        "permitted_future_source_only_diagnostics": [
            "CONSTRUCTOR_V5_2_SEMANTIC_EDGE_NECESSITY_ROOT_CAUSE_ANALYSIS",
            "TYPED_OPERAND_ROLE_CONTINUITY_VALIDATION_ANALYSIS",
            "NONHUMAN_AGENCY_AND_FORBIDDEN_OPERATION_PRE_EMISSION_GOVERNANCE_ANALYSIS",
        ],
        "authority_matrix": {key: False for key in (
            "candidate_repair", "candidate_rewrite", "candidate_regeneration", "candidate_retry",
            "additional_construction_under_consumed_capability", "g03_mechanism_recovery", "g03b", "g03c",
            "romanian_naturalness_review", "voice_review", "g04b_pool_certification", "owner_positive_review",
            "model_exposure", "training", "runtime_integration", "production_routing",
        )},
    }
    disposition = {**core, "disposition_identity": seal("B2_DEVELOPMENT_PILOT10_G02C_REJECTION_DISPOSITION_V1", core)}
    OUTPUT.write_text(json.dumps(disposition, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"disposition": disposition["disposition"], "disposition_identity": disposition["disposition_identity"],
                      "next_action": "SOURCE_ONLY_CONSTRUCTOR_V5_2_SEMANTIC_EDGE_AND_ROLE_CONTINUITY_ROOT_CAUSE_ANALYSIS_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
