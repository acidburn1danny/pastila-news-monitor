from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-case01-real-world-escape-owner-review-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-case01-real-world-escape-owner-review-v1-evidence/review.json"
RUN = ROOT / ".semantic-admission-v2-stage-p-creative-target-case01-probe-run-v1-evidence"


def test_review_identity_and_bound_evidence_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8")); bound = value["bound_evidence"]
    files = {"request_sha256": "stage-p-request.json", "raw_sha256": "stage-p-raw.bin",
        "phase_receipt_sha256": "stage-p-phase-receipt-v2.json", "identity_binding_sha256": "identity-binding.json"}
    for key, name in files.items(): assert bound[key] == hashlib.sha256((RUN / name).read_bytes()).hexdigest()
    parts = [value["artifact_id"], bound["probe_binding_identity"], bound["raw_sha256"],
        "FAIL_FALSE_COMPLETE", "REAL_WORLD_COMMITMENT_ESCAPE_FROM_TARGET_AUDIT",
        "NO_REMEDIATION", "NO_RERUN", "NO_STAGE_C"]
    assert value["review_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_review_rejects_semantic_complete_and_blocks_stage_c():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "FAIL_FALSE_COMPLETE"
    assert evidence["failure_class"] == "REAL_WORLD_COMMITMENT_ESCAPE_FROM_TARGET_AUDIT"
    assert evidence["semantic_exhaustiveness_valid"] is evidence["coverage_complete_credible"] is False
    assert evidence["stage_c_eligible"] is False and value["owner_decision"]["stage_c_eligible"] is False
    assert all(flag is False for flag in value["boundaries"].values())


def test_review_performed_no_execution_or_remediation():
    evidence = json.loads(EVIDENCE.read_text("utf-8"))
    for key in ("model_calls_during_review", "provider_calls_during_review", "inference_calls_during_review",
                "case01_reruns", "stage_c_calls"):
        assert evidence[key] == 0
