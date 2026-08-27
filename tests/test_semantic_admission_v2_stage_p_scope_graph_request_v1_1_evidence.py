from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_request_candidate_v1_1 import StagePScopeGraphRequestCandidateV1_1


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-v1-1-request-candidate.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-v1-1-request-evidence"


def test_artifact_matches_constructed_candidate_and_manifest():
    value = json.loads(CANDIDATE.read_text("utf-8")); constructed = StagePScopeGraphRequestCandidateV1_1(project_root=ROOT)
    assert value["candidate_identity"] == constructed.candidate_identity
    for key in ("prompt_identity", "schema_identity", "grammar_identity", "tokenizer_identity"):
        assert value[key] == getattr(constructed, key)
    manifest = json.loads((EVIDENCE / "manifest.json").read_text("utf-8"))
    assert manifest["candidate_identity"] == value["candidate_identity"]


def test_source_hash_and_zero_inference_are_exact():
    value = json.loads(CANDIDATE.read_text("utf-8"))
    source = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_request_candidate_v1_1.py"
    assert value["candidate_source_identity"] == "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    preflight = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    assert not any(value["authority"].values()) and preflight["requests_executed"] == 0
    assert preflight["inference_executed"] is False
    for key in ("runner_calls", "model_loads", "model_calls", "provider_calls"):
        assert preflight[key] == 0
