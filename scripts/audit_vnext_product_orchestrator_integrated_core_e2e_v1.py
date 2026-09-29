#!/usr/bin/env python3
"""Audit the isolated product orchestrator and integrated core E2E closure."""
from __future__ import annotations

import ast
import json
from pathlib import Path

from pastila_scout.vnext_foundation_v1 import object_identity, scan_legacy_dependencies
from pastila_scout.vnext_state_sqlite_v1 import SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
EXPECTED_LOCK = "2ddc484171f3b58f0f10ce4c4c73c1db51323d5c545320c578dc17ebb3edb4e6"


def load(name: str) -> dict[str, object]:
    value = json.loads((ART / name).read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def main() -> None:
    manifest = load("vnext-active-authority-audit-manifest-v1.json")
    closure = load("vnext-product-orchestrator-integrated-core-e2e-closure-v1.json")
    for value, key in ((manifest, "manifest_identity"), (closure, "closure_identity")):
        assert value[key] == object_identity({k: v for k, v in value.items() if k != key})
    assert closure["base_commit"] == "71443f463c6f0320b9c4f53f37bf672157764286"
    assert manifest["bound_commit"] == "71443f463c6f0320b9c4f53f37bf672157764286"
    assert manifest["current_auditor"] == "scripts/audit_vnext_product_orchestrator_integrated_core_e2e_v1.py"
    invariants = manifest["invariants"]
    assert invariants["product_orchestrator_implemented"] is True
    assert invariants["active_integration"] is False
    assert invariants["product_lock_replaced"] is False
    assert invariants["voice"] == "DISABLED_UNTIL_PROMOTION"
    assert invariants["stop_all_candidates"] is True
    assert invariants["legacy_dependency_count"] == 0
    modules = set(manifest["active_runtime_modules"])
    orchestrator = "src/pastila_scout/vnext_product_orchestrator_v1.py"
    assert orchestrator in modules
    discovered: set[str] = set()
    for relative in modules:
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module and node.module.startswith("vnext_"):
                candidate = f"src/pastila_scout/{node.module}.py"
                if (ROOT / candidate).exists():
                    discovered.add(candidate)
    assert discovered <= modules, sorted(discovered - modules)
    source = (ROOT / orchestrator).read_text(encoding="utf-8")
    for marker in (
        "FactualReviewInstruction",
        "PolicyInstruction",
        "explicit APPROVE_FINAL authority",
        "capture_and_group",
        "select_and_generate_editor_draft",
        "apply_factual_review",
        "apply_policy_and_export",
        "load_editor_review_bundle",
        "load_factual_result_bundle",
    ):
        assert marker in source
    for forbidden in ("/root/pastila-vnext", "EvidencePacket", "factual ledger", "active integration"):
        assert forbidden not in source
    findings = scan_legacy_dependencies(ROOT / "src/pastila_scout")
    active_names = {Path(value).name for value in modules}
    assert [finding for finding in findings if finding["path"] in active_names] == []
    product_lock = Path("/root/pastila-vnext/v1/product-lock.json")
    if product_lock.exists():
        import hashlib
        assert hashlib.sha256(product_lock.read_bytes()).hexdigest() == EXPECTED_LOCK
    assert not Path("/root/pastila-vnext/v2").exists()
    assert SCHEMA_VERSION == 6
    assert closure["validation"]["suite"] == "121_PASS"
    assert closure["validation"]["dedicated"] == "11_PASS"
    assert closure["invariants"]["audit_streak"] == "0/2"
    print(json.dumps({
        "status": "PASS",
        "closure_identity": closure["closure_identity"],
        "manifest_identity": manifest["manifest_identity"],
        "suite": "121_PASS",
        "dedicated": "11_PASS",
        "legacy_dependency_count": 0,
        "schema_version": SCHEMA_VERSION,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
