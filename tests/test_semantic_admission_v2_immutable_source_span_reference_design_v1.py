from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-case01-execution-result-v1.json"
DESIGN = ROOT / "docs/artifacts/semantic-admission-v2-immutable-source-span-reference-design-v1.json"


def _load(path: Path):
    return json.loads(path.read_bytes())


def test_frozen_result_identity_and_terminal_controls():
    value = _load(RESULT)
    parts = [value["artifact_id"], value["source_binding_identity"],
             value["attempts"][0]["phase_receipt_sha256"],
             value["attempts"][1]["phase_receipt_sha256"],
             value["attempts"][1]["raw_sha256"],
             value["attempts"][1]["durable_lifecycle_tree_identity"]]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == value["result_identity"]
    assert value["attempts"][1]["source_membership"] == "FAIL"
    assert value["call_controls"]["completed_retry_count"] == 1
    assert value["call_controls"]["further_probe_calls"] == value["call_controls"]["stage_c_calls"] == 0
    assert all(item is False for item in value["authority"].values())


def test_design_identity_and_copyless_contract():
    value = _load(DESIGN)
    parts = [value["artifact_id"], "STAGE_P_CONSTRUCTION_OBLIGATION_CASE01_EXECUTION_RESULT_V1",
             value["recommended_contract"]["name"], "NO_APPROXIMATE_REPAIR", "DESIGN_ONLY"]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == value["design_identity"]
    assert value["recommended_contract"]["name"] == "COPYLESS_UTF8_HALF_OPEN_SOURCE_REFERENCE"
    assert value["recommended_contract"]["model_emits"]["start_utf8"]
    assert value["recommended_contract"]["model_emits"]["end_utf8"]


def test_design_prohibits_fuzzy_repair_and_keeps_semantics_separate():
    value = _load(DESIGN)
    fuzzy = next(x for x in value["alternatives_assessed"] if x["option"] == "FUZZY_MATCH_OR_NEAREST_SOURCE_SNAPPING")
    assert fuzzy["disposition"] == "PROHIBITED"
    assert "semantic_receipt" in value["receipt_separation"]
    assert any("event_alignment" in item for item in value["case01_acceptance_requirements"])
    assert all(item is False for item in value["authority"].values())
