import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];A=R/"docs/artifacts"
def mod():s=importlib.util.spec_from_file_location("b",R/"scripts/build_vnext_canonical_only_recovery_topology_v1.py");m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def load(n):return json.loads((A/n).read_text())
def test_authority_identities_and_canonical_only_semantics():
 b=mod();spec={"vnext-canonical-only-current-activation-receipt-v5.json":"activation_receipt_identity","vnext-canonical-only-current-active-state-authority-v5.json":"active_state_authority_identity","vnext-canonical-only-rollback-manifest-v8.json":"rollback_manifest_identity","vnext-canonical-only-product-lock-v8.json":"product_lock_identity"};d={}
 for n,k in spec.items():
  x=load(n);claimed=x.pop(k);assert claimed==b.ident(x);x[k]=claimed;d[n]=x
 m=d["vnext-canonical-only-rollback-manifest-v8.json"];a=d["vnext-canonical-only-current-active-state-authority-v5.json"];r=d["vnext-canonical-only-current-activation-receipt-v5.json"];l=d["vnext-canonical-only-product-lock-v8.json"]
 assert m["rollback_root"]==a["canonical_rollback"]["root"]==r["rollback"]["canonical_root"]==b.C[0]
 assert m["recovery_topology"]["physical_root_count"]==1 and m["recovery_topology"]["historical_physical_roots_required"]==0
 assert a["recovery_topology"]=="ACTIVE_TO_CANONICAL_ONLY" and l["rollback_authority_transition"]["topology"]=="ACTIVE_TO_CANONICAL_ONLY"
 blob="\n".join(json.dumps(x,sort_keys=True) for x in d.values())
 assert all(x[1] not in blob for x in b.H)
 for e in m["historical_evidence"]:assert e["evidence_role"]=="CONTENT_ADDRESSED_PROVENANCE_ONLY" and e["physical_root_required"] is False and e["reconstructible"] is True
def test_prospective_install_rollback_restore_and_preservation():
 r=load("vnext-canonical-only-recovery-topology-result-v1.json")
 assert r["status"]=="PASS" and r["blockers"]==0 and r["recovery_topology"]=="ACTIVE_TO_CANONICAL_ONLY"
 assert [r[x]["terminal"] for x in ("prospective_install","prospective_rollback","prospective_restore")]==["EXPORTED"]*3
 assert [r[x]["startup"] for x in ("prospective_install","prospective_rollback","prospective_restore")]==["PASS_STARTUP_READY"]*3
 assert r["prospective_install"]["audit"]==r["prospective_restore"]["audit"]=="PASS"
 assert r["canonical_rollback_integrity"]=="PASS" and r["protected_root_identity_preservation"]=="PASS"
 assert not r["active_root_modified"] and not r["rollback_roots_modified"] and not r["retirement_executed"]
 assert r["legacy_dependency_count"]==0 and r["retirement_eligible_bytes"]==99918413824
