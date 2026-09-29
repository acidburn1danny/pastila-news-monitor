#!/usr/bin/env python3
"""Audit complete terminal outcome authority without runtime changes."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from pastila_scout.vnext_foundation_v1 import object_identity, scan_legacy_dependencies
from pastila_scout.vnext_state_sqlite_v1 import SCHEMA_VERSION
from pastila_scout.vnext_workflow_v1 import STATES, TRANSITIONS

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
LOCK_SHA = "2ddc484171f3b58f0f10ce4c4c73c1db51323d5c545320c578dc17ebb3edb4e6"
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
    "src/pastila_scout/vnext_product_orchestrator_v1.py": "f158c01a3d48455c58f0a32780df607a4dcf4a35c936bcf3645d2dd1e3c689e7",
    "src/pastila_scout/vnext_scout_production_v1.py": "b08633014c2d59ab39b668d3371bbc37003c676e606584d2d0333c784226632d",
    "src/pastila_scout/vnext_workflow_v1.py": "b3214f3b9f43ae14751bd0ecc2c04d055435ca56996ed735c438efd6d930506a",
}


def load(name: str) -> dict[str, object]:
    value = json.loads((ART / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def exact_identity(value: dict[str, object], key: str) -> None:
    assert value[key] == object_identity({k: v for k, v in value.items() if k != key})


def main() -> None:
    manifest = load("vnext-active-authority-audit-manifest-v1.json")
    workflow = load("vnext-active-product-workflow-state-contract-v5.json")
    sqlite = load("vnext-consolidated-operational-state-sqlite-boundary-v7-contract.json")
    closure = load("vnext-scout-terminal-outcome-authority-completeness-repair-v1.json")
    for value, key in (
        (manifest, "manifest_identity"),
        (workflow, "authority_identity"),
        (sqlite, "authority_identity"),
        (closure, "closure_identity"),
    ):
        exact_identity(value, key)

    assert manifest["bound_commit"] == "87ddff21382c86c51fcc3fcdbb6cf46cec798d1f"
    assert manifest["current_auditor"] == (
        "scripts/audit_vnext_scout_terminal_outcome_authority_completeness_repair_v1.py"
    )
    assert manifest["active_authorities"]["workflow"] == {
        "identity": workflow["authority_identity"],
        "identity_key": "authority_identity",
        "path": "docs/artifacts/vnext-active-product-workflow-state-contract-v5.json",
    }
    assert workflow["supersedes"] == "vnext-active-product-workflow-state-contract-v4"
    assert workflow["terminal_semantics"] == EXPECTED_TERMINAL_SEMANTICS
    assert set(map(tuple, workflow["transitions"])) == set(TRANSITIONS)
    assert set(workflow["states"]) == set(STATES)
    assert SCHEMA_VERSION == 7

    assert closure["authority"] == {
        "schema_migration": False,
        "sqlite_schema_version": 7,
        "workflow_v5_identity": workflow["authority_identity"],
    }
    assert closure["runtime_sha256"] == dict(sorted(RUNTIME_HASHES.items()))
    assert closure["validation"] == {
        "dedicated": "3_PASS",
        "self_contained_auditor": "PASS",
        "vnext_suite": "388_PASS",
    }
    assert closure["invariants"] == {
        "active_integration": False,
        "audit_streak": "0/2",
        "legacy_dependency_count": 0,
        "product_lock_replaced": False,
    }
    for relative, expected in RUNTIME_HASHES.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected

    invariants = manifest["invariants"]
    assert invariants["terminal_outcome_authority_complete"] is True
    assert invariants["active_integration"] is False
    assert invariants["product_lock_replaced"] is False
    assert invariants["legacy_dependency_count"] == 0
    assert invariants["stop_all_candidates"] is True
    assert invariants["voice"] == "DISABLED_UNTIL_PROMOTION"

    modules = set(manifest["active_runtime_modules"])
    discovered: set[str] = set()
    for relative in modules:
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.level == 1
                and node.module
                and node.module.startswith("vnext_")
            ):
                candidate = f"src/pastila_scout/{node.module}.py"
                if (ROOT / candidate).exists():
                    discovered.add(candidate)
    assert discovered <= modules, sorted(discovered - modules)
    findings = scan_legacy_dependencies(ROOT / "src/pastila_scout")
    active_names = {Path(value).name for value in modules}
    assert [item for item in findings if item["path"] in active_names] == []

    lock = Path("/root/pastila-vnext/v1/product-lock.json")
    if lock.exists():
        assert hashlib.sha256(lock.read_bytes()).hexdigest() == LOCK_SHA
    assert not Path("/root/pastila-vnext/v2").exists()

    print(json.dumps({
        "status": "PASS",
        "workflow_authority_identity": workflow["authority_identity"],
        "manifest_identity": manifest["manifest_identity"],
        "closure_identity": closure["closure_identity"],
        "suite": "388_PASS",
        "dedicated": "3_PASS",
        "runtime_byte_identical": True,
        "schema_version": SCHEMA_VERSION,
        "schema_migration": False,
        "legacy_dependency_count": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
