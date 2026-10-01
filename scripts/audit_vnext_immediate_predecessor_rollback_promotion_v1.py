#!/usr/bin/env python3
import argparse,importlib.util,json,os,shutil,subprocess,tempfile
from pathlib import Path
def mod(p,n):s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def cp(src,dst):mode=dst.stat().st_mode&0o777;shutil.copyfile(src,dst);os.chmod(dst,mode)
def cmd(a,env):return json.loads(subprocess.run(a,check=True,text=True,capture_output=True,env=env).stdout)
def mount(lower,td,n):
 u=td/(n+"u");w=td/(n+"w");m=td/(n+"m");u.mkdir();w.mkdir();m.mkdir();subprocess.run(["mount","-t","overlay","overlay","-o",f"lowerdir={lower},upperdir={u},workdir={w}",str(m)],check=True);return u,w,m
def exercise(root,ws,rollback=None,full=True):
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1");py=root/"platform/python-ml/bin/python"
 p=cmd([str(py),"-I","-B",str(root/"app/cli/product.py"),"--root",str(root),"--preflight-only"],env)
 s=cmd([str(py),"-I","-B",str(root/"app/cli/product.py"),"--root",str(root)],env)
 e=cmd([str(py),"-I","-B",str(root/"app/cli/acceptance.py"),"--root",str(root),"--workspace",str(ws)],env)
 r={"preflight":p["status"],"startup":s["status"],"terminal":e["workflow_state"],"product_lock_identity":s["product_lock_identity"]}
 if full:
  a=cmd([str(py),"-I","-B",str(root/"app/cli/audit.py"),"--root",str(root),"--rollback-root",str(rollback),"--live"],env);r.update(audit=a["status"],rollback_integrity=a["rollback_integrity"])
 return r
def install(repo,out,merged):
 cp(repo/"scripts/vnext_materialized_active_preflight_v12.py",merged/"app/cli/preflight.py")
 cp(out/"vnext-immediate-predecessor-active-state-authority-v4.json",merged/"manifest/authorities/vnext-active-product-lock-successor-v1.json")
 cp(out/"vnext-immediate-predecessor-canonical-rollback-manifest-v3.json",merged/"manifest/rollback/vnext-canonical-rollback-manifest-v1.json")
 cp(out/"vnext-immediate-predecessor-product-lock-successor-v1.json",merged/"product-lock.json")
def run(repo,active,immediate,prior):
 b=mod(repo/"scripts/build_vnext_immediate_predecessor_rollback_promotion_v1.py","b")
 before={str(x):b.sha(x/"product-lock.json") for x in (active,immediate,prior)}
 with tempfile.TemporaryDirectory(prefix="vnext-immediate-rollback-",dir="/root") as x:
  td=Path(x);out=td/"out";built=b.build(repo,active,immediate,prior,out)
  spec={"vnext-immediate-predecessor-canonical-rollback-manifest-v3.json":"rollback_manifest_identity","vnext-immediate-predecessor-active-state-authority-v4.json":"active_state_authority_identity","vnext-immediate-predecessor-product-lock-successor-v1.json":"product_lock_identity"}
  vals={}
  for n,k in spec.items():
   v=json.loads((out/n).read_text());vals[n]=v;c=v.pop(k)
   if c!=b.ident(v):raise RuntimeError("identity "+n)
   v[k]=c
  m=vals[next(iter(spec))];a=vals["vnext-immediate-predecessor-active-state-authority-v4.json"];l=vals["vnext-immediate-predecessor-product-lock-successor-v1.json"]
  if m["rollback_root"]!=b.IMMEDIATE_ROOT or m["prior_canonical_root"]["classification"]!="HISTORICAL_NON_CANONICAL_RETIREMENT_PENDING_SEPARATE_AUTHORITY" or m["retired_root_references"]!=[]:raise RuntimeError("manifest semantics")
  if a["canonical_rollback"]["manifest_identity"]!=m["rollback_manifest_identity"] or a["retired_root_references"]!=[]:raise RuntimeError("authority")
  if l["supersedes_product_lock_identity"]!=b.ACTIVE_ID:raise RuntimeError("lock lineage")
  u,w,z=mount(active,td,"install")
  try:install(repo,out,z);ins=exercise(z,td/"ie2e",immediate,True)
  finally:subprocess.run(["umount",str(z)],check=True)
  u2,w2,z2=mount(immediate,td,"rollback")
  try:
   for p in z2.rglob("*.pyc"):p.unlink()
   rb=exercise(z2,td/"re2e",None,False)
  finally:subprocess.run(["umount",str(z2)],check=True)
  shutil.rmtree(u);shutil.rmtree(w);u.mkdir();w.mkdir();subprocess.run(["mount","-t","overlay","overlay","-o",f"lowerdir={active},upperdir={u},workdir={w}",str(z)],check=True)
  try:install(repo,out,z);restore=exercise(z,td/"se2e",immediate,True)
  finally:subprocess.run(["umount",str(z)],check=True)
 after={str(x):b.sha(x/"product-lock.json") for x in (active,immediate,prior)}
 if before!=after:raise RuntimeError("protected root mutation")
 result={"schema":"vnext-immediate-predecessor-rollback-promotion-result-v1","status":"PASS","blockers":0,**built,"prospective_install":ins,"prospective_rollback":rb,"prospective_restore":restore,"active_root_modified":False,"rollback_roots_modified":False,"prior_root_deleted":False,"legacy_dependency_count":0};result["result_identity"]=b.ident(result);return result
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--active",type=Path,required=True);p.add_argument("--immediate",type=Path,required=True);p.add_argument("--prior",type=Path,required=True);x=p.parse_args();print(json.dumps(run(x.repo,x.active,x.immediate,x.prior),sort_keys=True))
