from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-track-a-runner-binding-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-track-a-runner-binding-v1-evidence/preflight.json"


def test_binding_identity_and_sources_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    ids = value["identities"]
    files = {
        "runner_sha256": "src/pastila_scout/experimental_core_v1_2_stage_p_scope_graph_runner_v1_2.py",
        "constraint_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_constraint_v1_2.py",
        "projector_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_liveness_trie_projector_v1.py",
        "tracker_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_incremental_tracker_v1_2.py",
        "controller_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_liveness_callback_controller_v1_2.py",
    }
    for key, relative in files.items():
        assert ids[key] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    parts = ["STAGE_P_SCOPE_GRAPH_TRACK_A_RUNNER_BINDING_V1", value["approved_candidate_identity"],
             ids["runner_sha256"], ids["constraint_sha256"], ids["projector_sha256"],
             ids["tracker_sha256"], ids["controller_sha256"], "ZERO_INFERENCE", "CASE01_BLOCKED"]
    assert value["binding_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_preflight_preserves_block_and_has_no_model_activity():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "PASS" and evidence["case01_blocked"] is True
    for key in ("model_loads", "model_calls", "provider_calls", "inference_calls"):
        assert evidence[key] == 0
    assert value["authority"]["case01"] is False
    assert value["authority"]["probe"] is False
