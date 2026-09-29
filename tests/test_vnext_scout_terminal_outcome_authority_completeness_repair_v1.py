from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_state_sqlite_v1 import SCHEMA_VERSION
from pastila_scout.vnext_workflow_v1 import STATES, TRANSITIONS

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"

EXPECTED_TERMINAL_SEMANTICS = {
    "CAPTURE_FAILED": {
        "allowed_source_dispositions": ["CAPTURE_FAILED", "NO_ELIGIBLE_ENTRIES"],
        "minimum_valid_failures": 1,
        "operational_outcome": "FAIL",
        "requires_capture_failure_evidence": True,
        "requires_zero_captures": True,
    },
    "NO_ELIGIBLE_CONTENT": {
        "allowed_source_dispositions": ["NO_ELIGIBLE_ENTRIES"],
        "maximum_valid_failures": 0,
        "operational_outcome": "PASS",
        "requires_all_enabled_sources_no_eligible": True,
        "requires_zero_captures": True,
    },
}

RUNTIME_HASHES = {
    "src/pastila_scout/vnext_workflow_v1.py": "b3214f3b9f43ae14751bd0ecc2c04d055435ca56996ed735c438efd6d930506a",
    "src/pastila_scout/vnext_scout_production_v1.py": "b08633014c2d59ab39b668d3371bbc37003c676e606584d2d0333c784226632d",
    "src/pastila_scout/vnext_product_orchestrator_v1.py": "f158c01a3d48455c58f0a32780df607a4dcf4a35c936bcf3645d2dd1e3c689e7",
}


def load(name: str) -> dict[str, object]:
    value = json.loads((ART / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_workflow_authority_v5_declares_exact_terminal_predicates():
    authority = load("vnext-active-product-workflow-state-contract-v5.json")
    assert authority["authority_identity"] == object_identity(
        {key: value for key, value in authority.items() if key != "authority_identity"}
    )
    assert authority["supersedes"] == "vnext-active-product-workflow-state-contract-v4"
    assert authority["terminal_semantics"] == EXPECTED_TERMINAL_SEMANTICS
    assert set(map(tuple, authority["transitions"])) == set(TRANSITIONS)
    assert set(authority["states"]) == set(STATES)


def test_v5_predecessor_auditor_is_historical_not_current():
    manifest = load("vnext-active-authority-audit-manifest-v1.json")
    expected = {
        "commit": "86af603a",
        "path": "scripts/audit_vnext_scout_terminal_outcome_authority_completeness_repair_v1.py",
    }
    assert expected in manifest["historical_commit_only_auditors"]
    assert manifest["current_auditor"] != expected["path"]

def test_runtime_and_sqlite_are_byte_identical_and_unchanged():
    for relative, expected in RUNTIME_HASHES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected
    assert SCHEMA_VERSION == 7
