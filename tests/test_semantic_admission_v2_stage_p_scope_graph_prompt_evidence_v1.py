from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-prompt-v1-candidate.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-prompt-v1-evidence"


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def test_candidate_identity_and_manifest_are_bound():
    candidate = json.loads(CANDIDATE.read_text("utf-8"))
    expected = candidate.pop("candidate_identity")
    assert hashlib.sha256(_canonical(candidate)).hexdigest() == expected
    manifest = json.loads((EVIDENCE / "manifest.json").read_text("utf-8"))
    assert manifest["candidate_identity"] == expected
    for key in ("prompt_identity", "prompt_contract_identity", "schema_identity", "grammar_identity", "tokenizer_identity"):
        assert manifest[key] == candidate[key]


def test_prompt_and_contract_hashes_are_current():
    candidate = json.loads(CANDIDATE.read_text("utf-8"))
    prompt = (ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-prompt-v1.txt").read_bytes()
    contract = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_prompt_v1.py"
    assert candidate["prompt_identity"] == "sha256:" + hashlib.sha256(prompt[:-1]).hexdigest()
    assert candidate["prompt_contract_identity"] == "sha256:" + hashlib.sha256(contract.read_bytes()).hexdigest()


def test_evidence_is_zero_inference_and_candidate_grants_no_authority():
    candidate = json.loads(CANDIDATE.read_text("utf-8"))
    preflight = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    assert not any(candidate["authority"].values())
    assert preflight["result"] == "PASS" and preflight["inference_executed"] is False
    for key in ("model_loads", "model_calls", "provider_calls", "runner_calls"):
        assert preflight[key] == 0
