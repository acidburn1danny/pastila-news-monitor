#!/usr/bin/env python3
"""Audit SourcePacket and EditorDraft relational ownership integrity."""
from __future__ import annotations
import ast,hashlib,json
from pathlib import Path
from pastila_scout.vnext_foundation_v1 import object_identity,scan_legacy_dependencies
from pastila_scout.vnext_state_sqlite_v1 import SCHEMA_VERSION
ROOT=Path(__file__).resolve().parents[1];ART=ROOT/"docs/artifacts"
LOCK_SHA="2ddc484171f3b58f0f10ce4c4c73c1db51323d5c545320c578dc17ebb3edb4e6"
def load(name):
    value=json.loads((ART/name).read_text(encoding="utf-8"));assert isinstance(value,dict);return value
def main():
    manifest=load("vnext-active-authority-audit-manifest-v1.json")
    closure=load("vnext-sourcepacket-editor-draft-relational-ownership-integrity-repair-v1.json")
    for value,key in ((manifest,"manifest_identity"),(closure,"closure_identity")):
        assert value[key]==object_identity({k:v for k,v in value.items() if k!=key})
    assert manifest["bound_commit"]=="dfdb2bf285b4e21ab16a39cc3740f08a5089b377"
    assert manifest["current_auditor"]=="scripts/audit_vnext_sourcepacket_editor_draft_relational_ownership_v1.py"
    invariants=manifest["invariants"]
    for key in ("source_packet_relational_ownership","editor_draft_relational_ownership","editor_to_factual_transition_ownership"):
        assert invariants[key] is True
    assert invariants["active_integration"] is False
    assert invariants["product_lock_replaced"] is False
    assert invariants["legacy_dependency_count"]==0
    modules=set(manifest["active_runtime_modules"]);discovered=set()
    for relative in modules:
        tree=ast.parse((ROOT/relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom) and node.level==1 and node.module and node.module.startswith("vnext_"):
                candidate=f"src/pastila_scout/{node.module}.py"
                if (ROOT/candidate).exists():discovered.add(candidate)
    assert discovered<=modules,sorted(discovered-modules)
    source=(ROOT/"src/pastila_scout/vnext_product_orchestrator_v1.py").read_text(encoding="utf-8")
    for marker in ("SourcePacket row binding mismatch", 'label="SourcePacket"', "EditorDraft artifact binding mismatch", 'label="EditorDraft"', 'label="EditorDraft factual review"'):
        assert marker in source
    findings=scan_legacy_dependencies(ROOT/"src/pastila_scout");active_names={Path(v).name for v in modules}
    assert [f for f in findings if f["path"] in active_names]==[]
    lock=Path("/root/pastila-vnext/v1/product-lock.json")
    if lock.exists():assert hashlib.sha256(lock.read_bytes()).hexdigest()==LOCK_SHA
    assert not Path("/root/pastila-vnext/v2").exists()
    assert SCHEMA_VERSION==6
    assert closure["validation"]["suite"]=="187_PASS"
    assert closure["validation"]["dedicated_fault_injection"]=="77_PASS"
    assert closure["invariants"]["audit_streak"]=="0/2"
    print(json.dumps({"status":"PASS","closure_identity":closure["closure_identity"],"manifest_identity":manifest["manifest_identity"],"suite":"187_PASS","dedicated_fault_injection":"77_PASS","legacy_dependency_count":0,"schema_version":SCHEMA_VERSION},sort_keys=True))
if __name__=="__main__":main()
