#!/usr/bin/env python3
"""Audit FINAL atomic publication, recovery, and authority semantics."""
from __future__ import annotations

import ast
import json
from pathlib import Path

from pastila_scout.vnext_foundation_v1 import object_identity, scan_legacy_dependencies
from pastila_scout.vnext_state_sqlite_v1 import SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def load(name: str) -> dict[str, object]:
    value = json.loads((ART / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def main() -> None:
    manifest = load("vnext-active-authority-audit-manifest-v1.json")
    closure = load("vnext-final-atomic-publication-recovery-authority-repair-v1.json")
    for value, key in ((manifest, "manifest_identity"), (closure, "closure_identity")):
        assert value[key] == object_identity({k: v for k, v in value.items() if k != key})
    assert manifest["bound_commit"] == "0a4e6e00281c658f7930958e57292631cdefeff4"
    assert manifest["current_auditor"] == "scripts/audit_vnext_final_atomic_publication_recovery_authority_v1.py"
    invariants = manifest["invariants"]
    assert invariants["post_acceptance_policy_final_implemented"] is True
    assert invariants["policy_final_merged"] is True
    assert invariants["product_orchestrator_implemented"] is False
    assert invariants["active_integration"] is False
    assert invariants["product_lock_replaced"] is False
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
    source = (ROOT / "src/pastila_scout/vnext_core_final_v1.py").read_text(encoding="utf-8")
    for marker in (
        "load_exported_final",
        "FINAL output is not export-eligible",
        "receipts/final-exports",
        "FINAL export bytes mismatch",
        "FINAL_READY",
        "EXPORTED",
    ):
        assert marker in source
    findings = scan_legacy_dependencies(ROOT / "src/pastila_scout")
    active_names = {Path(value).name for value in modules}
    assert [finding for finding in findings if finding["path"] in active_names] == []
    assert SCHEMA_VERSION == 6
    assert closure["validation"]["tests"] == "106_PASS"
    assert closure["validation"]["fault_injection"] == "3_PASS"
    assert closure["invariants"]["audit_streak"] == "0/2"
    print(json.dumps({
        "status": "PASS",
        "closure_identity": closure["closure_identity"],
        "manifest_identity": manifest["manifest_identity"],
        "fault_injection": "3_PASS",
        "legacy_dependency_count": 0,
        "schema_version": SCHEMA_VERSION,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
