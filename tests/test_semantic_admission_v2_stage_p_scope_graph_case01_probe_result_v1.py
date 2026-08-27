from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-case01-probe-v1-result.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-case01-probe-v1-evidence"


def test_raw_and_result_identities_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    raw = (EVIDENCE / "stage-p-raw.bin").read_bytes()
    assert hashlib.sha256(raw).hexdigest() == value["execution_receipt"]["raw_sha256"]
    expected = hashlib.sha256(("STAGE_P_SCOPE_GRAPH_CASE01_PROBE_V1\n" + value["source_binding_identity"] + "\n" +
                               value["execution_receipt"]["raw_sha256"] + "\n" +
                               value["execution_receipt"]["durable_lifecycle_identity"]).encode()).hexdigest()
    assert value["result_identity"] == expected


def test_raw_shape_matches_recorded_semantic_failure():
    raw = json.loads((EVIDENCE / "stage-p-raw.bin").read_bytes())
    value = json.loads(ARTIFACT.read_text("utf-8"))
    assert raw["coverage_decision"] == "COMPLETE" and len(raw["entries"]) == 1
    entry = raw["entries"][0]
    assert entry["entry_type"] == "REAL_WORLD_COMMITMENT"
    assert entry["scope_relation"] == "STANDALONE" and entry["authority_support"] is None
    assert value["acceptance_assessment"]["scope_graph_semantic_acceptance"] == "FAIL"


def test_single_call_and_quarantine_boundaries_are_preserved():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    receipt = json.loads((EVIDENCE / "stage-p-phase-receipt-v2.json").read_text("utf-8"))
    assert receipt["provider_call_count"] == value["execution_receipt"]["provider_call_count"] == 1
    assert receipt["eligibility"] == value["execution_receipt"]["eligibility"] == "QUARANTINED_EVALUATION_ONLY"
    assert not any(value["authority"].values())
    assert all(count == 0 for count in value["call_controls"].values())
