from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-track-b-case01-probe-binding-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-track-b-case01-probe-binding-v1-evidence/preflight.json"


def test_binding_identity_and_probe_source_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    probe = ROOT / "src/pastila_scout/semantic_admission_v2/run_stage_p_scope_graph_track_b_case01_probe_v1.py"
    assert value["probe_runner_sha256"] == hashlib.sha256(probe.read_bytes()).hexdigest()
    parts = ["STAGE_P_SCOPE_GRAPH_TRACK_B_CASE01_PROBE_BINDING_V1",
             value["approved_evaluator_binding_identity"], value["probe_runner_sha256"], value["pack_sha256"],
             value["case_id"], "MAXIMUM_PROVIDER_CALLS_1", "NO_RETRY_REPAIR_SELECTION", "NO_STAGE_C",
             "NOT_EXECUTED"]
    assert value["binding_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_preflight_has_no_calls_and_no_execution_authority():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "PASS" and evidence["case01_executed"] is False
    assert evidence["case01_execution_authorized"] is False
    for key in ("wsl_calls", "runner_calls", "tokenizer_loads", "model_loads", "model_calls",
                "provider_calls", "inference_calls"):
        assert evidence[key] == 0
    assert value["authority"]["case01_execution"] is False
    assert value["authority"]["probe_execution"] is False
