from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-runner-executor-binding-v1.json"
EVALUATOR = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-evaluator-binding-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-binding-v1-evidence/preflight.json"


def test_runner_and_evaluator_binding_identities_are_reproducible():
    runner = json.loads(RUNNER.read_text("utf-8")); ids = runner["identities"]
    parts = [runner["artifact_id"], runner["approved_dfa_candidate_identity"], ids["runner_sha256"],
             ids["executor_sha256"], ids["tracker_sha256"], ids["controller_sha256"],
             ids["tokenizer_identity"]]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == runner["binding_identity"]
    evaluator = json.loads(EVALUATOR.read_text("utf-8")); eids = evaluator["identities"]
    parts = [evaluator["artifact_id"], evaluator["approved_dfa_candidate_identity"],
             evaluator["approved_runner_executor_binding_identity"], eids["request_module_sha256"],
             eids["evaluator_sha256"], eids["executor_sha256"], eids["evaluator_identity"],
             evaluator["receipt_propagation_candidate_identity"]]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == evaluator["binding_identity"]


def test_no_probe_case_or_runtime_authority_exists():
    evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "PASS" and not evidence["probe_constructed"]
    assert not evidence["case01_request_constructed"] and not evidence["case01_executed"]
    assert evidence["runner_calls"] == evidence["model_loads"] == evidence["inference_calls"] == 0
    for path in (RUNNER, EVALUATOR):
        assert not any(json.loads(path.read_text("utf-8"))["authority"].values())
