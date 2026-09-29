#!/usr/bin/env python3
"""Audit SCOUT workflow-event ownership and grouping lineage repair."""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from pastila_scout.vnext_foundation_v1 import object_identity, scan_legacy_dependencies
from pastila_scout.vnext_state_sqlite_v1 import MIGRATION_7, SCHEMA_VERSION

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
    sqlite = load("vnext-consolidated-operational-state-sqlite-boundary-v7-contract.json")
    source = load("vnext-canonical-sourcepacket-v1-contract.json")
    closure = load("vnext-scout-workflow-event-ownership-grouping-lineage-repair-v1.json")
    identity(manifest, "manifest_identity")
    identity(sqlite, "authority_identity")
    identity(source, "authority_identity")
    identity(closure, "closure_identity")

    assert manifest["bound_commit"] == "fbb7dfcd1024d90fc0d63d3b24b611bba56f8827"
    assert manifest["current_auditor"] == (
        "scripts/audit_vnext_scout_workflow_event_ownership_grouping_lineage_repair_v1.py"
    )
    assert manifest["active_authorities"]["sqlite"] == {
        "identity": sqlite["authority_identity"],
        "identity_key": "authority_identity",
        "path": "docs/artifacts/vnext-consolidated-operational-state-sqlite-boundary-v7-contract.json",
    }
    assert manifest["active_authorities"]["source_packet"]["identity"] == source["authority_identity"]
    invariants = manifest["invariants"]
    for key in (
        "workflow_event_relational_ownership",
        "grouping_transition_relational_ownership",
        "global_event_cross_workflow_reuse",
        "canonical_source_packet",
        "explicit_user_selection_authority",
    ):
        assert invariants[key] is True
    assert invariants["active_integration"] is False
    assert invariants["product_lock_replaced"] is False
    assert invariants["legacy_dependency_count"] == 0
    assert invariants["stop_all_candidates"] is True
    assert invariants["voice"] == "DISABLED_UNTIL_PROMOTION"

    assert SCHEMA_VERSION == 7
    assert len(MIGRATION_7) == 1
    assert "CREATE TABLE workflow_events" in MIGRATION_7[0]
    assert "PRIMARY KEY(workflow_identity,event_identity)" in MIGRATION_7[0]
    assert "UNIQUE(workflow_identity,position)" in MIGRATION_7[0]
    assert sqlite["migration"]["from"] == 6
    assert sqlite["migration"]["to"] == 7
    assert sqlite["persistence"]["selection_scope"] == "CURRENT_WORKFLOW_ONLY"
    assert closure["validation"] == {
        "vnext_suite": "324_PASS",
        "dedicated": "14_PASS",
        "self_contained_auditor": "PASS",
    }
    assert closure["invariants"]["audit_streak"] == "0/2"

    scout = (ROOT / "src/pastila_scout/vnext_scout_production_v1.py").read_text(encoding="utf-8")
    orchestrator = (ROOT / "src/pastila_scout/vnext_product_orchestrator_v1.py").read_text(encoding="utf-8")
    for marker in (
        "INSERT INTO workflow_events VALUES(?,?,?,?)",
        "global event identity conflicts with grouping",
        "global event capture membership conflict",
        "def validate_workflow_event_membership(",
        "workflow event membership missing",
        "grouping transition ownership is absent or ambiguous",
        "grouping transition receipt binding mismatch",
        "event is not owned uniquely by workflow grouping",
    ):
        assert marker in scout
    assert "validate_workflow_event_membership(" in orchestrator

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
        "sqlite_authority_identity": sqlite["authority_identity"],
        "closure_identity": closure["closure_identity"],
        "manifest_identity": manifest["manifest_identity"],
        "suite": "324_PASS",
        "dedicated": "14_PASS",
        "legacy_dependency_count": 0,
        "schema_version": SCHEMA_VERSION,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
