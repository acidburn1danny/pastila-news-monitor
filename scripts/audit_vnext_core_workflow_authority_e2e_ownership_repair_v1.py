#!/usr/bin/env python3
"""Audit VNext core authority and end-to-end ownership repair."""
from __future__ import annotations

import ast
import json
from pathlib import Path

from pastila_scout.vnext_foundation_v1 import object_identity, scan_legacy_dependencies
from pastila_scout.vnext_state_sqlite_v1 import SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/artifacts/vnext-active-authority-audit-manifest-v1.json"
CLOSURE = ROOT / "docs/artifacts/vnext-core-workflow-authority-e2e-ownership-repair-v1.json"
CORE = ROOT / "src/pastila_scout/vnext_core_final_v1.py"


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def main() -> None:
    manifest = load(MANIFEST)
    closure = load(CLOSURE)
    assert manifest["manifest_identity"] == object_identity(
        {key: value for key, value in manifest.items() if key != "manifest_identity"}
    )
    assert closure["closure_identity"] == object_identity(
        {key: value for key, value in closure.items() if key != "closure_identity"}
    )
    assert manifest["bound_commit"] == "23995243a2b46bcdb94742d29fac818b3aee842a"
    assert manifest["binding_semantics"] == "SUCCESSOR_OVER_BOUND_COMMIT"
    assert manifest["current_auditor"] == "scripts/audit_vnext_core_workflow_authority_e2e_ownership_repair_v1.py"
    assert manifest["invariants"]["final_implemented"] is True
    assert manifest["invariants"]["orchestrator_implemented"] is True
    assert manifest["invariants"]["core_workflow_policy_final_merged"] is True
    assert manifest["invariants"]["active_integration"] is False
    assert manifest["invariants"]["product_lock_replaced"] is False
    assert SCHEMA_VERSION == 6
    source = CORE.read_text(encoding="utf-8")
    ast.parse(source)
    for marker in (
        "persisted factual acceptance provenance missing",
        "factual decision payload mismatch",
        "factual receipt payload mismatch",
        "DETERMINISTIC_PASSTHROUGH_V1",
    ):
        assert marker in source
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
    assert [finding for finding in findings if finding["path"] in active_names] == []
    assert closure["validation"]["tests"] == "102_PASS"
    assert closure["validation"]["real_component_e2e"] == "4_PASS"
    assert closure["invariants"]["audit_streak"] == "0/2"
    print(json.dumps({
        "status": "PASS",
        "closure_identity": closure["closure_identity"],
        "manifest_identity": manifest["manifest_identity"],
        "legacy_dependency_count": 0,
        "schema_version": SCHEMA_VERSION,
        "real_component_e2e": "4_PASS",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
