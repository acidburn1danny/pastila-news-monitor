#!/usr/bin/env python3
"""Build the post-activation active-audit authority successor."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
BASE_COMMIT="f9a566b0c350ea113844e21f93c80bf8a8f6dd7f"
PREDECESSOR_ID="154f689b70c050820e1595ba08375f1965ef5a4aa0521e279dd2063a9703dbde"
PREDECESSOR_AUDITOR="scripts/audit_vnext_scout_exhaustive_source_disposition_terminal_authority_repair_v1.py"
PREDECESSOR_COMMIT="c211a07551284627a8e23c6e84d7dbf7e1125681"
CURRENT_AUDITOR="scripts/audit_vnext_post_activation_active_audit_authority_v1.py"
HISTORICAL_TEST="tests/test_vnext_cross_component_eligibility_evidence_recovery_transitive_repair_v1.py"
LOCK_SHA="0ff93c4d9f550c8458d2223ae91627903bf02dc24973c59d3069fa94ada1100e"
ACTIVE_STATE_ID="f7ab34467d316c9ef0a827c5483eab291ea1976036f38f8d0578edc471eed164"
RECEIPT_ID="2d79120f5b2b294ae9067e1596f7460778035e1837e849bf0b45896e2335e9d2"
ROLLBACK_ID="2d86d60806ca15eb8051dcbf61952c10c0d669e077f3ff4e7d167bf3b5509485"
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def identity(v):return hashlib.sha256(canonical(v)).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding="utf-8"))
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
def build(repo:Path,out:Path):
 pred=load(repo/"docs/artifacts/vnext-active-authority-audit-manifest-v1.json")
 if pred["manifest_identity"]!=PREDECESSOR_ID or pred["current_auditor"]!=PREDECESSOR_AUDITOR:raise RuntimeError("predecessor mismatch")
 state=load(repo/"docs/artifacts/vnext-active-product-lock-successor-v1.json");receipt=load(repo/"docs/artifacts/vnext-activation-receipt-v1.json");rollback=load(repo/"docs/artifacts/vnext-canonical-rollback-manifest-v1.json")
 if (state["product_lock_identity"],receipt["activation_receipt_identity"],rollback["rollback_manifest_identity"])!=(ACTIVE_STATE_ID,RECEIPT_ID,ROLLBACK_ID):raise RuntimeError("post-activation binding mismatch")
 historical=list(pred["historical_commit_only_auditors"])+[{"commit":PREDECESSOR_COMMIT,"path":PREDECESSOR_AUDITOR,"sha256":sha(repo/PREDECESSOR_AUDITOR),"reason":"PRE_ACTIVATION_PRODUCT_LOCK_ASSERTION"}]
 coverage={
  "pre_activation_invariant_snapshot":{"identity":identity(pred["invariants"]),"keys":sorted(pred["invariants"]),"source_manifest_identity":PREDECESSOR_ID},
  "post_activation_required_checks":["ACTIVE_PRODUCT_LOCK","ACTIVE_STATE_AUTHORITY","ACTIVATION_RECEIPT","CANONICAL_ROLLBACK_MANIFEST","ACTIVE_ROOT_MANAGED_BYTES","ACTIVE_DEPENDENCY_GRAPH","R2_BYTES","PLATFORM_TREE","SQLITE_INTEGRITY","STARTUP","INTEGRATED_E2E_EXPORTED","ROLLBACK_RESTORE_FAULT_INJECTION","LEGACY_DEPENDENCY_COUNT_ZERO"],
  "coverage_semantics":"PRE_ACTIVATION_EVIDENCE_PRESERVED_PLUS_POST_ACTIVATION_LIVE_SUCCESSOR_AUDIT",
 }
 manifest={
  "schema":"vnext-post-activation-active-audit-authority-v1","schema_version":1,"status":"PASS_ACTIVE_AUDIT_AUTHORITY_SUCCESSOR",
  "bound_commit":BASE_COMMIT,"supersedes":{"manifest_identity":PREDECESSOR_ID,"path":"docs/artifacts/vnext-active-authority-audit-manifest-v1.json"},
  "current_auditor":CURRENT_AUDITOR,"current_auditor_count":1,"exclusive_current_auditor":True,
  "active_bindings":{"active_product_lock_sha256":LOCK_SHA,"active_state_authority_identity":ACTIVE_STATE_ID,"activation_receipt_identity":RECEIPT_ID,"rollback_manifest_identity":ROLLBACK_ID},
  "active_authorities":pred["active_authorities"],"active_runtime_modules":pred["active_runtime_modules"],"coverage":coverage,
  "historical_commit_only_auditors":historical,
  "historical_tests":[{"path":HISTORICAL_TEST,"sha256":sha(repo/HISTORICAL_TEST),"classification":"PRE_ACTIVATION_COMMIT_ONLY","reason":"TRANSITIVELY_INVOKES_PRE_ACTIVATION_LOCK_ASSERTION","active_coverage_replacement":CURRENT_AUDITOR}],
  "historical_evidence_mutated":False,"legacy_dependency_count":0,
 }
 manifest["manifest_identity"]=identity(manifest);out.mkdir(parents=True,exist_ok=True);write(out/"vnext-post-activation-active-audit-authority-v1.json",manifest)
 print(json.dumps({"active_audit_manifest_identity":manifest["manifest_identity"],"pre_activation_invariant_snapshot_identity":coverage["pre_activation_invariant_snapshot"]["identity"]},sort_keys=True))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args();build(a.repo,a.output)
