#!/usr/bin/env python3
"""Exact dependency and authority preflight for a VNext product candidate."""
import argparse,hashlib,json,os,re,shutil,sqlite3,subprocess
from pathlib import Path
FROZEN_PLATFORM="ef5318bfa36af16350ec96d16ef84eb8b55c527894c3c5045f08d4b9ba1bc498"
LEGACY_MARKERS=("/"+"root/pf9-","/mnt"+"/f/pt","F:"+chr(92)+chr(92)+"pt","/root/"+"pastila-news-monitor")
MANAGED=("app","config","contracts","foundation","manifest")
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def identity(v):return hashlib.sha256(canonical(v)).hexdigest()
def file_hash(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(8*1024*1024),b""):h.update(c)
 return h.hexdigest()
def tree_identity(root):
 rows=[]
 for p in sorted(root.rglob("*")):
  rel=p.relative_to(root).as_posix()
  if "__pycache__" in p.parts or p.suffix==".pyc":continue
  if p.is_symlink():rows.append({"path":rel,"type":"symlink","target":os.readlink(p)})
  elif p.is_file():rows.append({"path":rel,"type":"file","sha256":file_hash(p),"size":p.stat().st_size})
 return identity(rows)
def load(p):
 v=json.loads(p.read_text(encoding="utf-8"))
 if not isinstance(v,dict):raise RuntimeError("object required: "+str(p))
 return v
def check_identity(v,key):
 claimed=v.get(key);actual=identity({k:x for k,x in v.items() if k!=key})
 if claimed!=actual:raise RuntimeError("identity mismatch: "+key)
def managed_entries(root):
 out={}
 for base in MANAGED:
  for p in sorted((root/base).rglob("*")):
   rel=p.relative_to(root).as_posix()
   if p.is_symlink():out[rel]={"path":rel,"type":"symlink","target":os.readlink(p)}
   elif p.is_file():out[rel]={"path":rel,"type":"file","size":p.stat().st_size,"sha256":file_hash(p)}
 return out
def verify_host(root,platform):
 host=platform["host_dependencies"];py=root/"platform/python-ml/bin/python"
 version=subprocess.run([str(py),"--version"],text=True,capture_output=True,check=True).stdout.strip().split()[-1]
 if version!=host["python"]["version"] or os.readlink(root/"platform/python-ml/bin/python3")!=host["python"]["path"]:raise RuntimeError("host Python mismatch")
 code="import importlib.metadata as m,json;print(json.dumps({n:m.version(n) for n in "+repr(tuple(host["packages"]))+"},sort_keys=True))"
 packages=json.loads(subprocess.run([str(py),"-c",code],text=True,capture_output=True,check=True).stdout)
 if packages!=host["packages"]:raise RuntimeError("platform package mismatch")
 nvidia=shutil.which("nvidia-smi")
 if not nvidia:raise RuntimeError("nvidia-smi missing")
 line=subprocess.run([nvidia,"--query-gpu=name,driver_version,memory.total","--format=csv,noheader,nounits"],text=True,capture_output=True,check=True).stdout.strip().splitlines()[0]
 name,driver,memory=(x.strip() for x in line.split(","))
 if name!=host["gpu"]["name"] or int(memory)<host["gpu"]["minimum_memory_mib"]:raise RuntimeError("GPU mismatch")
 def parts(x):return tuple(int(n) for n in re.findall(r"\d+",x))
 if parts(driver)<parts(host["nvidia_driver"]["minimum"]):raise RuntimeError("driver too old")
 return {"python":version,"packages":packages,"gpu":name,"driver":driver,"memory_mib":int(memory)}
