from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_contract_v1_1 import ScopeGraphLedgerV1_1


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-v1-1-contract-prompt-candidate.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-v1-1-contract-prompt-evidence"


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def test_candidate_identity_and_manifest_are_exact():
    value = json.loads(CANDIDATE.read_text("utf-8"))
    expected = value.pop("candidate_identity")
    assert hashlib.sha256(_canonical(value)).hexdigest() == expected
    manifest = json.loads((EVIDENCE / "manifest.json").read_text("utf-8"))
    assert manifest["candidate_identity"] == expected


def test_contract_prompt_and_schema_hashes_are_current():
    value = json.loads(CANDIDATE.read_text("utf-8"))
    paths = {"contract_source_identity": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_contract_v1_1.py",
             "prompt_contract_identity": "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_prompt_v1_1.py"}
    for key, relative in paths.items():
        assert value[key] == "sha256:" + hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    prompt = (ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-prompt-v1-1.txt").read_bytes()
    assert value["prompt_identity"] == "sha256:" + hashlib.sha256(prompt[:-1]).hexdigest()
    assert value["schema_identity"] == "sha256:" + hashlib.sha256(_canonical(ScopeGraphLedgerV1_1.model_json_schema())).hexdigest()


def test_evidence_is_zero_inference_and_grants_no_authority():
    value = json.loads(CANDIDATE.read_text("utf-8"))
    preflight = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    assert not any(value["authority"].values()) and preflight["result"] == "PASS"
    assert preflight["grammar_changes"] == 0 and preflight["inference_executed"] is False
    for key in ("tokenizer_loads", "model_loads", "model_calls", "provider_calls", "runner_calls"):
        assert preflight[key] == 0
