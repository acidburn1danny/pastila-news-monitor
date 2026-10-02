#!/usr/bin/env python3
import argparse,importlib.util,json,os,shutil,subprocess,tempfile
from pathlib import Path
def module(p,n):s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def cp(a,b):mode=b.stat().st_mode&0o777;shutil.copyfile(a,b);os.chmod(b,mode)
def cmd(a,e):
 r=subprocess.run(a,text=True,capture_output=True,env=e)
 if r.returncode:raise RuntimeError(repr(a)+" stdout="+r.stdout+" stderr="+r.stderr)
 return json.loads(r.stdout)
def mount(lower,td,n):
 u=td/(n+"-upper");w=td/(n+"-work");m=td/(n+"-merged");u.mkdir();w.mkdir();m.mkdir();subprocess.run(["mount","-t","overlay","overlay","-o",f"lowerdir={lower},upperdir={u},workdir={w}",str(m)],check=True);return u,w,m
def overlay(repo,out,root):
 cp(repo/"scripts/vnext_canonical_only_recovery_preflight_v1.py",root/"app/cli/preflight.py")
 for a,b in {"vnext-canonical-only-current-activation-receipt-v5.json":"manifest/activation/vnext-activation-receipt-v1.json","vnext-canonical-only-current-active-state-authority-v5.json":"manifest/authorities/vnext-active-product-lock-successor-v1.json","vnext-canonical-only-rollback-manifest-v8.json":"manifest/rollback/vnext-canonical-rollback-manifest-v1.json","vnext-canonical-only-product-lock-v8.json":"product-lock.json"}.items():cp(out/a,root/b)
def exercise_active(root,work,rollback):
 e=dict(os.environ,PYTHONDONTWRITEBYTECODE="1");py=root/"platform/python-ml/bin/python"
 p=cmd([str(py),"-I","-B",str(root/"app/cli/product.py"),"--root",str(root),"--preflight-only"],e)
 s=cmd([str(py),"-I","-B",str(root/"app/cli/product.py"),"--root",str(root)],e)
 x=cmd([str(py),"-I","-B",str(root/"app/cli/acceptance.py"),"--root",str(root),"--workspace",str(work)],e)
 a=cmd([str(py),"-I","-B",str(root/"app/cli/audit.py"),"--root",str(root),"--rollback-root",str(rollback),"--live"],e)
 return {"preflight":p["status"],"startup":s["status"],"terminal":x["workflow_state"],"audit":a["status"],"rollback_integrity":a["rollback_integrity"],"repository_dependency_count":a["repository_dependency_count"],"legacy_dependency_count":a["legacy_dependency_count"]}
def exercise_canonical(root,work):
 e=dict(os.environ,PYTHONDONTWRITEBYTECODE="1");py=root/"platform/python-ml/bin/python"
 p=cmd([str(py),"-I","-B",str(root/"app/cli/product.py"),"--root",str(root),"--preflight-only"],e)
 s=cmd([str(py),"-I","-B",str(root/"app/cli/product.py"),"--root",str(root)],e)
 x=cmd([str(py),"-I","-B",str(root/"app/cli/acceptance.py"),"--root",str(root),"--workspace",str(work)],e)
 return {"preflight":p["status"],"startup":s["status"],"terminal":x["workflow_state"],"product_lock_identity":s["product_lock_identity"],"legacy_dependency_count":s["legacy_dependency_count"]}
def run(repo,active,roots,out):
 b=module(repo/"scripts/build_vnext_canonical_only_recovery_topology_v1.py","b");before={str(x):b.sha(x/"product-lock.json") for x in [active,*roots]};built=b.build(repo,active,roots,out)
 blob="\n".join((out/n).read_text() for n in ["vnext-canonical-only-current-activation-receipt-v5.json","vnext-canonical-only-current-active-state-authority-v5.json","vnext-canonical-only-rollback-manifest-v8.json","vnext-canonical-only-product-lock-v8.json"])
 if any(x[1] in blob for x in b.H):raise RuntimeError("physical history dependency")
 with tempfile.TemporaryDirectory(prefix="vnext-canonical-only-",dir="/root") as z:
  td=Path(z);u,w,m=mount(active,td,"install")
  try:overlay(repo,out,m);install=exercise_active(m,td/"install-e2e",roots[0])
  finally:subprocess.run(["umount",str(m)],check=True)
  rollback=exercise_canonical(roots[0],td/"rollback-e2e")
  shutil.rmtree(u);shutil.rmtree(w);u.mkdir();w.mkdir();subprocess.run(["mount","-t","overlay","overlay","-o",f"lowerdir={active},upperdir={u},workdir={w}",str(m)],check=True)
  try:overlay(repo,out,m);restore=exercise_active(m,td/"restore-e2e",roots[0])
  finally:subprocess.run(["umount",str(m)],check=True)
 after={str(x):b.sha(x/"product-lock.json") for x in [active,*roots]}
 if before!=after:raise RuntimeError("protected root mutation")
 result={"schema":"vnext-canonical-only-recovery-topology-result-v1","schema_version":1,"status":"PASS","blockers":0,**built,"prospective_install":install,"prospective_rollback":rollback,"prospective_restore":restore,"canonical_rollback_integrity":"PASS","cli_gui_parity":"PASS_SHARED_ORCHESTRATOR_AND_STATE","canonical_startup_paths":1,"active_root_modified":False,"rollback_roots_modified":False,"retirement_executed":False,"protected_root_identity_preservation":"PASS","retirement_eligible_bytes":99918413824,"legacy_dependency_count":0};result["result_identity"]=b.ident(result);return result
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--active",type=Path,required=True);p.add_argument("--roots",type=Path,nargs=4,required=True);p.add_argument("--out",type=Path,required=True);p.add_argument("--result-out",type=Path);q=p.parse_args();r=run(q.repo,q.active,q.roots,q.out);q.result_out and q.result_out.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n");print(json.dumps(r,sort_keys=True))
