"""Current-head audit for trusted factual review authority and active audit consolidation."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from pastila_scout.vnext_foundation_v1 import object_identity, scan_legacy_dependencies
from pastila_scout.vnext_state_sqlite_v1 import MIGRATION_4, SCHEMA_VERSION
from pastila_scout.vnext_workflow_v1 import STATES, TRANSITIONS

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SCOPE = (
    "docs/artifacts/vnext-active-authority-audit-manifest-v1.json",
    "docs/artifacts/vnext-consolidated-operational-state-sqlite-boundary-v4-contract.json",
    "docs/artifacts/vnext-trusted-review-authority-active-audit-repair-v1.json",
    "docs/vnext-trusted-review-authority-active-audit-repair-v1.md",
    "scripts/audit_vnext_trusted_review_authority_active_audit_repair_v1.py",
    "src/pastila_scout/vnext_factual_acceptance_v1.py",
    "src/pastila_scout/vnext_state_sqlite_v1.py",
    "tests/test_vnext_consolidated_operational_state_sqlite_boundary_v1.py",
    "tests/test_vnext_critical_path_authority_repair_editor_vertical_slice_v1.py",
    "tests/test_vnext_cross_component_authority_ownership_factual_repair_v1.py",
    "tests/test_vnext_trusted_review_authority_active_audit_repair_v1.py",
)


def load(name: str) -> dict[str, object]:
    value = json.loads((ART / name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(name)
    return value


def check_identity(value: dict[str, object], key: str) -> None:
    assert value[key] == object_identity({name: item for name, item in value.items() if name != key})


def main() -> None:
    workflow = load("vnext-active-product-workflow-state-contract-v3.json")
    sqlite = load("vnext-consolidated-operational-state-sqlite-boundary-v4-contract.json")
    manifest = load("vnext-active-authority-audit-manifest-v1.json")
    closure = load("vnext-trusted-review-authority-active-audit-repair-v1.json")
    check_identity(workflow, "authority_identity")
    check_identity(sqlite, "authority_identity")
    check_identity(manifest, "manifest_identity")
    check_identity(closure, "closure_identity")
    assert set(map(tuple, workflow["transitions"])) == set(TRANSITIONS)
    assert set(workflow["states"]) == set(STATES)
    assert SCHEMA_VERSION == 4 and any("CREATE TABLE review_sessions" in row for row in MIGRATION_4)
    assert manifest["active_authorities"]["workflow"]["identity"] == workflow["authority_identity"]
    assert manifest["active_authorities"]["sqlite"]["identity"] == sqlite["authority_identity"]
    assert closure["authority_bindings"]["active_manifest_identity"] == manifest["manifest_identity"]
    assert closure["authority_bindings"]["sqlite_v4_identity"] == sqlite["authority_identity"]
    assert manifest["current_auditor"] == "scripts/audit_vnext_trusted_review_authority_active_audit_repair_v1.py"
    historical = manifest["historical_commit_only_auditors"]
    assert len(historical) == 3 and all(row["commit"] for row in historical)
    active_modules = manifest["active_runtime_modules"]
    assert "src/pastila_scout/vnext_sourcepacket_binding_v1.py" not in active_modules
    for relative in active_modules:
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        assert all(
            not isinstance(node, ast.ImportFrom) or node.module != "vnext_sourcepacket_binding_v1"
            for node in ast.walk(tree)
        )
    factual = (ROOT / "src/pastila_scout/vnext_factual_acceptance_v1.py").read_text(encoding="utf-8")
    assert "EXPLICIT_TRUSTED_REVIEW_SESSION" not in factual
    assert "PERSISTED_SINGLE_USE_REVIEW_SESSION" in factual
    assert "UPDATE review_sessions SET status='CONSUMED'" in factual
    invariants = closure["invariants"]
    assert not invariants["active_integration"] and not invariants["product_lock_replaced"]
    assert not invariants["orchestrator_implemented"] and not invariants["final_implemented"]
    assert invariants["voice"] == "DISABLED_UNTIL_PROMOTION" and invariants["stop_all_candidates"]
    findings = scan_legacy_dependencies(ROOT / "src/pastila_scout")
    relevant = [row for row in findings if row["path"] in {Path(item).name for item in active_modules}]
    assert relevant == [] and invariants["legacy_dependency_count"] == 0
    files = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SCOPE}
    print(json.dumps({
        "status": "PASS", "scope": len(SCOPE), "schema_version": SCHEMA_VERSION,
        "workflow_identity": workflow["authority_identity"], "sqlite_identity": sqlite["authority_identity"],
        "manifest_identity": manifest["manifest_identity"], "closure_identity": closure["closure_identity"],
        "historical_auditors": len(historical), "legacy_dependency_count": 0, "files": files,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
