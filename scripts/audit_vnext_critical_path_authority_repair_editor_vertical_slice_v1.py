from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = (
    "src/pastila_scout/vnext_workflow_v1.py",
    "src/pastila_scout/vnext_state_sqlite_v1.py",
    "src/pastila_scout/vnext_scout_production_v1.py",
    "src/pastila_scout/vnext_sourcepacket_binding_v1.py",
    "src/pastila_scout/vnext_editor_vertical_slice_v1.py",
    "docs/artifacts/vnext-active-product-workflow-state-contract-v2.json",
    "docs/artifacts/vnext-consolidated-operational-state-sqlite-boundary-v2-contract.json",
    "docs/artifacts/vnext-critical-path-authority-repair-editor-vertical-slice-v1.json",
    "docs/artifacts/vnext-critical-path-authority-repair-editor-vertical-slice-v1-fixture.json",
    "docs/vnext-critical-path-authority-repair-editor-vertical-slice-v1.md",
    "tests/test_vnext_shared_foundation_workflow_boundary_v1.py",
    "tests/test_vnext_consolidated_operational_state_sqlite_boundary_v1.py",
    "tests/test_vnext_critical_path_authority_repair_editor_vertical_slice_v1.py",
    "scripts/audit_vnext_critical_path_authority_repair_editor_vertical_slice_v1.py",
)


def digest(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    for name in SCOPE:
        if not (ROOT / name).is_file(): raise SystemExit(f"BLOCKER missing scope file: {name}")
    authority = json.loads((ROOT / SCOPE[7]).read_text(encoding="utf-8"))
    workflow = json.loads((ROOT / SCOPE[5]).read_text(encoding="utf-8"))
    sqlite_contract = json.loads((ROOT / SCOPE[6]).read_text(encoding="utf-8"))
    transitions = {tuple(item) for item in workflow["transitions"]}
    required = {("EDITOR_PENDING", "STRUCTURAL_FAIL"), ("STRUCTURAL_FAIL", "SOURCE_FALLBACK"), ("STRUCTURAL_FAIL", "ABSTAINED"), ("EDITOR_DRAFT_READY", "FACTUAL_REVIEW_PENDING")}
    if not required <= transitions or "STRUCTURAL_PASS" in workflow["states"]:
        raise SystemExit("BLOCKER workflow repair absent or inconsistent")
    kinds = set(sqlite_contract["consolidations"]["workflow_artifacts"])
    if not {"EDITOR_DRAFT", "ACCEPTED_SETUP", "SOURCE_FALLBACK", "ABSTAINED"} <= kinds:
        raise SystemExit("BLOCKER acceptance artifacts cannot be persisted")
    invariants = {"status": "ISOLATED_NOT_ACTIVE", "active_integration": False, "product_lock_replaced": False, "product_root_modified": False, "model_relocated": False, "model_loaded": False, "inference_performed": False, "training_performed": False, "legacy_dependency_count": 0, "stop_all_candidates": True}
    if any(authority.get(key) != value for key, value in invariants.items()):
        raise SystemExit("BLOCKER product invariant drift")
    sys.path.insert(0, str(ROOT / "src"))
    from pastila_scout.vnext_foundation_v1 import object_identity
    if workflow.get("authority_identity") != object_identity({key: value for key, value in workflow.items() if key != "authority_identity"}):
        raise SystemExit("BLOCKER workflow authority identity mismatch")
    if sqlite_contract.get("authority_identity") != object_identity({key: value for key, value in sqlite_contract.items() if key != "authority_identity"}):
        raise SystemExit("BLOCKER SQLite authority identity mismatch")
    if authority.get("closure_identity") != object_identity({key: value for key, value in authority.items() if key != "closure_identity"}):
        raise SystemExit("BLOCKER vertical-slice closure identity mismatch")
    editor = (ROOT / SCOPE[4]).read_text(encoding="utf-8")
    if "editor-vnext-source-packet" in editor or "vnext_sourcepacket_binding" in editor:
        raise SystemExit("BLOCKER dual SourcePacket schema remains active")
    tree = ast.parse(editor)
    imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    allowed = {"__future__", "collections.abc", "dataclasses", "pathlib", "typing", "peft", "transformers", "vnext_foundation_v1", "vnext_r2_consolidation_binding_v1", "vnext_scout_production_v1", "vnext_state_sqlite_v1", "vnext_workflow_v1"}
    if imports - allowed: raise SystemExit(f"BLOCKER hidden import: {sorted(imports - allowed)}")
    forbidden = ("/root/pf9-", "C:\\pf9", "F:\\pt")
    for name in SCOPE[:5]:
        text = (ROOT / name).read_text(encoding="utf-8", errors="ignore")
        if any(value.casefold() in text.casefold() for value in forbidden):
            raise SystemExit(f"BLOCKER forbidden dependency: {name}")
    if "AcceptedSetup(".casefold() in editor.casefold():
        raise SystemExit("BLOCKER EditorDraft acceptance bypass")
    result = {"status": "PASS", "scope": len(SCOPE), "legacy_dependency_count": 0, "files": {name: digest(ROOT / name) for name in SCOPE}}
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__": sys.exit(main())
