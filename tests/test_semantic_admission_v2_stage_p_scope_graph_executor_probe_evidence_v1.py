from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-executor-probe-binding-v1-candidate.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-executor-probe-binding-v1-evidence"


def test_implementation_hashes_are_exact():
    value = json.loads(CANDIDATE.read_text("utf-8"))["implementation_identities"]
    paths = {"executor_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_durable_executor_v1.py",
             "evaluator_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_evaluator_v1.py",
             "probe_runner_sha256": "src/pastila_scout/semantic_admission_v2/run_stage_p_scope_graph_case01_probe_v1.py"}
    for key, relative in paths.items():
        assert value[key] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def test_candidate_identity_binds_runner_implementations_and_pack():
    value = json.loads(CANDIDATE.read_text("utf-8"))
    identities = value["implementation_identities"]
    parts = ["STAGE_P_SCOPE_GRAPH_EXECUTOR_PROBE_BINDING_V1", value["approved_runner_binding_identity"],
             identities["executor_sha256"], identities["evaluator_sha256"], identities["probe_runner_sha256"],
             value["pack_sha256"]]
    assert value["candidate_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_preflight_has_no_calls_events_or_authority():
    value = json.loads(CANDIDATE.read_text("utf-8"))
    preflight = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    manifest = json.loads((EVIDENCE / "manifest.json").read_text("utf-8"))
    assert manifest["candidate_identity"] == preflight["candidate_identity"] == value["candidate_identity"]
    assert not any(value["authority"].values())
    assert preflight["result"] == "PASS" and preflight["maximum_provider_calls"] == 1
    for key in ("durable_lifecycle_events", "wsl_calls", "runner_calls", "tokenizer_loads", "model_loads",
                "model_calls", "provider_calls"):
        assert preflight[key] == 0
    assert preflight["inference_executed"] is False
