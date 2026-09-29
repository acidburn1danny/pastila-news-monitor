#!/usr/bin/env python3
"""Audit Policy and FINAL relational ownership integrity."""
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
    closure=load("vnext-policy-final-relational-ownership-integrity-repair-v1.json")
    for value,key in ((manifest,"manifest_identity"),(closure,"closure_identity")):
        assert value[key]==object_identity({k:v for k,v in value.items() if k!=key})
    assert manifest["bound_commit"]=="0f5890452c4ead7c0288c980fe085924cbe8422b"
    assert manifest["current_auditor"]=="scripts/audit_vnext_policy_final_relational_ownership_v1.py"
    invariants=manifest["invariants"]
    for key in ("policy_decision_relational_ownership","policy_session_relational_ownership","policy_transition_ownership","final_artifact_relational_ownership","final_transition_ownership"):
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
    orchestrator=(ROOT/"src/pastila_scout/vnext_product_orchestrator_v1.py").read_text(encoding="utf-8")
    final=(ROOT/"src/pastila_scout/vnext_core_final_v1.py").read_text(encoding="utf-8")
    for marker in ("policy decision row binding mismatch","policy-session row binding mismatch",'label="policy decision"'):
        assert marker in orchestrator
    for marker in ("persisted FINAL artifact-row binding mismatch",'label="FINAL assembly"','label="FINAL export"'):
        assert marker in final
    findings=scan_legacy_dependencies(ROOT/"src/pastila_scout");active_names={Path(v).name for v in modules}
    assert [f for f in findings if f["path"] in active_names]==[]
    lock=Path("/root/pastila-vnext/v1/product-lock.json")
    if lock.exists():assert hashlib.sha256(lock.read_bytes()).hexdigest()==LOCK_SHA
    assert not Path("/root/pastila-vnext/v2").exists()
    assert SCHEMA_VERSION==6
    assert closure["validation"]["suite"]=="233_PASS"
    assert closure["validation"]["dedicated_fault_injection"]=="123_PASS"
    assert closure["invariants"]["audit_streak"]=="0/2"
    print(json.dumps({"status":"PASS","closure_identity":closure["closure_identity"],"manifest_identity":manifest["manifest_identity"],"suite":"233_PASS","dedicated_fault_injection":"123_PASS","legacy_dependency_count":0,"schema_version":SCHEMA_VERSION},sort_keys=True))
if __name__=="__main__":main()
