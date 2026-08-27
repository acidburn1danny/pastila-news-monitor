from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_contract_v1 import ScopeGraphLedgerV1


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-constraint-v1-candidate.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-constraint-v1-evidence"


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def test_candidate_identity_and_evidence_are_bound():
    candidate = json.loads(CANDIDATE.read_text("utf-8"))
    expected = candidate.pop("candidate_identity")
    assert hashlib.sha256(_canonical(candidate)).hexdigest() == expected
    preflight = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    manifest = json.loads((EVIDENCE / "manifest.json").read_text("utf-8"))
    for key in ("schema_identity", "constraint_source_identity", "grammar_identity"):
        assert candidate[key] == preflight[key] == manifest[key]
    assert manifest["candidate_identity"] == expected


def test_schema_constraint_and_grammar_hashes_are_current():
    candidate = json.loads(CANDIDATE.read_text("utf-8"))
    schema = "sha256:" + hashlib.sha256(_canonical(ScopeGraphLedgerV1.model_json_schema())).hexdigest()
    source = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_scope_graph_constraint_v1.py"
    constraint = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    grammar = "sha256:" + hashlib.sha256(f"{schema}\n{constraint}".encode()).hexdigest()
    assert (schema, constraint, grammar) == (candidate["schema_identity"], candidate["constraint_source_identity"],
                                             candidate["grammar_identity"])


def test_evidence_is_zero_inference_and_has_no_authority():
    candidate = json.loads(CANDIDATE.read_text("utf-8"))
    preflight = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    assert not any(candidate["authority"].values())
    for key in ("wsl_calls", "model_loads", "model_calls", "provider_calls", "tokenizer_loads"):
        assert preflight[key] == 0
    assert preflight["inference_executed"] is False
