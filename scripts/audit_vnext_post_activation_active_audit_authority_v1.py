#!/usr/bin/env python3
"""Current self-contained post-activation active authority auditor."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json
from pathlib import Path

def module(name,path):s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def identity(v):return hashlib.sha256(canonical(v)).hexdigest()
def load(p):return json.loads(p.read_text(encoding="utf-8"))
def check(v,key):
 if v[key]!=identity({k:x for k,x in v.items() if k!=key}):raise RuntimeError("identity mismatch: "+key)
def audit(repo:Path,active:Path,rollback:Path,live:bool):
 build=module("authority_builder",repo/"scripts/build_vnext_post_activation_active_audit_authority_v1.py")
 manifest=load(repo/"docs/artifacts/vnext-post-activation-active-audit-authority-v1.json");check(manifest,"manifest_identity")
 if manifest["current_auditor_count"]!=1 or not manifest["exclusive_current_auditor"] or manifest["current_auditor"]!=build.CURRENT_AUDITOR:raise RuntimeError("current auditor cardinality failure")
 pred=load(repo/"docs/artifacts/vnext-active-authority-audit-manifest-v1.json");check(pred,"manifest_identity")
 if manifest["supersedes"]["manifest_identity"]!=pred["manifest_identity"]:raise RuntimeError("predecessor not superseded")
 hist=[x for x in manifest["historical_commit_only_auditors"] if x["path"]==build.PREDECESSOR_AUDITOR]
 if len(hist)!=1 or hist[0]["commit"]!=build.PREDECESSOR_COMMIT or hist[0]["sha256"]!=build.sha(repo/build.PREDECESSOR_AUDITOR):raise RuntimeError("predecessor historical classification failure")
 tests=manifest["historical_tests"]
 if len(tests)!=1 or tests[0]["path"]!=build.HISTORICAL_TEST or tests[0]["active_coverage_replacement"]!=build.CURRENT_AUDITOR or tests[0]["sha256"]!=build.sha(repo/build.HISTORICAL_TEST):raise RuntimeError("historical test classification failure")
 snap=manifest["coverage"]["pre_activation_invariant_snapshot"]
 if snap["identity"]!=identity(pred["invariants"]) or snap["keys"]!=sorted(pred["invariants"]):raise RuntimeError("pre-activation coverage snapshot failure")
 required={"ACTIVE_PRODUCT_LOCK","ACTIVE_STATE_AUTHORITY","ACTIVATION_RECEIPT","CANONICAL_ROLLBACK_MANIFEST","ACTIVE_ROOT_MANAGED_BYTES","ACTIVE_DEPENDENCY_GRAPH","R2_BYTES","PLATFORM_TREE","SQLITE_INTEGRITY","STARTUP","INTEGRATED_E2E_EXPORTED","ROLLBACK_RESTORE_FAULT_INJECTION","LEGACY_DEPENDENCY_COUNT_ZERO"}
 if set(manifest["coverage"]["post_activation_required_checks"])!=required:raise RuntimeError("post-activation coverage incomplete")
 if build.sha(active/"product-lock.json")!=build.LOCK_SHA:raise RuntimeError("active product lock mismatch")
 state=load(repo/"docs/artifacts/vnext-active-product-lock-successor-v1.json");receipt=load(repo/"docs/artifacts/vnext-activation-receipt-v1.json");rb=load(repo/"docs/artifacts/vnext-canonical-rollback-manifest-v1.json")
 check(state,"product_lock_identity");check(receipt,"activation_receipt_identity");check(rb,"rollback_manifest_identity")
 bindings=manifest["active_bindings"]
 if bindings!={"active_product_lock_sha256":build.LOCK_SHA,"active_state_authority_identity":state["product_lock_identity"],"activation_receipt_identity":receipt["activation_receipt_identity"],"rollback_manifest_identity":rb["rollback_manifest_identity"]}:raise RuntimeError("active binding mismatch")
 successor=module("successor_auditor",repo/"scripts/audit_vnext_active_state_attestation_rollback_v1.py")
 nested=successor.audit(repo,active,rollback,live)
 if nested["status"]!="PASS" or nested["blockers"]!=0:raise RuntimeError("successor audit failure")
 result={"schema":"vnext-post-activation-active-audit-authority-result-v1","status":"PASS","blockers":0,"active_audit_manifest_identity":manifest["manifest_identity"],"current_auditor":build.CURRENT_AUDITOR,"current_auditor_count":1,"predecessor_classification":"HISTORICAL_COMMIT_ONLY","historical_test_classification":"PRE_ACTIVATION_COMMIT_ONLY","pre_activation_coverage":"PRESERVED","post_activation_coverage":"COMPLETE","nested_successor_result_identity":nested["result_identity"],"r2_closure":nested["r2_closure"],"sqlite_integrity":nested["sqlite_integrity"],"legacy_dependency_count":nested["legacy_dependency_count"],"active_root_mutated":False,"rollback_root_mutated":False}
 result["result_identity"]=identity(result);return result
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--active-root",type=Path,required=True);p.add_argument("--rollback-root",type=Path,required=True);p.add_argument("--live",action="store_true");p.add_argument("--write-result",type=Path);a=p.parse_args();r=audit(a.repo,a.active_root,a.rollback_root,a.live);t=json.dumps(r,indent=2,sort_keys=True)+"\n";print(t,end="");
 if a.write_result:a.write_result.write_text(t,encoding="utf-8")
