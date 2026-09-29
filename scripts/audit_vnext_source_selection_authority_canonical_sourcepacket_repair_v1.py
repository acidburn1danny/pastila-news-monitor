#!/usr/bin/env python3
"""Audit the canonical SourcePacket and explicit selection authority repair."""
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


def identity(value: dict[str, object], key: str) -> None:
    assert value[key] == object_identity({k: v for k, v in value.items() if k != key})


def main() -> None:
    manifest = load("vnext-active-authority-audit-manifest-v1.json")
    contract = load("vnext-canonical-sourcepacket-v1-contract.json")
    closure = load("vnext-source-selection-authority-canonical-sourcepacket-repair-v1.json")
    identity(manifest, "manifest_identity")
    identity(contract, "authority_identity")
    identity(closure, "closure_identity")

    assert manifest["bound_commit"] == "07c8c4cbc7b050343a51f1be4bbb3c8d7f478c28"
    assert manifest["current_auditor"] == (
        "scripts/audit_vnext_source_selection_authority_canonical_sourcepacket_repair_v1.py"
    )
    source_authority = manifest["active_authorities"]["source_packet"]
    assert source_authority == {
        "identity": contract["authority_identity"],
        "identity_key": "authority_identity",
        "path": "docs/artifacts/vnext-canonical-sourcepacket-v1-contract.json",
    }
    invariants = manifest["invariants"]
    assert invariants["canonical_source_packet"] is True
    assert invariants["explicit_user_selection_authority"] is True
    assert invariants["selection_transition_relational_ownership"] is True
    assert invariants["active_integration"] is False
    assert invariants["product_lock_replaced"] is False
    assert invariants["legacy_dependency_count"] == 0
    assert closure["validation"] == {
        "vnext_suite": "310_PASS",
        "dedicated": "10_PASS",
        "self_contained_auditor": "PASS",
    }
    assert closure["invariants"]["audit_streak"] == "0/2"
    assert contract["selection_authority"] == "EXPLICIT_USER_EVENT_ID"
    assert contract["selection_receipt"]["required_transition"] == "GROUPED_TO_SELECTED"
    assert contract["historical_adapter_active"] is False

    scout = (ROOT / "src/pastila_scout/vnext_scout_production_v1.py").read_text(encoding="utf-8")
    orchestrator = (ROOT / "src/pastila_scout/vnext_product_orchestrator_v1.py").read_text(encoding="utf-8")
    for marker in (
        "vnext-source-selection-receipt",
        "explicit selection actor required",
        "explicit selection authorization identity required",
        '"selection_authority": "EXPLICIT_USER_EVENT_ID"',
        "transition_receipt_identity",
    ):
        assert marker in scout
    for marker in (
        "source selection receipt",
        'previous_state="GROUPED"',
        'resulting_state="SELECTED"',
        'operation_identity="scout:select"',
        "SourcePacket selection transition receipt binding mismatch",
    ):
        assert marker in orchestrator

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
    excluded = {
        item.get("path"): item.get("reason")
        for item in manifest["excluded_from_active_graph"]
        if "path" in item
    }
    assert excluded["src/pastila_scout/vnext_sourcepacket_binding_v1.py"] == (
        "HISTORICAL_AUTHORITY_UPGRADING_ADAPTER_SUPERSEDED_BY_CANONICAL_SOURCE_PACKET"
    )

    findings = scan_legacy_dependencies(ROOT / "src/pastila_scout")
    active_names = {Path(value).name for value in modules}
    assert [item for item in findings if item["path"] in active_names] == []
    lock = Path("/root/pastila-vnext/v1/product-lock.json")
    if lock.exists():
        assert hashlib.sha256(lock.read_bytes()).hexdigest() == LOCK_SHA
    assert not Path("/root/pastila-vnext/v2").exists()
    assert SCHEMA_VERSION == 6
    print(json.dumps({
        "status": "PASS",
        "authority_identity": contract["authority_identity"],
        "closure_identity": closure["closure_identity"],
        "manifest_identity": manifest["manifest_identity"],
        "suite": "310_PASS",
        "dedicated": "10_PASS",
        "legacy_dependency_count": 0,
        "schema_version": SCHEMA_VERSION,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
