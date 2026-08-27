from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-role-receipt-propagation-candidate-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-construction-role-receipt-propagation-candidate-v1-evidence/preflight.json"


def test_candidate_identity_is_reproducible_and_sources_are_bound():
    value = json.loads(ARTIFACT.read_text("utf-8")); ids = value["identities"]
    parts = [value["artifact_id"], value["approved_failure_review_identity"],
             value["source_evaluator_binding_identity"], ids["propagation_module_sha256"],
             ids["evaluator_v1_1_sha256"], ids["evaluator_v1_1_identity"],
             "CAPTURED_FIXTURES_ONLY", "ZERO_INFERENCE"]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == value["candidate_identity"]
    for relative, expected in (
        ("src/pastila_scout/semantic_admission_v2/stage_p_constraint_failure_propagation_v1.py",
         ids["propagation_module_sha256"]),
        ("src/pastila_scout/semantic_admission_v2/stage_p_construction_role_evaluator_v1_1.py",
         ids["evaluator_v1_1_sha256"]),
    ):
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_candidate_has_no_execution_or_runtime_authority():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert not any(value["authority"].values())
    assert evidence["result"] == "PASS"
    assert evidence["wsl_calls"] == evidence["model_calls"] == evidence["provider_calls"] == 0
    assert evidence["inference_calls"] == evidence["case01_reruns"] == evidence["stage_c_calls"] == 0
