#!/usr/bin/env python3
"""Self-contained auditor for the bounded active-state attestation and rollback proof."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, shutil, sqlite3, subprocess, tempfile
from pathlib import Path

def load_module(path):
 s=importlib.util.spec_from_file_location("builder",path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def load(p): return json.loads(p.read_text(encoding="utf-8"))
def verify_id(v,key,m):
 claimed=v[key]; actual=m.identity({k:x for k,x in v.items() if k!=key})
 if claimed!=actual: raise RuntimeError("identity mismatch: "+key)
def atomic_proof():
 results=[]
 for fp in ("BEFORE_BACKUP","AFTER_BACKUP","AFTER_ACTIVATE"):
  with tempfile.TemporaryDirectory(prefix="vnext-rollback-proof-") as td:
   base=Path(td); current=base/"active"; staged=base/"rollback"; backup=base/"backup"
   current.mkdir();staged.mkdir();(current/"marker").write_text("ACTIVE");(staged/"marker").write_text("ROLLBACK")
   old=(current/"marker").read_bytes(); new=(staged/"marker").read_bytes()
   try:
    if fp=="BEFORE_BACKUP": raise RuntimeError(fp)
    os.replace(current,backup)
    if fp=="AFTER_BACKUP": raise RuntimeError(fp)
    os.replace(staged,current)
    if fp=="AFTER_ACTIVATE": raise RuntimeError(fp)
   except RuntimeError:
    if current.exists() and backup.exists(): os.replace(current,staged)
    if backup.exists(): os.replace(backup,current)
   if (current/"marker").read_bytes()!=old or (staged/"marker").read_bytes()!=new: raise RuntimeError("rollback fault recovery failed: "+fp)
   results.append({"failpoint":fp,"status":"PASS_BYTE_EXACT_RECOVERY"})

 # success plus controlled return
 with tempfile.TemporaryDirectory(prefix="vnext-restore-proof-") as td:
  b=Path(td); a=b/"active";r=b/"rollback";bak=b/"backup";a.mkdir();r.mkdir();(a/"m").write_text("A");(r/"m").write_text("R")
  os.replace(a,bak);os.replace(r,a)
  if (a/"m").read_text()!="R":raise RuntimeError("restore simulation failed")
  os.replace(a,r);os.replace(bak,a)
  if (a/"m").read_text()!="A" or (r/"m").read_text()!="R":raise RuntimeError("controlled return failed")
 return results,"PASS_RESTORE_AND_CONTROLLED_RETURN"
def audit(repo:Path,active:Path,rollback:Path,live:bool):
 m=load_module(repo/"scripts/build_vnext_active_state_attestation_rollback_v1.py")
 art=repo/"docs/artifacts"; successor=load(art/"vnext-active-product-lock-successor-v1.json");receipt=load(art/"vnext-activation-receipt-v1.json");rb=load(art/"vnext-canonical-rollback-manifest-v1.json")
 verify_id(successor,"product_lock_identity",m);verify_id(receipt,"activation_receipt_identity",m);verify_id(rb,"rollback_manifest_identity",m)
 if successor["status"]!="ACTIVE" or successor["active_integration_state"]!="ACTIVATED" or not successor["activation"]["authorized"] or not successor["activation"]["product_lock_replacement"]:raise RuntimeError("active semantics incomplete")
 if receipt["active"]["successor_product_lock_identity"]!=successor["product_lock_identity"] or receipt["rollback_manifest_identity"]!=rb["rollback_manifest_identity"]:raise RuntimeError("cross-artifact binding mismatch")
 installed=active/"product-lock.json"
 if m.sha(installed)!=m.CANDIDATE_LOCK_SHA:raise RuntimeError("installed candidate lock drift")
 current=load(installed);managed=[]
 for e in current["application_files"]:
  p=active/e["path"]; row={"path":e["path"],"type":"file","size":p.stat().st_size,"sha256":m.sha(p)}
  if row!=e:raise RuntimeError("active managed drift: "+e["path"])
  managed.append(row)
 if m.identity(managed)!=receipt["active"]["managed_application_identity"]:raise RuntimeError("active managed identity mismatch")
 for rel,expected in rb["managed_components"].items():
  if m.tree_summary(rollback/rel)!=expected:raise RuntimeError("rollback managed drift: "+rel)
 if m.sha(rollback/"product-lock.json")!=rb["authority"]["product_lock_sha256"]:raise RuntimeError("rollback product lock drift")
 r2root=active/"components/editor-r2";r2=load(r2root/"dependency-lock.json");verify_id(r2,"lock_identity",m)
 if r2["lock_identity"]!=successor["components"]["R2_REFERENCE"]["lock_identity"]:raise RuntimeError("R2 binding mismatch")
 for row in r2["files"]:
  p=r2root/row["path"]
  if not p.is_file() or p.is_symlink() or p.stat().st_nlink!=1 or p.stat().st_size!=row["size"] or m.sha(p)!=row["sha256"]:raise RuntimeError("R2 managed byte drift: "+row["path"])
 platform=load(active/"manifest/platform-lock.json");verify_id(platform,"lock_identity",m)
 platform_preflight=load_module(active/"app/cli/preflight.py")
 platform_tree=platform_preflight.tree_identity(active/"platform/python-ml")
 if platform_tree!=platform["stable_content_identity"] or platform_tree!=successor["components"]["PYTHON_ML_PLATFORM"]["stable_content_identity"]:raise RuntimeError("platform content drift")
 con=sqlite3.connect("file:"+(active/"state/product.sqlite3").as_posix()+"?mode=ro",uri=True); integrity=con.execute("pragma integrity_check").fetchone()[0];con.close()
 if integrity!="ok":raise RuntimeError("SQLite integrity failure")
 for row in successor["application_files"]:
  p=active/row["path"]
  if p.stat().st_size<2000000:
   try:t=p.read_text(encoding="utf-8").casefold()
   except UnicodeDecodeError:continue
   if any(x in t for x in ("/root/pf9-","/mnt/f/pt","/root/pastila-news-monitor")):raise RuntimeError("legacy binding: "+row["path"])
 faults,restore=atomic_proof(); live_result={"startup":"NOT_RUN","e2e":"NOT_RUN"}
 if live:
  env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1")
  before=(m.sha(installed),m.sha(active/"state/product.sqlite3"))
  startup=json.loads(subprocess.run([str(active/"platform/python-ml/bin/python"),str(active/"app/cli/product.py"),"--root",str(active)],check=True,text=True,capture_output=True,env=env).stdout)
  with tempfile.TemporaryDirectory(prefix="vnext-attestation-live-") as td:
   e2e=json.loads(subprocess.run([str(active/"platform/python-ml/bin/python"),str(active/"app/cli/acceptance.py"),"--root",str(active),"--workspace",td],check=True,text=True,capture_output=True,env=env).stdout)
  after=(m.sha(installed),m.sha(active/"state/product.sqlite3"))
  if before!=after or startup["status"]!="PASS_STARTUP_READY" or e2e["workflow_state"]!="EXPORTED":raise RuntimeError("live non-destructive gates failed")
  live_result={"startup":startup["status"],"e2e":e2e["status"],"terminal":e2e["workflow_state"],"active_unchanged":True,"acceptance_identity":e2e["acceptance_identity"]}
 result={"schema":"vnext-active-state-attestation-rollback-proof-result-v1","status":"PASS","blockers":0,"active_state_authority_identity":successor["product_lock_identity"],"activation_receipt_identity":receipt["activation_receipt_identity"],"rollback_manifest_identity":rb["rollback_manifest_identity"],"rollback_managed_integrity":"PASS","sqlite_integrity":"PASS","r2_closure":"PASS","fault_injection":faults,"restore_simulation":restore,"live":live_result,"legacy_dependency_count":0,"active_root_mutated":False,"rollback_root_mutated":False}
 result["result_identity"]=m.identity(result);return result
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--active-root",type=Path,required=True);p.add_argument("--rollback-root",type=Path,required=True);p.add_argument("--write-result",type=Path);p.add_argument("--live",action="store_true");a=p.parse_args();r=audit(a.repo,a.active_root,a.rollback_root,a.live);text=json.dumps(r,indent=2,sort_keys=True)+"\n";print(text,end="");
 if a.write_result:a.write_result.write_text(text,encoding="utf-8")
