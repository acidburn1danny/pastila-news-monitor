from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_track_b_request_candidate_v1 import (
    StagePScopeGraphTrackBRequestCandidateV1,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-track-b-prompt-contract-candidate-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-track-b-prompt-contract-candidate-v1-evidence/preflight.json"


def test_candidate_and_source_identities_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8")); ids = value["identities"]
    candidate = StagePScopeGraphTrackBRequestCandidateV1(project_root=ROOT)
    assert value["candidate_identity"] == candidate.candidate_identity
    files = {
        "prompt_file_sha256": "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-track-b-prompt-v1.txt",
        "prompt_contract_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_track_b_prompt_v1.py",
        "request_candidate_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_track_b_request_candidate_v1.py",
        "zero_inference_preflight_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_track_b_zero_inference_v1.py",
    }
    for key, relative in files.items():
        assert ids[key] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def test_preflight_is_zero_inference_and_case_remains_blocked():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "PASS" and evidence["candidate_first"] is True
    assert evidence["case01_executed"] is False and evidence["case01_blocked"] is True
    for key in ("model_loads", "model_calls", "provider_calls", "inference_calls"):
        assert evidence[key] == 0
    assert value["authority"]["case01"] is False and value["authority"]["probe"] is False
