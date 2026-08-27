from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-case01-failure-analysis-v1.json"


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def test_design_identity_is_canonical():
    value = json.loads(DESIGN.read_text("utf-8"))
    expected = value.pop("design_identity")
    assert hashlib.sha256(_canonical(value)).hexdigest() == expected


def test_design_separates_demonstrated_findings_from_hypotheses():
    value = json.loads(DESIGN.read_text("utf-8"))
    assert len(value["demonstrated_failures"]) == 4
    assert all(item["status"] != "DEMONSTRATED" for item in value["contributing_factors"])
    assert value["acceptance_result"]["case01_scope_semantics"] == "FAIL"


def test_remediation_preserves_embedded_unsupported_returns_and_plain_facts():
    value = json.loads(DESIGN.read_text("utf-8"))
    contract = " ".join(value["zero_inference_acceptance_contract"])
    assert "governed literal clause nested" in contract
    assert "unsupported presupposition nested" in contract
    assert "standalone noncreative governed proposition" in contract
    assert "Pure creative components" in contract


def test_design_grants_no_change_or_execution_authority():
    value = json.loads(DESIGN.read_text("utf-8"))
    assert value["lifecycle"] == "DESIGN_ONLY_READY_FOR_OWNER_REVIEW"
    assert not any(value["authority"].values())
