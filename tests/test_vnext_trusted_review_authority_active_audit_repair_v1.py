from __future__ import annotations

import ast
import json
from pathlib import Path

from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_state_sqlite_v1 import MIGRATION_4, MIGRATION_5, MIGRATION_6, SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/artifacts/vnext-active-authority-audit-manifest-v1.json"
SQLITE = ROOT / "docs/artifacts/vnext-consolidated-operational-state-sqlite-boundary-v6-contract.json"


def test_schema_v5_persists_replay_safe_review_authority():
    assert SCHEMA_VERSION == 6
    joined = "\n".join(MIGRATION_4 + MIGRATION_5 + MIGRATION_6)
    assert "CREATE TABLE review_sessions" in joined
    assert "status IN ('OPEN','CONSUMED')" in joined
    assert "review_sessions_open_input" in joined


def test_active_manifest_is_content_addressed_and_has_one_current_auditor():
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert value["manifest_identity"] == object_identity(
        {key: item for key, item in value.items() if key != "manifest_identity"}
    )
    assert value["current_auditor"] == "scripts/audit_vnext_final_export_receipt_transition_binding_v1.py"
    assert len(value["historical_commit_only_auditors"]) == 8
    assert all(item["commit"] for item in value["historical_commit_only_auditors"])


def test_active_runtime_excludes_compatibility_adapter_and_hidden_imports():
    value = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert "src/pastila_scout/vnext_sourcepacket_binding_v1.py" not in value["active_runtime_modules"]
    excluded = {item.get("path") for item in value["excluded_from_active_graph"]}
    assert "src/pastila_scout/vnext_sourcepacket_binding_v1.py" in excluded
    for relative in value["active_runtime_modules"]:
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        imports = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        }
        assert "vnext_sourcepacket_binding_v1" not in imports


def test_successor_sqlite_authority_is_content_addressed():
    value = json.loads(SQLITE.read_text(encoding="utf-8"))
    assert value["authority_identity"] == object_identity(
        {key: item for key, item in value.items() if key != "authority_identity"}
    )
    assert value["persistence"]["review_authority"] == "PERSISTED_WORKFLOW_BOUND_SINGLE_USE_SESSION"
    assert value["persistence"]["self_asserted_session_identity_accepted"] is False
