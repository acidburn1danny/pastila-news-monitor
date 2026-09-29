#!/usr/bin/env python3
"""Audit state-aware orchestrator recovery and terminal routing repair."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from pastila_scout.vnext_foundation_v1 import object_identity, scan_legacy_dependencies
from pastila_scout.vnext_state_sqlite_v1 import SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
LOCK_SHA = "2ddc484171f3b58f0f10ce4c4c73c1db51323d5c545320c578dc17ebb3edb4e6"


def load(name: str) -> dict[str, object]:
    value = json.loads((ART / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def main() -> None:
    manifest = load("vnext-active-authority-audit-manifest-v1.json")
    closure = load("vnext-product-orchestrator-state-aware-recovery-terminal-routing-repair-v1.json")
    for value, key in ((manifest, "manifest_identity"), (closure, "closure_identity")):
        assert value[key] == object_identity({k: v for k, v in value.items() if k != key})
    assert manifest["bound_commit"] == "08d722e0af008fc163d990ea35233b9dc0027bea"
    assert manifest["current_auditor"] == "scripts/audit_vnext_product_orchestrator_state_aware_recovery_terminal_routing_v1.py"
    invariants = manifest["invariants"]
    assert invariants["product_orchestrator_implemented"] is True
    assert invariants["orchestrator_state_aware_recovery"] is True
    assert invariants["orchestrator_terminal_routing"] is True
    assert invariants["active_integration"] is False
    assert invariants["product_lock_replaced"] is False
    assert invariants["legacy_dependency_count"] == 0
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
    orchestrator = (ROOT / "src/pastila_scout/vnext_product_orchestrator_v1.py").read_text(encoding="utf-8")
    editor = (ROOT / "src/pastila_scout/vnext_editor_vertical_slice_v1.py").read_text(encoding="utf-8")
    for marker in (
        "load_source_packet",
        "retry_editor_generation",
        "record_editor_failure",
        "explicit retry or failure disposition",
        "_load_policy_decision",
        "APPROVED_FOR_FINAL",
        "FINAL_READY",
        "PolicyTerminalBundle",
        "ABSTAINED is terminal",
    ):
        assert marker in orchestrator
    for marker in (
        'state == "SOURCE_PACKET_READY"',
        'state != "EDITOR_PENDING"',
        "workflow is not ready to persist EditorDraft",
        "workflow is not ready to persist structural failure",
        "vnext-editor-retry-authorization-receipt",
        "editor-retry-authorizations",
    ):
        assert marker in editor
    findings = scan_legacy_dependencies(ROOT / "src/pastila_scout")
    active_names = {Path(value).name for value in modules}
    assert [finding for finding in findings if finding["path"] in active_names] == []
    product_lock = Path("/root/pastila-vnext/v1/product-lock.json")
    if product_lock.exists():
        assert hashlib.sha256(product_lock.read_bytes()).hexdigest() == LOCK_SHA
    assert not Path("/root/pastila-vnext/v2").exists()
    assert SCHEMA_VERSION == 6
    assert closure["validation"]["suite"] == "128_PASS"
    assert closure["validation"]["dedicated_fault_injection"] == "18_PASS"
    assert closure["invariants"]["audit_streak"] == "0/2"
    print(json.dumps({
        "status": "PASS",
        "closure_identity": closure["closure_identity"],
        "manifest_identity": manifest["manifest_identity"],
        "suite": "128_PASS",
        "dedicated_fault_injection": "18_PASS",
        "legacy_dependency_count": 0,
        "schema_version": SCHEMA_VERSION,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
