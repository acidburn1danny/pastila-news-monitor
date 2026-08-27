from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-track-b-semantic-scope-selection-design-v1.json"


def test_design_identity_and_upstream_bindings_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    parts = ["STAGE_P_SCOPE_GRAPH_TRACK_B_SEMANTIC_SCOPE_SELECTION_DESIGN_V1",
             value["source_failure_analysis_identity"], value["track_a_durable_binding_identity"],
             "CANDIDATE_FIRST_AUTHORITY_SECOND", "NEUTRALIZATION_SURVIVAL",
             "AUTHORITY_NOT_SEMANTIC_SOURCE", "PRESERVE_UNSUPPORTED_REAL_WORLD",
             "NO_SINGLE_SEGMENTATION", "NO_IMPLEMENTATION_NO_INFERENCE", "CASE01_BLOCKED"]
    assert value["design_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()
    case = value["case01_acceptance_contract"]
    request = ROOT / ".semantic-admission-v2-stage-p-scope-graph-v1-1-case01-probe-run-v2-evidence/stage-p-request.json"
    assert case["request_sha256"] == hashlib.sha256(request.read_bytes()).hexdigest()


def test_design_preserves_both_creative_containment_and_unsupported_recall():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    names = {item["name"] for item in value["governing_principles"]}
    assert "CREATIVE_HEAD_DOES_NOT_SHIELD_FACTUAL_RETURN" in names
    assert "NO_FORCED_CREATIVITY_OR_SINGLE_SEGMENTATION" in names
    classes = {item["class"] for item in value["contrastive_acceptance_matrix"]}
    assert {"INTEGRATED_CREATIVE_ONLY", "UNSUPPORTED_SURVIVING_PROPOSITION",
            "MIXED_CREATIVE_AND_UNSUPPORTED_RETURN", "GENUINELY_AMBIGUOUS_SCOPE"} <= classes


def test_design_is_non_executable_and_case01_remains_blocked():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    assert value["lifecycle"] == "DESIGN_ONLY_NOT_IMPLEMENTED_NOT_EXECUTED_CASE01_BLOCKED"
    assert "prompt implementation" in value["out_of_scope"]
    assert "inference" in value["out_of_scope"]
    assert "Case 01 execution" in value["out_of_scope"]
