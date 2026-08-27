from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-case01-run2-failure-analysis-v1.json"
RUN = ROOT / ".semantic-admission-v2-stage-p-scope-graph-v1-1-case01-probe-run-v2-evidence"


def test_design_identity_and_bound_run2_evidence_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    bound = value["bound_evidence"]
    for key, name in {
        "identity_binding_sha256": "identity-binding.json",
        "request_sha256": "stage-p-request.json",
        "phase_receipt_sha256": "stage-p-phase-receipt-v2.json",
    }.items():
        assert bound[key] == hashlib.sha256((RUN / name).read_bytes()).hexdigest()
    parts = [
        "STAGE_P_SCOPE_GRAPH_CASE01_RUN2_FAILURE_ANALYSIS_V1",
        bound["runner_binding_identity"],
        bound["executor_probe_binding_identity"],
        bound["phase_receipt_sha256"],
        "SEMANTIC_SCOPE_SELECTION_MISS",
        "CONSTRAINED_DECODING_LIVENESS_FAILURE",
        "PRESERVE_NULL_SUPPORT_UNSUPPORTED_PROPOSITIONS",
        "NO_IMPLEMENTATION_NO_INFERENCE",
    ]
    assert value["design_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_design_preserves_unsupported_proposition_path_and_separates_tracks():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    assert value["critical_non_remediation"]["rule"] == (
        "DO_NOT_GLOBALLY_PROHIBIT_REAL_WORLD_COMMITMENT_WITH_NULL_AUTHORITY_SUPPORT"
    )
    assert set(value["bounded_candidate_design"]) == {
        "track_a_constraint_liveness",
        "track_b_semantic_scope_selection",
    }
    assert "implementation" in value["out_of_scope"]
    assert "inference" in value["out_of_scope"]
