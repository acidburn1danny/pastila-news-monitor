from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-baseline-language-runner-executor-binding-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-baseline-language-runner-executor-binding-v1-evidence/preflight.json"


def test_binding_identity_and_sources_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    ids = value["identities"]
    files = {
        "runner_sha256": "src/pastila_scout/experimental_core_v1_2_stage_p_scope_graph_runner_v1_3.py",
        "executor_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_durable_executor_v1_3.py",
        "diagnostic_projector_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_diagnostic_trie_projector_v1.py",
        "diagnostic_controller_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_diagnostic_callback_controller_v1.py",
    }
    for key, relative in files.items():
        assert ids[key] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    parts = [value["artifact_id"], value["approved_adapter_identity"], ids["runner_sha256"],
             ids["executor_sha256"], "ZERO_INFERENCE", "CASE01_BLOCKED", "NOT_PROBE_BOUND"]
    assert value["binding_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_preflight_is_zero_inference_and_case01_remains_blocked():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "PASS" and evidence["case01_blocked"] is True
    assert evidence["probe_bound"] is False
    for key in ("runner_calls", "tokenizer_loads", "model_loads", "model_calls", "provider_calls", "inference_calls"):
        assert evidence[key] == 0
    assert value["authority"]["case01"] is False and value["authority"]["probe"] is False
