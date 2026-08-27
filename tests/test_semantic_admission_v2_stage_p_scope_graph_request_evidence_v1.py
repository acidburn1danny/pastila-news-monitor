from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_request_candidate_v1 import StagePScopeGraphRequestCandidateV1


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-request-v1-candidate.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-request-v1-evidence"


def test_artifact_identity_matches_constructed_candidate():
    artifact = json.loads(CANDIDATE.read_text("utf-8"))
    constructed = StagePScopeGraphRequestCandidateV1(project_root=ROOT)
    assert artifact["candidate_identity"] == constructed.candidate_identity
    assert artifact["prompt_identity"] == constructed.prompt_identity
    assert artifact["schema_identity"] == constructed.schema_identity
    assert artifact["grammar_identity"] == constructed.grammar_identity
    assert artifact["tokenizer_identity"] == constructed.tokenizer_identity


def test_source_hash_and_manifest_are_current():
    artifact = json.loads(CANDIDATE.read_text("utf-8"))
    manifest = json.loads((EVIDENCE / "manifest.json").read_text("utf-8"))
    source = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_request_candidate_v1.py"
    identity = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    assert artifact["candidate_source_identity"] == manifest["candidate_source_identity"] == identity
    assert manifest["candidate_identity"] == artifact["candidate_identity"]


def test_evidence_is_zero_inference_and_no_runner_authority_exists():
    artifact = json.loads(CANDIDATE.read_text("utf-8"))
    preflight = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    assert not any(artifact["authority"].values())
    assert preflight["requests_constructed"] > 0 and preflight["requests_executed"] == 0
    assert preflight["inference_executed"] is False
    for key in ("model_loads", "model_calls", "provider_calls", "runner_calls"):
        assert preflight[key] == 0
