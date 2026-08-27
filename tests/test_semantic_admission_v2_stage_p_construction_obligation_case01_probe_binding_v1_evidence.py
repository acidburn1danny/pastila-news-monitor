from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-case01-probe-binding-v1.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-case01-probe-binding-v1-evidence/preflight.json"
RUNNER = ROOT / "src/pastila_scout/semantic_admission_v2/run_stage_p_construction_obligation_case01_probe_v1.py"


def test_canonical_binding_identity_and_runner_bytes():
    artifact = json.loads(ARTIFACT.read_bytes())
    runner_sha = hashlib.sha256(RUNNER.read_bytes()).hexdigest()
    parts = [
        artifact["artifact_id"], artifact["approved_dfa_candidate_identity"],
        artifact["approved_evaluator_binding_identity"], artifact["identities"]["evaluator_identity"],
        artifact["case_id"], artifact["pack_sha256"], artifact["factual_summary_sha256"],
        artifact["candidate_sha256"], runner_sha,
    ]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == artifact["binding_identity"]
    assert runner_sha == artifact["probe_runner_sha256"]


def test_preflight_and_authority_are_zero_inference_and_fail_closed():
    artifact = json.loads(ARTIFACT.read_bytes())
    preflight = json.loads(PREFLIGHT.read_bytes())
    assert preflight["binding_identity"] == artifact["binding_identity"]
    assert preflight["result"] == "PASS"
    assert preflight["runner_calls"] == preflight["provider_calls"] == preflight["inference_calls"] == 0
    assert preflight["case01_executed"] is False and preflight["stage_c_calls"] == 0
    assert all(value is False for value in artifact["authority"].values())
    assert artifact["execution_boundaries"]["maximum_provider_calls"] == 1
    assert artifact["execution_boundaries"]["retry_count"] == 0
    assert artifact["execution_boundaries"]["repair_count"] == 0
    assert artifact["execution_boundaries"]["selection_count"] == 0
