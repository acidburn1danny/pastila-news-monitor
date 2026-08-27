from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-role-runner-executor-binding-v1.json"
EVALUATOR_ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-role-evaluator-binding-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-construction-role-binding-v1-evidence/preflight.json"


def test_runner_and_evaluator_binding_identities_are_reproducible():
    runner = json.loads(RUNNER_ARTIFACT.read_text("utf-8")); ids = runner["identities"]
    parts = [runner["artifact_id"], runner["approved_candidate_identity"], ids["runner_sha256"],
             ids["executor_sha256"], ids["tracker_sha256"], ids["controller_sha256"],
             ids["tokenizer_identity"]]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == runner["binding_identity"]
    evaluator = json.loads(EVALUATOR_ARTIFACT.read_text("utf-8")); eids = evaluator["identities"]
    parts = [evaluator["artifact_id"], evaluator["approved_request_candidate_identity"],
             evaluator["approved_runner_executor_binding_identity"], eids["evaluator_sha256"],
             eids["executor_sha256"], eids["evaluator_identity"]]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == evaluator["binding_identity"]


def test_receipts_deny_case01_stage_c_and_all_runtime_authority():
    evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "PASS"
    assert evidence["runner_calls"] == evidence["model_loads"] == evidence["inference_calls"] == 0
    assert not evidence["case01_request_constructed"] and not evidence["case01_executed"]
    assert evidence["stage_c_calls"] == 0
    for path in (RUNNER_ARTIFACT, EVALUATOR_ARTIFACT):
        value = json.loads(path.read_text("utf-8"))
        assert not any(value["authority"].values())
