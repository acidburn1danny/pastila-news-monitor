from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-case01-baseline-language-false-complete-analysis-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-case01-baseline-language-false-complete-analysis-v1-evidence/review.json"
RUN = ROOT / ".semantic-admission-v2-stage-p-track-b-baseline-language-case01-probe-run-v1-evidence"


def test_design_identity_and_bound_evidence_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8")); bound = value["bound_evidence"]
    files = {
        "request_sha256": "stage-p-request.json",
        "raw_sha256": "stage-p-raw.bin",
        "phase_receipt_sha256": "stage-p-phase-receipt-v2.json",
        "identity_binding_sha256": "identity-binding.json",
    }
    for key, name in files.items():
        assert bound[key] == hashlib.sha256((RUN / name).read_bytes()).hexdigest()
    parts = [value["artifact_id"], bound["probe_binding_identity"], bound["raw_sha256"],
             "STAGE_P_VALID_CONTRACT", "FALSE_COMPLETE_SEMANTIC",
             "CONTAINED_CREATIVE_OVER_COLLAPSE", "NO_STAGE_C", "DESIGN_ONLY"]
    assert value["design_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_review_blocks_stage_c_and_authorizes_no_changes_or_calls():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "FAIL_FALSE_COMPLETE"
    assert evidence["semantic_exhaustiveness_valid"] is False
    assert evidence["stage_c_eligible"] is False
    assert value["owner_evaluation"]["stage_c_eligible"] is False
    assert all(flag is False for flag in value["boundaries"].values())
    for key in ("model_calls_during_review", "provider_calls_during_review",
                "inference_calls_during_review", "stage_c_calls"):
        assert evidence[key] == 0


def test_remediation_preserves_factual_and_creative_boundaries():
    value = json.loads(ARTIFACT.read_text("utf-8")); design = value["bounded_remediation_design"]
    requirements = "\n".join(design["requirements"])
    assert "do not force every metaphorical target" in requirements
    assert "UNRESOLVED_SCOPE and INDETERMINATE" in requirements
    assert design["case01_acceptance_contract"]["single_correct_segmentation"] is False
    assert design["case01_acceptance_contract"]["unsupported_real_world_commitments"] == 0
