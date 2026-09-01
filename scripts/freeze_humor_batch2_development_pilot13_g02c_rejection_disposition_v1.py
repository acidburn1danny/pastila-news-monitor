"""Freeze Pilot 13 as non-positive DEVELOPMENT G02C-rejection evidence."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
G02C_COMMIT = "cb98b42c6326061cf2805a8f446c511129d39246"
CANDIDATE_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-candidate01-v1.txt"
RECEIPT_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-candidate01-g02c-conformance-receipt-v5-3-3.json"
REVIEW_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-candidate01-g02c-review-v5-3-3.json"
OUTPUT = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot13-candidate01-g02c-rejection-disposition-v1.json"


def git_bytes(path):
    return subprocess.check_output(["git", "show", f"{G02C_COMMIT}:{path}"], cwd=ROOT)


def git_json(path):
    return json.loads(git_bytes(path))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def require(value, message):
    if not value:
        raise SystemExit(message)


def main():
    require(not OUTPUT.exists(), "disposition already frozen")
    require(subprocess.run(["git", "merge-base", "--is-ancestor", G02C_COMMIT, "HEAD"], cwd=ROOT).returncode == 0, "G02C commit")
    candidate = git_bytes(CANDIDATE_PATH)
    receipt, review = git_json(RECEIPT_PATH), git_json(REVIEW_PATH)
    require(hashlib.sha256(candidate).hexdigest() == "907392cd76554340b09ef27145256b45f3c1ae013f41f4e4503ea156dc546759", "candidate")
    require(hashlib.sha1(b"blob " + str(len(candidate)).encode() + b"\0" + candidate).hexdigest() == "9a643cff281455ee0b4c9772f9740175ab27753b", "candidate blob")
    require(receipt["verdict"] == "FAIL_FIRST_INVENTED_LINK_ROLE_AFFORDANCE_AND_CAUSAL_NECESSITY", "verdict")
    require(receipt["failure"]["earliest_failed_link"] == "P5_TO_L1", "failed link")
    require(receipt["conformance_receipt_identity"] == "c4a51b9a8f982a6de9911907af4c8b21ab85b942858a1742755e50a26c7cc5f1", "receipt")
    require(review["g02c_review_identity"] == "363eaedb8276532f67761f39ae9272a0462cdad21ea0c39bf95e1c7c27c55f3f", "review")
    require(review["g03_eligibility"] is False and review["disposition"] == "G02C_REJECTED_STOP_NO_REPAIR", "eligibility")
    require(receipt["required_predicates"]["EVERY_REQUIRED_NODE_MATERIALLY_INSTANTIATED"] is True, "nodes")
    require(receipt["required_predicates"]["EVERY_REQUIRED_EDGE_MATERIALLY_INSTANTIATED"] is True, "edges")
    core = {
        "schema_name": "batch2-development-pilot13-g02c-rejection-disposition-v1", "schema_version": "1.0.0",
        "candidate_identity": review["candidate_identity"], "candidate_raw_sha256": review["candidate_raw_sha256"],
        "candidate_git_blob_oid_sha1": receipt["candidate_git_blob_oid_sha1"],
        "g02c_commit": G02C_COMMIT, "g02c_verdict": receipt["verdict"],
        "earliest_failed_link": receipt["failure"]["earliest_failed_link"],
        "conformance_receipt_identity": receipt["conformance_receipt_identity"],
        "g02c_review_identity": review["g02c_review_identity"],
        "stable_rejection_reason": "FIRST_INVENTED_LINK_MATERIALLY_PRESENT_BUT_FACT_ACTOR_TEMPORAL_PATIENT_AND_ELIGIBILITY_OUTPUT_LACK_ROLE_AFFORDANCE_AND_CAUSAL_LICENSE",
        "material_realization": {"nodes": "3_OF_3", "planned_edges": "2_OF_2", "anchor_to_first_link": "PRESENT", "terminal_result_witnesses": 1},
        "semantic_conformance": {"role_affordance_compatible_links": "0_OF_3", "necessary_nonarbitrary_links": "0_OF_3",
            "failed_first_link": "P5_TO_L1", "downstream_failures": ["L1_TO_L2", "L2_TO_TERMINAL"]},
        "formal_pre_emission_conformance_status": "PRESERVED_AS_PROVENANCE_BUT_INSUFFICIENT_AS_INDEPENDENT_G02C_PROOF",
        "placeholder_summary_meta_assertion_or_instruction_transfer": "ABSENT",
        "qualification_and_fictional_marking": "PASS", "candidate_level_failure_not_infrastructure_defect": True,
        "disposition": "DEVELOPMENT_NONPOSITIVE_G02C_REJECTION_EVIDENCE", "partition": "DEVELOPMENT",
        "evidence_role": "NONPOSITIVE_OBLIGATION_CONFORMANCE_FAILURE", "positive_coverage_eligible": False,
        "g03_eligible": False, "romanian_naturalness_review_eligible": False, "voice_review_eligible": False,
        "g04b_pool_certification_eligible": False, "capability_state": "CONSUMED_1_OF_1_NO_FURTHER_CONSTRUCTION",
        "candidate_bytes_modified": False, "existing_identities_modified": False, "sealed_mapping_accessed": False,
        "visibility": "NON_MODEL_VISIBLE", "training_eligible": False, "runtime_eligible": False, "production_eligible": False,
        "permitted_future_source_only_diagnostics": [
            "V5_3_3_FIRST_LINK_ROLE_AFFORDANCE_AND_CAUSAL_NECESSITY_ROOT_CAUSE_ANALYSIS",
            "PREEMISSION_MATERIAL_PRESENCE_VERSUS_SEMANTIC_EXECUTABILITY_ANALYSIS",
        ],
        "authority_matrix": {key: False for key in ("candidate_repair", "candidate_rewrite", "candidate_regeneration",
            "candidate_retry", "additional_construction_under_consumed_capability", "g03_mechanism_recovery", "g03b",
            "g03c", "romanian_naturalness_review", "voice_review", "g04b_pool_certification", "owner_positive_review",
            "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    disposition = {**core, "disposition_identity": seal("B2_DEVELOPMENT_PILOT13_G02C_REJECTION_DISPOSITION_V1", core)}
    OUTPUT.write_text(json.dumps(disposition, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"disposition": disposition["disposition"], "disposition_identity": disposition["disposition_identity"],
                      "next_action": "SOURCE_ONLY_V5_3_3_FIRST_LINK_ROLE_AFFORDANCE_AND_CAUSAL_NECESSITY_ROOT_CAUSE_ANALYSIS_SEPARATELY_AUTHORIZED"}, sort_keys=True))


if __name__ == "__main__":
    main()
