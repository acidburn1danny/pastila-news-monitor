from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-runner-binding-v1-candidate.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-runner-binding-v1-evidence"


def test_runner_dependency_hashes_are_exact():
    binding = json.loads(CANDIDATE.read_text("utf-8"))["runner_binding"]
    paths = {"runner_sha256": "src/pastila_scout/experimental_core_v1_2_stage_p_scope_graph_runner_v1.py",
             "durable_base_runner_sha256": "src/pastila_scout/experimental_core_v1_2_stage_p_constrained_runner_v3.py",
             "constraint_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_constraint_v1.py",
             "trie_projector_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_trie_projector_v1.py",
             "incremental_tracker_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_incremental_tracker_v1.py",
             "callback_controller_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_callback_controller_v1.py",
             "append_only_lifecycle_sha256": "src/pastila_scout/semantic_admission_v2/append_only_lifecycle_v1.py"}
    for key, relative in paths.items():
        assert binding[key] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def test_candidate_identity_is_exact_dependency_binding():
    value = json.loads(CANDIDATE.read_text("utf-8"))
    binding = value["runner_binding"]
    parts = ["STAGE_P_SCOPE_GRAPH_RUNNER_BINDING_V1", value["approved_request_candidate_identity"],
             binding["runner_sha256"], binding["durable_base_runner_sha256"], binding["constraint_sha256"],
             binding["trie_projector_sha256"], binding["incremental_tracker_sha256"],
             binding["callback_controller_sha256"], binding["append_only_lifecycle_sha256"]]
    assert value["candidate_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_binding_was_not_executed_and_grants_no_authority():
    value = json.loads(CANDIDATE.read_text("utf-8"))
    preflight = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    manifest = json.loads((EVIDENCE / "manifest.json").read_text("utf-8"))
    assert value["runner_binding"]["execution_status"] == "NOT_EXECUTED"
    assert not any(value["authority"].values())
    assert manifest["candidate_identity"] == preflight["candidate_identity"] == value["candidate_identity"]
    for key in ("runner_calls", "model_loads", "model_calls", "provider_calls"):
        assert preflight[key] == 0
    assert preflight["inference_executed"] is False
