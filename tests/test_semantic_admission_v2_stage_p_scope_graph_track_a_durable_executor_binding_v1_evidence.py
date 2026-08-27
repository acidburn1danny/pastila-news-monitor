from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-track-a-durable-executor-binding-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-track-a-durable-executor-binding-v1-evidence/preflight.json"


def test_binding_identity_and_sources_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8")); ids = value["identities"]
    files = {
        "executor_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_durable_executor_v1_2.py",
        "runner_sha256": "src/pastila_scout/experimental_core_v1_2_stage_p_scope_graph_runner_v1_2.py",
        "reconciliation_sha256": "src/pastila_scout/semantic_admission_v2/durable_lifecycle_reconciliation_v1.py",
        "append_only_lifecycle_sha256": "src/pastila_scout/semantic_admission_v2/append_only_lifecycle_v1.py",
    }
    for key, relative in files.items():
        assert ids[key] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    parts = ["STAGE_P_SCOPE_GRAPH_TRACK_A_DURABLE_EXECUTOR_BINDING_V1",
             value["approved_runner_binding_identity"], ids["executor_sha256"], ids["runner_sha256"],
             ids["reconciliation_sha256"], "CONSTRAINT_LIVENESS_FAILURE_DISTINCT",
             "PARTIAL_HASH_AND_LENGTH_PRESERVED", "ZERO_INFERENCE", "CASE01_BLOCKED"]
    assert value["binding_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_evidence_has_no_calls_and_preserves_case_block():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "PASS" and evidence["case01_blocked"] is True
    for key in ("runner_calls", "tokenizer_loads", "model_loads", "model_calls", "provider_calls", "inference_calls"):
        assert evidence[key] == 0
    assert value["authority"]["case01"] is False and value["authority"]["probe"] is False
