#!/usr/bin/env python3
"""Audit neutral no-eligible terminal workflow authority and recovery."""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path

from pastila_scout.vnext_foundation_v1 import object_identity, scan_legacy_dependencies
from pastila_scout.vnext_product_orchestrator_v1 import ProductOrchestrator
from pastila_scout.vnext_scout_production_v1 import (
    validate_terminal_capture_outcome,
)
from pastila_scout.vnext_state_sqlite_v1 import SCHEMA_VERSION
from pastila_scout.vnext_workflow_v1 import STATES, TRANSITIONS

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
LOCK_SHA = "2ddc484171f3b58f0f10ce4c4c73c1db51323d5c545320c578dc17ebb3edb4e6"


def load(name: str) -> dict[str, object]:
    value = json.loads((ART / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def identity(value: dict[str, object], key: str) -> None:
    assert value[key] == object_identity({k: v for k, v in value.items() if k != key})


def main() -> None:
    manifest = load("vnext-active-authority-audit-manifest-v1.json")
    workflow = load("vnext-active-product-workflow-state-contract-v4.json")
    sqlite = load("vnext-consolidated-operational-state-sqlite-boundary-v7-contract.json")
    closure = load("vnext-scout-no-eligible-terminal-workflow-authority-repair-v1.json")
    for value, key in (
        (manifest, "manifest_identity"),
        (workflow, "authority_identity"),
        (sqlite, "authority_identity"),
        (closure, "closure_identity"),
    ):
        identity(value, key)

    assert manifest["bound_commit"] == "4584c94812e0dddaba6cd2e75c8787db94610181"
    assert manifest["current_auditor"] == (
        "scripts/audit_vnext_scout_no_eligible_terminal_workflow_repair_v1.py"
    )
    assert manifest["active_authorities"]["workflow"] == {
        "identity": workflow["authority_identity"],
        "identity_key": "authority_identity",
        "path": "docs/artifacts/vnext-active-product-workflow-state-contract-v4.json",
    }
    assert set(map(tuple, workflow["transitions"])) == set(TRANSITIONS)
    assert set(workflow["states"]) == set(STATES)
    assert ("DISCOVERED", "NO_ELIGIBLE_CONTENT") in TRANSITIONS
    assert workflow["terminal_semantics"] == {
        "CAPTURE_FAILED": {
            "operational_outcome": "FAIL",
            "requires_capture_failure_evidence": True,
        },
        "NO_ELIGIBLE_CONTENT": {
            "operational_outcome": "PASS",
            "requires_all_enabled_sources_no_eligible": True,
        },
    }

    invariants = manifest["invariants"]
    assert invariants["no_eligible_terminal_authority"] is True
    assert invariants["capture_terminal_recovery"] is True
    assert invariants["active_integration"] is False
    assert invariants["product_lock_replaced"] is False
    assert invariants["legacy_dependency_count"] == 0
    assert invariants["stop_all_candidates"] is True
    assert invariants["voice"] == "DISABLED_UNTIL_PROMOTION"

    assert SCHEMA_VERSION == 7
    assert closure["authority"]["schema_migration"] is False
    assert closure["authority"]["sqlite_v7_identity"] == sqlite["authority_identity"]
    assert closure["authority"]["workflow_v4_identity"] == workflow["authority_identity"]
    assert closure["validation"] == {
        "dedicated": "14_PASS",
        "self_contained_auditor": "PASS",
        "vnext_suite": "385_PASS",
    }
    assert closure["invariants"]["audit_streak"] == "0/2"

    scout = (ROOT / "src/pastila_scout/vnext_scout_production_v1.py").read_text(encoding="utf-8")
    for marker in (
        '"CAPTURE_FAILED" if failures else "NO_ELIGIBLE_CONTENT"',
        "terminal capture transition ownership is absent or ambiguous",
        "no-eligible terminal semantics mismatch",
        "capture-failed terminal semantics mismatch",
        "terminal capture canonical workflow history mismatch",
    ):
        assert marker in scout
    recovery_source = inspect.getsource(validate_terminal_capture_outcome)
    assert '"PASS"' in recovery_source
    assert '"FAIL"' in recovery_source
    assert hasattr(ProductOrchestrator, "load_capture_terminal_result")

    modules = set(manifest["active_runtime_modules"])
    discovered: set[str] = set()
    for relative in modules:
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module and node.module.startswith("vnext_"):
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
        "closure_identity": closure["closure_identity"],
        "manifest_identity": manifest["manifest_identity"],
        "suite": "385_PASS",
        "dedicated": "14_PASS",
        "legacy_dependency_count": 0,
        "schema_version": SCHEMA_VERSION,
        "schema_migration": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
