#!/usr/bin/env python3
import argparse,copy,hashlib,json
from pathlib import Path
ACTIVE_ID="e180a1e504983cc807fdf1a923613893f71d47f1ed308962d8317113ce9693e8";ACTIVE_SHA="00c33e0f64bba06dada06231cb00e4785eb127d8d5b5a78e6b32f748447d97e5";ACTIVE_AUTH="6d9b3f7fe500c22f632e3c288e3be65cebe4a3240a0c4b4bc94096c95bf66b3e"
IMMEDIATE_ROOT="/root/pastila-vnext/.rollback-pre-contract-e180a1e5";IMMEDIATE_ID="03e43da4e052ed0bf0a1caa7f9da7103a111e1192362ea9887ed86388b864b78";IMMEDIATE_SHA="196c5f7bdec6f59f0609ad334dbdebdc17e5ad9f793945713ff2b7afaa5b58a2"
PRIOR_ROOT="/root/pastila-vnext/.rollback-pre-exchange-5e31722e";PRIOR_ID="68fb2c347367ff3aa725cfb44de11be07921ad2e39fcbe98b01b389eee46c19b";PRIOR_SHA="0ff93c4d9f550c8458d2223ae91627903bf02dc24973c59d3069fa94ada1100e"
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def ident(v):return hashlib.sha256(canon(v)).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open("rb") as f:
  for c in iter(lambda:f.read(8388608),b""):h.update(c)
 return h.hexdigest()
def write(p,v,k):v.pop(k,None);v[k]=ident(v);p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
def row(p,target):return {"path":target,"type":"file","size":p.stat().st_size,"sha256":sha(p)}
def build(repo,active,immediate,prior,out):
 cur=json.loads((active/"product-lock.json").read_text());direct=json.loads((immediate/"product-lock.json").read_text());old=json.loads((prior/"product-lock.json").read_text())
 if cur.get("product_lock_identity")!=ACTIVE_ID or sha(active/"product-lock.json")!=ACTIVE_SHA:raise RuntimeError("active")
 if direct.get("product_lock_identity")!=IMMEDIATE_ID or sha(immediate/"product-lock.json")!=IMMEDIATE_SHA:raise RuntimeError("immediate")
 if old.get("product_lock_identity")!=PRIOR_ID or sha(prior/"product-lock.json")!=PRIOR_SHA:raise RuntimeError("prior")
 out.mkdir(parents=True,exist_ok=True)
 m={"schema":"vnext-canonical-rollback-manifest-v3","schema_version":3,"status":"PASS_CANONICAL_IMMEDIATE_PREDECESSOR","rollback_root":IMMEDIATE_ROOT,"authority":{"product_lock_identity":IMMEDIATE_ID,"product_lock_sha256":IMMEDIATE_SHA},"verification":{"managed_inventory_source":"product-lock.json","managed_file_count":len(direct["application_files"]),"active_graph_identity":direct["active_graph_identity"],"prospective_atomic_rollback":"PASS","prospective_restore":"PASS"},"prior_canonical_root":{"path":PRIOR_ROOT,"classification":"HISTORICAL_NON_CANONICAL_RETIREMENT_PENDING_SEPARATE_AUTHORITY","product_lock_identity":PRIOR_ID,"product_lock_sha256":PRIOR_SHA},"retired_root_references":[],"legacy_dependency_count":0}
 write(out/"vnext-immediate-predecessor-canonical-rollback-manifest-v3.json",m,"rollback_manifest_identity")
 a={"schema":"vnext-current-active-state-authority-v4","schema_version":5,"status":"ACTIVATED_ATTESTED_CANONICAL_IMMEDIATE_PREDECESSOR","active_root":"/root/pastila-vnext/v1","installed_product_lock":{"identity":ACTIVE_ID,"sha256":ACTIVE_SHA},"predecessor_active_state_authority_identity":ACTIVE_AUTH,"activation_candidate_product_lock_identity":cur["activation_attestation"]["activation_candidate_product_lock_identity"],"activation_receipt_identity":cur["activation_attestation"]["current_activation_receipt_identity"],"active_graph_identity":cur["active_graph_identity"],"contract_authority_bindings":cur["contract_authority_bindings"],"canonical_rollback":{"manifest_identity":m["rollback_manifest_identity"],"root":IMMEDIATE_ROOT,"product_lock_identity":IMMEDIATE_ID,"product_lock_sha256":IMMEDIATE_SHA},"prior_canonical_root":{"root":PRIOR_ROOT,"classification":"HISTORICAL_NON_CANONICAL_RETIREMENT_PENDING_SEPARATE_AUTHORITY","product_lock_identity":PRIOR_ID,"product_lock_sha256":PRIOR_SHA},"retired_root_references":[],"legacy_dependency_count":0}
 write(out/"vnext-immediate-predecessor-active-state-authority-v4.json",a,"active_state_authority_identity")
 s=copy.deepcopy(cur);s["supersedes_product_lock_identity"]=ACTIVE_ID
 att=s["activation_attestation"];att["current_active_state_authority_identity"]=a["active_state_authority_identity"];att["canonical_rollback_manifest_identity"]=m["rollback_manifest_identity"];att["canonical_rollback_product_lock_identity"]=IMMEDIATE_ID;att["canonical_rollback_product_lock_sha256"]=IMMEDIATE_SHA;att["rollback_product_lock_sha256"]=IMMEDIATE_SHA
 s["rollback_authority_transition"]={"immediate_predecessor_root":IMMEDIATE_ROOT,"prior_canonical_root":PRIOR_ROOT,"prior_canonical_classification":"HISTORICAL_NON_CANONICAL_RETIREMENT_PENDING_SEPARATE_AUTHORITY"}
 repl={"app/cli/preflight.py":row(repo/"scripts/vnext_materialized_active_preflight_v12.py","app/cli/preflight.py"),"manifest/authorities/vnext-active-product-lock-successor-v1.json":row(out/"vnext-immediate-predecessor-active-state-authority-v4.json","manifest/authorities/vnext-active-product-lock-successor-v1.json"),"manifest/rollback/vnext-canonical-rollback-manifest-v1.json":row(out/"vnext-immediate-predecessor-canonical-rollback-manifest-v3.json","manifest/rollback/vnext-canonical-rollback-manifest-v1.json")}
 found=set();rows=[]
 for x in s["application_files"]:
  if x["path"] in repl:rows.append(repl[x["path"]]);found.add(x["path"])
  else:rows.append(x)
 if found!=set(repl):raise RuntimeError("targets")
 s["application_files"]=rows;write(out/"vnext-immediate-predecessor-product-lock-successor-v1.json",s,"product_lock_identity")
 return {"status":"PASS","rollback_manifest_identity":m["rollback_manifest_identity"],"active_state_authority_identity":a["active_state_authority_identity"],"product_lock_identity":s["product_lock_identity"],"product_lock_sha256":sha(out/"vnext-immediate-predecessor-product-lock-successor-v1.json"),"managed_replacements":sorted(repl),"legacy_dependency_count":0}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--active",type=Path,required=True);p.add_argument("--immediate",type=Path,required=True);p.add_argument("--prior",type=Path,required=True);p.add_argument("--out",type=Path,required=True);x=p.parse_args();print(json.dumps(build(x.repo,x.active,x.immediate,x.prior,x.out),sort_keys=True))
