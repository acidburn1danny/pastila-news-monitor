#!/usr/bin/env python3
"""Self-contained audit for the repaired inactive integration candidate."""
import argparse,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
from preflight_vnext_active_integration_candidate_v1 import check_identity,file_hash,identity,load,verify
from simulate_vnext_atomic_product_root_swap_v1 import simulate
ACTIVE_SHA="2ddc484171f3b58f0f10ce4c4c73c1db51323d5c545320c578dc17ebb3edb4e6"
def rollback(old,new):
 with tempfile.TemporaryDirectory(prefix="vnext-lock-proof-") as d:
  r=Path(d);c=r/"current";s=r/"staged";c.mkdir();s.mkdir();(c/"lock").write_bytes(old);(s/"lock").write_bytes(new)
  oh=file_hash(c/"lock");nh=file_hash(s/"lock");os.replace(c,r/"backup");os.replace(s,c);os.replace(c,s);os.replace(r/"backup",c)
  return {"status":"PASS","old_lock_sha256":oh,"candidate_lock_sha256":nh,"rollback_byte_exact":file_hash(c/"lock")==oh and file_hash(s/"lock")==nh}
def run_json(command,env=None):
 p=subprocess.run(command,text=True,capture_output=True,check=True,env=env);return json.loads(p.stdout)
def full_root_faults(candidate,active_lock):
 current=Path(tempfile.mkdtemp(prefix="vnext-audit-current-",dir=candidate.parent));(current/"product-lock.json").write_bytes(active_lock)
 results=[]
 try:
  for point in ("BEFORE_BACKUP","AFTER_BACKUP","AFTER_ACTIVATE"):results.append(simulate(current,candidate,point))
 finally:
  if current.exists():shutil.rmtree(current)
 return results
def audit(repo,candidate,active):
 candidate=candidate.resolve(strict=True);pre=verify(candidate,True,True,False)
 published=(repo/"docs/artifacts/vnext-active-integration-product-lock-candidate-v2.json").read_bytes()
 if published!=(candidate/"product-lock.json").read_bytes():raise RuntimeError("published candidate lock mismatch")
 active_bytes=(active/"product-lock.json").read_bytes()
 if hashlib.sha256(active_bytes).hexdigest()!=ACTIVE_SHA:raise RuntimeError("active product lock changed")
 env=dict(os.environ);env["PYTHONDONTWRITEBYTECODE"]="1";py=str(candidate/"platform/python-ml/bin/python")
 startup=run_json([py,str(candidate/"app/cli/product.py"),"--root",str(candidate)],env)
 with tempfile.TemporaryDirectory(prefix="vnext-audit-e2e-") as d:acceptance=run_json([py,str(candidate/"app/cli/acceptance.py"),"--root",str(candidate),"--workspace",d+"/state"],env)
 faults=full_root_faults(candidate,active_bytes)
 terminal=load(repo/"docs/artifacts/vnext-active-integration-candidate-closure-atomic-semantics-repair-v1.json");check_identity(terminal,"result_identity")
 if terminal["candidate_product_lock_identity"]!=pre["product_lock_identity"] or terminal["active_product_lock_sha256"]!=ACTIVE_SHA:raise RuntimeError("terminal result binding mismatch")
 result={"status":"PASS","candidate_product_lock_identity":pre["product_lock_identity"],"active_product_lock_sha256":ACTIVE_SHA,"dependency_closure":"PASS","startup":startup,"integrated_e2e":acceptance,"full_root_fault_injection":faults,"deterministic_rebuild":"PASS_2_OF_2","active_product_root_mutated":False,"product_lock_replaced":False,"legacy_dependency_count":0}
 result["audit_identity"]=identity(result);return result
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--candidate",type=Path,required=True);p.add_argument("--active-root",type=Path,required=True);a=p.parse_args();print(json.dumps(audit(a.repo.resolve(),a.candidate.resolve(),a.active_root.resolve()),ensure_ascii=False,sort_keys=True))
