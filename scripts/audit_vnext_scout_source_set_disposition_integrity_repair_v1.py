#!/usr/bin/env python3
"""Audit typed SourceSet authority and exhaustive capture dispositions."""
from __future__ import annotations

import ast
import hashlib
import inspect
import json
from pathlib import Path

from pastila_scout.vnext_foundation_v1 import object_identity, scan_legacy_dependencies
from pastila_scout.vnext_product_orchestrator_v1 import ProductOrchestrator
from pastila_scout.vnext_scout_production_v1 import ValidatedSourceSet
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
    sqlite = load("vnext-consolidated-operational-state-sqlite-boundary-v7-contract.json")
    source = load("vnext-canonical-sourcepacket-v1-contract.json")
    closure = load("vnext-scout-source-set-disposition-integrity-repair-v1.json")
    for value, key in (
        (manifest, "manifest_identity"),
        (sqlite, "authority_identity"),
        (source, "authority_identity"),
        (closure, "closure_identity"),
    ):
        identity(value, key)

    assert manifest["bound_commit"] == "439b39fa671df22ab7fbc69e4818a9d35e3a6976"
    assert manifest["current_auditor"] == (
        "scripts/audit_vnext_scout_source_set_disposition_integrity_repair_v1.py"
    )
    invariants = manifest["invariants"]
    for key in (
        "validated_typed_source_set_authority",
        "exhaustive_per_source_capture_dispositions",
        "capture_provenance_source_definition_binding",
        "capture_batch_content_addressed_authority",
        "capture_to_grouping_transitive_lineage",
        "canonical_workflow_transition_recovery",
    ):
        assert invariants[key] is True
    assert invariants["active_integration"] is False
    assert invariants["product_lock_replaced"] is False
    assert invariants["legacy_dependency_count"] == 0
    assert invariants["stop_all_candidates"] is True
    assert invariants["voice"] == "DISABLED_UNTIL_PROMOTION"

    assert SCHEMA_VERSION == 7
    assert closure["authority"]["schema_migration"] is False
    assert closure["authority"]["source_registry_semantics"] == "CURRENT_NON_AUTHORITATIVE_REGISTRY"
    assert closure["authority"]["sqlite_v7_identity"] == sqlite["authority_identity"]
    assert closure["validation"] == {
        "dedicated": "17_PASS",
        "self_contained_auditor": "PASS",
        "vnext_suite": "357_PASS",
    }
    assert closure["invariants"]["audit_streak"] == "0/2"

    parameters = inspect.signature(ProductOrchestrator.capture_and_group).parameters
    assert "source_set" in parameters
    assert "sources_identity" not in parameters
    assert "sources" not in parameters
    assert "source_set_identity" in ValidatedSourceSet.__annotations__

    scout = (ROOT / "src/pastila_scout/vnext_scout_production_v1.py").read_text(encoding="utf-8")
    for marker in (
        "source-set identity mismatch",
        "capture provenance conflicts with SourceDefinition",
        "capture failures conflict with validated SourceSet",
        "source cannot be captured and failed",
        "SourceSet disposition binding mismatch",
        "NO_ELIGIBLE_ENTRIES",
        "source_set_reference",
        "blobs/source-sets",
    ):
        assert marker in scout

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
        "closure_identity": closure["closure_identity"],
        "manifest_identity": manifest["manifest_identity"],
        "suite": "357_PASS",
        "dedicated": "17_PASS",
        "legacy_dependency_count": 0,
        "schema_version": SCHEMA_VERSION,
        "schema_migration": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
