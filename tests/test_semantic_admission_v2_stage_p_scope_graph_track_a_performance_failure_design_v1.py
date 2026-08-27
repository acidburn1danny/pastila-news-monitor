from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-track-a-lookahead-performance-failure-design-v1.json"
RUN = ROOT / ".semantic-admission-v2-stage-p-scope-graph-track-b-case01-probe-run-v1-evidence"


def test_design_identity_and_timeout_evidence_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = value["source_run_evidence"]
    assert evidence["identity_binding_sha256"] == hashlib.sha256((RUN / "identity-binding.json").read_bytes()).hexdigest()
    assert evidence["phase_receipt_sha256"] == hashlib.sha256((RUN / "stage-p-phase-receipt-v2.json").read_bytes()).hexdigest()
    parts = ["STAGE_P_SCOPE_GRAPH_TRACK_A_LOOKAHEAD_PERFORMANCE_FAILURE_DESIGN_V1",
             value["source_probe_binding_identity"], evidence["identity_binding_sha256"],
             evidence["phase_receipt_sha256"], "HOST_TIMEOUT_AFTER_31_TOKENS", "REMOVE_BROAD_LOOKAHEAD",
             "PRESERVE_V1_2_EARLY_COVERAGE", "BASELINE_LANGUAGE_PROJECTOR",
             "INDEPENDENT_LIVENESS_RECEIPT", "NO_TIMEOUT_INCREASE", "NO_IMPLEMENTATION_NO_INFERENCE",
             "CASE01_BLOCKED"]
    assert value["design_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_design_preserves_language_and_rejects_timeout_masking():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    assert "exactly" in value["acceptance_requirements"]["allowed_set_equivalence"]
    assert any("Do not increase" in item for item in value["explicit_non_remediations"])
    assert "StagePScopeGraphConstraintStateV1_2" in value["required_remediation"]["preserve"][0]
    assert "Case 01 rerun" in value["out_of_scope"]


def test_partial_semantic_selection_is_not_promoted_to_result():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    boundary = value["semantic_observation_boundary"]
    assert boundary["status"] == "PROMISING_BUT_NOT_ADJUDICABLE"
    assert value["lifecycle"] == "DESIGN_ONLY_NOT_IMPLEMENTED_NOT_EXECUTED_CASE01_BLOCKED"
