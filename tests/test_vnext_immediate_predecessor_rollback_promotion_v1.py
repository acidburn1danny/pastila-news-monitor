import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def module():
 s=importlib.util.spec_from_file_location("b",R/"scripts/build_vnext_immediate_predecessor_rollback_promotion_v1.py");m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_identities_and_bindings():
 b=module();d=R/"docs/artifacts";spec={"vnext-immediate-predecessor-canonical-rollback-manifest-v3.json":"rollback_manifest_identity","vnext-immediate-predecessor-active-state-authority-v4.json":"active_state_authority_identity","vnext-immediate-predecessor-product-lock-successor-v1.json":"product_lock_identity"};v={}
 for n,k in spec.items():
  x=json.loads((d/n).read_text());v[n]=x;c=x.pop(k);assert c==b.ident(x);x[k]=c
 m=v["vnext-immediate-predecessor-canonical-rollback-manifest-v3.json"];a=v["vnext-immediate-predecessor-active-state-authority-v4.json"];l=v["vnext-immediate-predecessor-product-lock-successor-v1.json"]
 assert m["rollback_root"]==b.IMMEDIATE_ROOT and m["retired_root_references"]==[]
 assert m["prior_canonical_root"]["classification"]=="HISTORICAL_NON_CANONICAL_RETIREMENT_PENDING_SEPARATE_AUTHORITY"
 assert a["canonical_rollback"]["manifest_identity"]==m["rollback_manifest_identity"] and a["retired_root_references"]==[]
 assert l["activation_attestation"]["canonical_rollback_manifest_identity"]==m["rollback_manifest_identity"] and l["supersedes_product_lock_identity"]==b.ACTIVE_ID
def test_three_phase_result():
 r=json.loads((R/"docs/artifacts/vnext-immediate-predecessor-rollback-promotion-result-v1.json").read_text())
 assert r["status"]=="PASS" and r["blockers"]==0
 assert [r[x]["terminal"] for x in ("prospective_install","prospective_rollback","prospective_restore")]==["EXPORTED"]*3
 assert not r["active_root_modified"] and not r["rollback_roots_modified"] and not r["prior_root_deleted"]
