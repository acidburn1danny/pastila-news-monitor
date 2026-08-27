from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-baseline-language-diagnostic-adapter-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-baseline-language-diagnostic-adapter-v1-evidence/real-tokenizer-timing.json"


def test_candidate_identity_and_implementation_hashes_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8")); ids = value["identities"]
    files = {
        "diagnostic_projector_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_diagnostic_trie_projector_v1.py",
        "diagnostic_controller_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_diagnostic_callback_controller_v1.py",
        "zero_inference_profiler_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_diagnostic_projector_zero_inference_v1.py",
    }
    for key, relative in files.items():
        assert ids[key] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    parts = ["STAGE_P_BASELINE_LANGUAGE_DIAGNOSTIC_ADAPTER_V1",
             value["approved_performance_design_identity"], ids["diagnostic_projector_sha256"],
             ids["diagnostic_controller_sha256"], ids["zero_inference_profiler_sha256"],
             "ALLOWED_SET_EQUIVALENT", "REAL_TOKENIZER_11_STATES_PASS", "NO_MODEL_NO_INFERENCE",
             "CASE01_BLOCKED", "NOT_RUNNER_BOUND"]
    assert value["candidate_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_real_tokenizer_evidence_meets_all_frozen_budgets():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "PASS" and evidence["allowed_set_equivalence"] is True
    assert all(row["sets_equal"] for row in evidence["states"])
    assert evidence["maximum_candidate_cold_seconds"] <= 5
    assert evidence["candidate_matrix_seconds"] <= 30
    assert evidence["warm_p95_seconds"] <= .25
    assert evidence["candidate_to_baseline_median_ratio"] <= 1.25
    for key in ("model_loads", "model_calls", "provider_calls", "inference_calls"):
        assert evidence[key] == 0
    assert value["authority"]["runner_binding"] is False
    assert value["authority"]["case01_execution"] is False
