from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-track-b-baseline-language-evaluator-rebinding-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-track-b-baseline-language-evaluator-rebinding-v1-evidence/preflight.json"


def test_binding_identity_and_sources_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8")); ids = value["identities"]
    files = {
        "evaluator_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_track_b_evaluator_v1_1.py",
        "executor_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_durable_executor_v1_3.py",
    }
    for key, relative in files.items():
        assert ids[key] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    parts = [value["artifact_id"], value["approved_request_candidate_identity"],
             value["approved_runner_executor_binding_identity"], ids["evaluator_sha256"],
             ids["executor_sha256"], ids["model_identity"], "240.0", "ZERO_INFERENCE",
             "CASE01_BLOCKED", "NOT_PROBE_BOUND"]
    assert value["binding_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_preflight_has_no_execution_edge_or_calls():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "PASS" and evidence["case01_blocked"] is True
    assert evidence["probe_wrapper_created"] is False and evidence["stage_c_edge"] is False
    for key in ("wsl_calls", "runner_calls", "tokenizer_loads", "model_loads", "model_calls",
                "provider_calls", "inference_calls"):
        assert evidence[key] == 0
    assert value["authority"]["case01"] is False and value["authority"]["probe"] is False