def verify(root,full_platform_hash=True,verify_host_dependencies=True,require_pristine_state=False):
 root=root.resolve(strict=True);lock=load(root/"product-lock.json");check_identity(lock,"product_lock_identity")
 if lock["product_root"]!="/root/pastila-vnext/v1" or lock["active_integration_state"]!="CANDIDATE_NOT_ACTIVATED" or lock["legacy_dependency_count"]!=0:raise RuntimeError("candidate authority mismatch")
 expected={x["path"]:x for x in lock["application_files"]};actual=managed_entries(root)
 if set(expected)!=set(actual):raise RuntimeError("managed inventory mismatch: missing="+repr(sorted(set(expected)-set(actual)))+" extra="+repr(sorted(set(actual)-set(expected))))
 for path,row in expected.items():
  if row!=actual[path]:raise RuntimeError("managed byte mismatch: "+path)
 graph=load(root/"manifest/authorities/vnext-active-product-dependency-graph-v2.json");check_identity(graph,"authority_identity")
 if graph["authority_identity"]!=lock["active_graph_identity"]:raise RuntimeError("active graph mismatch")
 for node in graph["nodes"]:
  if not (root/node["target_path"]).exists():raise RuntimeError("active graph target missing: "+node["target_path"])
 r2=root/"components/editor-r2";r2lock=load(r2/"dependency-lock.json");check_identity(r2lock,"lock_identity")
 if r2lock["lock_identity"]!=lock["components"]["R2_REFERENCE"]["lock_identity"]:raise RuntimeError("R2 lock mismatch")
 for row in r2lock["files"]:
  p=r2/row["path"]
  if not p.is_file() or p.is_symlink() or p.stat().st_nlink!=1 or p.stat().st_size!=row["size"] or file_hash(p)!=row["sha256"]:raise RuntimeError("R2 byte mismatch: "+row["path"])
 platform=load(root/"manifest/platform-lock.json");check_identity(platform,"lock_identity")
 if platform["frozen_platform_authority_identity"]!=FROZEN_PLATFORM:raise RuntimeError("frozen platform authority mismatch")
 if platform["stable_content_identity"]!=lock["components"]["PYTHON_ML_PLATFORM"]["stable_content_identity"]:raise RuntimeError("platform lock binding mismatch")
 if full_platform_hash and tree_identity(root/"platform/python-ml")!=platform["stable_content_identity"]:raise RuntimeError("stable platform content mismatch")
 state_db=root/lock["mutable_state"]["database"]
 if not state_db.is_file():raise RuntimeError("product state database missing")
 pristine=file_hash(state_db)==lock["mutable_state"]["bootstrap_sha256"]
 if require_pristine_state and not pristine:raise RuntimeError("staged state is not pristine")
 connection=sqlite3.connect("file:"+state_db.as_posix()+"?mode=ro",uri=True);integrity=connection.execute("PRAGMA integrity_check").fetchone()[0];connection.close()
 if integrity!="ok":raise RuntimeError("SQLite integrity failed")
 host_result=verify_host(root,platform) if verify_host_dependencies else {"verified":False}
 for rel,row in actual.items():
  p=root/rel
  if p.is_file() and p.stat().st_size<=2000000:
   try:text=p.read_text(encoding="utf-8")
   except UnicodeDecodeError:continue
   if any(m.casefold() in text.casefold() for m in LEGACY_MARKERS):raise RuntimeError("legacy binding: "+rel)
 return {"status":"PASS","product_lock_identity":lock["product_lock_identity"],"application_files":len(actual),"r2_files":len(r2lock["files"]),"platform_tree_verified":full_platform_hash,"host_dependencies":host_result,"active_graph_identity":graph["authority_identity"],"state_bootstrap_pristine":pristine,"state_integrity":"PASS","legacy_dependency_count":0}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);p.add_argument("--skip-platform-hash",action="store_true");p.add_argument("--skip-host",action="store_true");p.add_argument("--require-pristine-state",action="store_true");a=p.parse_args();print(json.dumps(verify(a.root,not a.skip_platform_hash,not a.skip_host,a.require_pristine_state),sort_keys=True))
