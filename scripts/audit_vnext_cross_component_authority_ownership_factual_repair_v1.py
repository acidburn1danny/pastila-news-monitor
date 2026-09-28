"""Cross-component audit for the bounded VNext authority/ownership repair."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.vnext_foundation_v1 import object_identity, scan_legacy_dependencies
from pastila_scout.vnext_state_sqlite_v1 import MIGRATION_3, SCHEMA_VERSION
from pastila_scout.vnext_workflow_v1 import STATES, TRANSITIONS

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
SCOPE = (
    "docs/artifacts/vnext-active-product-workflow-state-contract-v3.json",
    "docs/artifacts/vnext-consolidated-operational-state-sqlite-boundary-v3-contract.json",
    "docs/artifacts/vnext-cross-component-authority-ownership-factual-repair-v1-fixture.json",
    "docs/artifacts/vnext-cross-component-authority-ownership-factual-repair-v1.json",
    "docs/vnext-cross-component-authority-ownership-factual-repair-v1.md",
    "scripts/audit_vnext_cross_component_authority_ownership_factual_repair_v1.py",
    "src/pastila_scout/vnext_editor_vertical_slice_v1.py",
    "src/pastila_scout/vnext_factual_acceptance_v1.py",
    "src/pastila_scout/vnext_state_sqlite_v1.py",
    "src/pastila_scout/vnext_workflow_v1.py",
    "tests/test_vnext_consolidated_operational_state_sqlite_boundary_v1.py",
    "tests/test_vnext_critical_path_authority_repair_editor_vertical_slice_v1.py",
    "tests/test_vnext_cross_component_authority_ownership_factual_repair_v1.py",
    "tests/test_vnext_shared_foundation_workflow_boundary_v1.py",
)


def load(name: str) -> dict[str, object]:
    value = json.loads((ART / name).read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise TypeError(name)
    return value


def identity(value: dict[str, object], key: str) -> None:
    assert value[key] == object_identity({k: v for k, v in value.items() if k != key})


def main() -> None:
    workflow = load("vnext-active-product-workflow-state-contract-v3.json")
    sqlite = load("vnext-consolidated-operational-state-sqlite-boundary-v3-contract.json")
    fixture = load("vnext-cross-component-authority-ownership-factual-repair-v1-fixture.json")
    closure = load("vnext-cross-component-authority-ownership-factual-repair-v1.json")
    identity(workflow, "authority_identity"); identity(sqlite, "authority_identity")
    identity(fixture, "fixture_identity"); identity(closure, "closure_identity")
    assert set(map(tuple, workflow["transitions"])) == set(TRANSITIONS)
    assert set(workflow["states"]) == set(STATES)
    assert sqlite["authority"]["workflow_v3_identity"] == workflow["authority_identity"]
    assert closure["authority_bindings"]["workflow_v3_identity"] == workflow["authority_identity"]
    assert closure["authority_bindings"]["sqlite_v3_identity"] == sqlite["authority_identity"]
    assert closure["authority_bindings"]["fixture_identity"] == fixture["fixture_identity"]
    assert SCHEMA_VERSION == 3 and any("PRIMARY KEY(workflow_identity,artifact_identity)" in statement for statement in MIGRATION_3)
    assert ("STRUCTURAL_FAIL", "FACTUAL_REVIEW_PENDING") in TRANSITIONS
    assert ("STRUCTURAL_FAIL", "SOURCE_FALLBACK") not in TRANSITIONS
    editor = (ROOT / "src/pastila_scout/vnext_editor_vertical_slice_v1.py").read_text(encoding="utf-8")
    factual = (ROOT / "src/pastila_scout/vnext_factual_acceptance_v1.py").read_text(encoding="utf-8")
    assert "INSERT OR IGNORE INTO workflow_artifacts" not in editor + factual
    assert "EXPLICIT_TRUSTED_REVIEW_SESSION" in factual
    assert "?" not in fixture["romanian_text"] and "ș" in fixture["romanian_text"] and "ț" in fixture["romanian_text"]
    invariants = closure["invariants"]
    assert not invariants["active_integration"] and not invariants["product_lock_replaced"]
    assert not invariants["orchestrator_implemented"] and not invariants["final_implemented"]
    assert invariants["voice"] == "DISABLED_UNTIL_PROMOTION" and invariants["stop_all_candidates"]
    relevant = [f for f in scan_legacy_dependencies(ROOT / "src/pastila_scout") if any(name in f["path"] for name in ("vnext_workflow_v1.py", "vnext_state_sqlite_v1.py", "vnext_editor_vertical_slice_v1.py", "vnext_factual_acceptance_v1.py"))]
    assert relevant == [] and invariants["legacy_dependency_count"] == 0
    files = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SCOPE}
    print(json.dumps({"status":"PASS","scope":len(SCOPE),"workflow_identity":workflow["authority_identity"],"sqlite_identity":sqlite["authority_identity"],"fixture_identity":fixture["fixture_identity"],"closure_identity":closure["closure_identity"],"legacy_dependency_count":0,"files":files},sort_keys=True))


if __name__ == "__main__": main()
