from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-v1-1-executor-probe-binding-candidate.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-v1-1-executor-probe-binding-evidence"


def test_implementation_hashes_and_candidate_identity_are_exact():
    value = json.loads(CANDIDATE.read_text("utf-8")); identities = value["implementation_identities"]
    paths = {"executor_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_durable_executor_v1_1.py",
             "evaluator_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_evaluator_v1_1.py",
             "probe_runner_sha256": "src/pastila_scout/semantic_admission_v2/run_stage_p_scope_graph_case01_probe_v1_1.py"}
    for key, relative in paths.items():
        assert identities[key] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    parts = ["STAGE_P_SCOPE_GRAPH_EXECUTOR_PROBE_BINDING_V1_1", value["approved_runner_binding_identity"],
             identities["executor_sha256"], identities["evaluator_sha256"], identities["probe_runner_sha256"],
             value["pack_sha256"]]
    assert value["candidate_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_preflight_has_no_calls_events_or_authority():
    value = json.loads(CANDIDATE.read_text("utf-8")); preflight = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    assert preflight["candidate_identity"] == value["candidate_identity"] and not any(value["authority"].values())
    assert preflight["maximum_provider_calls"] == 1 and preflight["inference_executed"] is False
    for key in ("durable_lifecycle_events", "wsl_calls", "runner_calls", "tokenizer_loads", "model_loads",
                "model_calls", "provider_calls"):
        assert preflight[key] == 0
