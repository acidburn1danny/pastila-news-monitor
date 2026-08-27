from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-liveness-candidate-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-liveness-candidate-v1-evidence/real-tokenizer-characterization.json"


def test_candidate_identity_and_implementation_hashes_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    identities = value["implementation_identities"]
    files = {
        "early_coverage_constraint_sha256": "stage_p_scope_graph_constraint_v1_2.py",
        "liveness_projector_sha256": "stage_p_liveness_trie_projector_v1.py",
        "liveness_controller_sha256": "stage_p_scope_graph_liveness_callback_controller_v1.py",
        "zero_inference_characterizer_sha256": "stage_p_scope_graph_liveness_zero_inference_v1.py",
    }
    for key, name in files.items():
        path = ROOT / "src/pastila_scout/semantic_admission_v2" / name
        assert identities[key] == hashlib.sha256(path.read_bytes()).hexdigest()
    evidence = json.loads(EVIDENCE.read_text("utf-8"))
    parts = [
        "STAGE_P_SCOPE_GRAPH_LIVENESS_CANDIDATE_V1", value["approved_design_identity"],
        identities["early_coverage_constraint_sha256"], identities["liveness_projector_sha256"],
        identities["liveness_controller_sha256"], evidence["run2_partial_sha256"],
        "ZERO_MODEL_ZERO_INFERENCE", "NOT_RUNNER_BOUND",
    ]
    assert value["candidate_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_real_tokenizer_evidence_is_zero_inference_and_track_b_is_untouched():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "PASS"
    assert evidence["baseline_coverage_choices"] == ["COMPLETE", "INDETERMINATE"]
    assert evidence["candidate_coverage_choices"] == ["COMPLETE"]
    for key in ("model_loads", "model_calls", "provider_calls", "inference_calls"):
        assert evidence[key] == 0
    assert value["boundaries"]["runner_bound"] is False
    assert value["boundaries"]["track_b_started"] is False
