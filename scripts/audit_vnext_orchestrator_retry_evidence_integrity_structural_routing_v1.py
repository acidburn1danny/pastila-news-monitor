#!/usr/bin/env python3
"""Audit retry-evidence integrity and structural-failure factual routing."""
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
    closure = load("vnext-orchestrator-retry-evidence-integrity-structural-failure-factual-routing-repair-v1.json")
    for value, key in ((manifest, "manifest_identity"), (closure, "closure_identity")):
        assert value[key] == object_identity({k: v for k, v in value.items() if k != key})
    assert manifest["bound_commit"] == "83d11754a3ff852aeaf68ee633dbab64e8eb69aa"
    assert manifest["current_auditor"] == "scripts/audit_vnext_orchestrator_retry_evidence_integrity_structural_routing_v1.py"
    invariants = manifest["invariants"]
    assert invariants["orchestrator_retry_evidence_integrity"] is True
    assert invariants["orchestrator_structural_failure_factual_routing"] is True
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
    source = (ROOT / "src/pastila_scout/vnext_product_orchestrator_v1.py").read_text(encoding="utf-8")
    for marker in (
        "load_editor_failure_bundle",
        "persisted structural failure is absent or ambiguous",
        "vnext-editor-retry-authorization-receipt",
        "EDITOR retry authorization binding mismatch",
        "review_kind == \"STRUCTURAL_FAILURE\"",
        "structural_failure=structural_failure",
        "unsupported factual review bundle",
    ):
        assert marker in source
    findings = scan_legacy_dependencies(ROOT / "src/pastila_scout")
    active_names = {Path(value).name for value in modules}
    assert [finding for finding in findings if finding["path"] in active_names] == []
    product_lock = Path("/root/pastila-vnext/v1/product-lock.json")
    if product_lock.exists():
        assert hashlib.sha256(product_lock.read_bytes()).hexdigest() == LOCK_SHA
    assert not Path("/root/pastila-vnext/v2").exists()
    assert SCHEMA_VERSION == 6
    assert closure["validation"]["suite"] == "134_PASS"
    assert closure["validation"]["dedicated_fault_injection"] == "24_PASS"
    assert closure["invariants"]["audit_streak"] == "0/2"
    print(json.dumps({
        "status": "PASS",
        "closure_identity": closure["closure_identity"],
        "manifest_identity": manifest["manifest_identity"],
        "suite": "134_PASS",
        "dedicated_fault_injection": "24_PASS",
        "legacy_dependency_count": 0,
        "schema_version": SCHEMA_VERSION,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
