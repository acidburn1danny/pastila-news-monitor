#!/usr/bin/env python3
"""Exact dependency and authority preflight for a VNext product candidate."""
import argparse,hashlib,json,os,re,shutil,sqlite3,subprocess
from pathlib import Path
from runtime_bytes_policy import ALLOWED_REGENERABLE_RUNTIME,AUTHORIZED_COMPONENT_PATHS,DECLARED_ALLOWED,FORBIDDEN,MANAGED,MUTABLE_STATE,classify
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
   if p.is_dir() and not p.is_symlink():continue
   kind=classify(rel,p.is_symlink())
   if kind==FORBIDDEN:raise RuntimeError("forbidden product byte: "+rel)
   if kind==ALLOWED_REGENERABLE_RUNTIME:continue
   if p.is_file():out[rel]={"path":rel,"type":"file","size":p.stat().st_size,"sha256":file_hash(p)}
 return out
def verify_policy_surface(root):
 for p in sorted(root.iterdir()):
  if p.name in {"app","config","contracts","foundation","manifest","components","platform","state"}:continue
  if classify(p.name,p.is_symlink())==FORBIDDEN:raise RuntimeError("forbidden product byte: "+p.name)
 state=root/"state"
 for p in sorted(state.rglob("*")):
  if p.is_dir() and not p.is_symlink():continue
  rel=p.relative_to(root).as_posix()
  if classify(rel,p.is_symlink())==FORBIDDEN:raise RuntimeError("forbidden state byte: "+rel)
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
def verify_activation_authority(root,lock):
 version=lock.get("schema_version")
 if version in (4,5):return "PREDECESSOR_SCHEMA"
 if version==8:
  if lock.get("supersedes_product_lock_identity")!="4d45f169ed4f6eba530e181a7e61ce4ade02d63e8d21f5177b3d4d18d15a0738":raise RuntimeError("GUI candidate predecessor mismatch")
  if lock.get("gui_authority",{}).get("state")!="ACTIVE":raise RuntimeError("GUI authority state mismatch")
  att=lock.get("activation_attestation",{})
  if att.get("activation_candidate_product_lock_identity")!="4d45f169ed4f6eba530e181a7e61ce4ade02d63e8d21f5177b3d4d18d15a0738":raise RuntimeError("GUI activation candidate mismatch")
  receipt=load(root/"manifest/activation/vnext-activation-receipt-v1.json");check_identity(receipt,"activation_receipt_identity")
  authority=load(root/"manifest/authorities/vnext-active-product-lock-successor-v1.json");check_identity(authority,"active_state_authority_identity")
  rollback=load(root/"manifest/rollback/vnext-canonical-rollback-manifest-v1.json");check_identity(rollback,"rollback_manifest_identity")
  if receipt.get("candidate",{}).get("product_lock_identity")!=att["activation_candidate_product_lock_identity"]:raise RuntimeError("GUI receipt candidate binding")
  if receipt.get("activation_receipt_identity")!=att.get("current_activation_receipt_identity"):raise RuntimeError("GUI receipt identity")
  if authority.get("active_state_authority_identity")!=att.get("current_active_state_authority_identity") or authority.get("activation_receipt_identity")!=receipt["activation_receipt_identity"]:raise RuntimeError("GUI authority binding")
  if rollback.get("rollback_manifest_identity")!=att.get("canonical_rollback_manifest_identity"):raise RuntimeError("GUI rollback identity")
  expected_root="/root/pastila-vnext/.rollback-pre-gui-coherent-733ad2a1"
  if rollback.get("rollback_root")!=expected_root or rollback.get("authority",{}).get("product_lock_identity")!="5a5988bd0fb3b7d760c5a99dd13c007281a6900dd6a572c21c3812d6cd00bf93":raise RuntimeError("GUI rollback target")
  if authority.get("canonical_rollback",{}).get("root")!=expected_root or authority.get("active_graph_identity")!=lock.get("active_graph_identity"):raise RuntimeError("GUI active authority")
  if lock.get("rollback_authority_transition",{}).get("topology")=="ACTIVE_TO_CANONICAL_ONLY":
   if lock["rollback_authority_transition"].get("historical_physical_roots_required")!=0:raise RuntimeError("historical roots required")
   if rollback.get("historical_roots") is not None or rollback.get("recovery_topology",{}).get("physical_root_count")!=1:raise RuntimeError("canonical-only manifest")
   if authority.get("recovery_topology")!="ACTIVE_TO_CANONICAL_ONLY":raise RuntimeError("canonical-only authority")
   if receipt.get("rollback",{}).get("physical_historical_roots_required")!=0:raise RuntimeError("canonical-only receipt")
   return "V8_GUI_ACTIVE_ATTESTED_CANONICAL_ONLY"
  return "V8_GUI_ACTIVE_ATTESTED"
 if version not in (6,7):raise RuntimeError("unsupported product-lock schema")
 return "PREDECESSOR_SCHEMA_6_OR_7"
def verify(root,full_platform_hash=True,verify_host_dependencies=True,require_pristine_state=False):
 root=root.resolve(strict=True)
 for p in root.rglob("*"):
  meta=p.lstat()
  if meta.st_uid!=0 or meta.st_gid!=0:raise RuntimeError("product filesystem owner mismatch: "+p.relative_to(root).as_posix())
  if not p.is_symlink() and meta.st_mode & 0o022:raise RuntimeError("product filesystem permissions mismatch: "+p.relative_to(root).as_posix())
  if not (p.is_symlink() or p.is_dir() or p.is_file()):raise RuntimeError("product filesystem entry type mismatch: "+p.relative_to(root).as_posix())
  if not p.is_symlink() and p.is_file() and p.stat().st_nlink!=1:raise RuntimeError("product file ownership mismatch: "+p.relative_to(root).as_posix())
 lock=load(root/"product-lock.json");check_identity(lock,"product_lock_identity")
 if lock.get("status")!="ACTIVE" or lock["product_root"]!="/root/pastila-vnext/v1" or lock["active_integration_state"]!="ACTIVATED" or lock["legacy_dependency_count"]!=0:raise RuntimeError("active authority mismatch")
 activation_authority=verify_activation_authority(root,lock)
 if tuple(lock.get("runtime_cache_policy",{}).get("allowed",()))!=DECLARED_ALLOWED or lock["runtime_cache_policy"].get("authoritative") is not False or lock["runtime_cache_policy"].get("regenerable") is not True:raise RuntimeError("runtime cache policy drift")
 expected={x["path"]:x for x in lock["application_files"]};actual=managed_entries(root)
 verify_policy_surface(root)
 if set(expected)!=set(actual):raise RuntimeError("managed inventory mismatch: missing="+repr(sorted(set(expected)-set(actual)))+" extra="+repr(sorted(set(actual)-set(expected))))
 for path,row in expected.items():
  if row!=actual[path]:raise RuntimeError("managed byte mismatch: "+path)
 graph=load(root/"manifest/authorities/vnext-active-product-dependency-graph-v3.json");check_identity(graph,"authority_identity")
 if graph.get("schema_version") not in (3,4) or graph.get("status")!="ACTIVE_SELF_CONTAINED_AUTHORITY_CLOSURE":raise RuntimeError("active graph authority mismatch")
 if lock.get("schema_version")==8 and {x.get("id"):x.get("state") for x in graph.get("enabled",[])}.get("gui")!="ACTIVE":raise RuntimeError("GUI active graph state mismatch")
 if lock.get("schema_version")==8 and lock.get("gui_authority",{}).get("state")!={x.get("id"):x.get("state") for x in graph.get("enabled",[])}.get("gui"):raise RuntimeError("GUI lock/graph state mismatch")
 if lock.get("schema_version") in (7,8):
  bindings=lock.get("contract_authority_bindings")
  if graph.get("schema_version")!=4 or graph.get("contract_authority_bindings")!=bindings:raise RuntimeError("contract authority graph binding")
  paths={"workflow":"manifest/authorities/vnext-active-product-workflow-state-contract-v6.json","source_packet":"manifest/authorities/vnext-canonical-sourcepacket-v1-contract.json","sqlite":"manifest/authorities/vnext-consolidated-operational-state-sqlite-boundary-v7-contract.json"}
  for name,path in paths.items():
   contract=load(root/path);check_identity(contract,"authority_identity")
   if contract.get("authority_identity")!=bindings.get(name) or contract.get("status")!="ACTIVE_INSTALLED_AUTHORITY":raise RuntimeError("contract authority binding "+name)
 if graph["authority_identity"]!=lock["active_graph_identity"]:raise RuntimeError("active graph mismatch")
 if set(lock.get("components",{}))!={"R2_REFERENCE","PYTHON_ML_PLATFORM"}:raise RuntimeError("component authority set mismatch")
 if lock["components"]["R2_REFERENCE"]["path"]!="components/editor-r2" or lock["components"]["PYTHON_ML_PLATFORM"]["path"]!="platform/python-ml":raise RuntimeError("component path mismatch")
 targets={n["id"]:n["target_path"] for n in graph["nodes"]}
 if targets.get("r2")!="components/editor-r2" or targets.get("python_ml")!="platform/python-ml":raise RuntimeError("component graph mismatch")
 component_entries=list((root/'components').iterdir())
 if len(component_entries)!=1 or component_entries[0].name!='editor-r2' or component_entries[0].is_symlink() or not component_entries[0].is_dir():raise RuntimeError('component namespace mismatch')
 platform_entries=list((root/'platform').iterdir())
 if len(platform_entries)!=1 or platform_entries[0].name!='python-ml' or platform_entries[0].is_symlink() or not platform_entries[0].is_dir():raise RuntimeError('platform namespace mismatch')
 for node in graph["nodes"]:
  if not (root/node["target_path"]).exists():raise RuntimeError("active graph target missing: "+node["target_path"])
 r2=root/"components/editor-r2";r2lock=load(r2/"dependency-lock.json");check_identity(r2lock,"lock_identity")
 if r2lock["lock_identity"]!=lock["components"]["R2_REFERENCE"]["lock_identity"]:raise RuntimeError("R2 lock mismatch")
 expected_r2={x["path"] for x in r2lock["files"]}|{"dependency-lock.json",r2lock["layout"]["dependency_preflight"]}
 actual_r2={p.relative_to(r2).as_posix() for p in r2.rglob("*") if p.is_file() or p.is_symlink()}
 if actual_r2!=expected_r2:raise RuntimeError("R2 exhaustive inventory mismatch")
 for rel in actual_r2:
  p=r2/rel
  if p.is_symlink() or p.stat().st_nlink!=1:raise RuntimeError("R2 ownership mismatch: "+rel)
 for row in r2lock["files"]:
  p=r2/row["path"]
  if not p.is_file() or p.is_symlink() or p.stat().st_nlink!=1 or p.stat().st_size!=row["size"] or file_hash(p)!=row["sha256"]:raise RuntimeError("R2 byte mismatch: "+row["path"])
 platform=load(root/"manifest/platform-lock.json");check_identity(platform,"lock_identity")
 if platform["frozen_platform_authority_identity"]!=FROZEN_PLATFORM:raise RuntimeError("frozen platform authority mismatch")
 if platform["stable_content_identity"]!=lock["components"]["PYTHON_ML_PLATFORM"]["stable_content_identity"]:raise RuntimeError("platform lock binding mismatch")
 if any(not x.is_symlink() and x.is_file() and x.stat().st_nlink!=1 for x in (root/'platform/python-ml').rglob('*')):raise RuntimeError('platform ownership mismatch')
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
  active_surface=rel.startswith(("app/","config/","contracts/","foundation/")) or rel.endswith("vnext-active-product-dependency-graph-v3.json")
  if active_surface and p.is_file() and p.stat().st_size<=2000000:
   try:text=p.read_text(encoding="utf-8")
   except UnicodeDecodeError:continue
   if any(m.casefold() in text.casefold() for m in LEGACY_MARKERS):raise RuntimeError("legacy binding: "+rel)
 return {"status":"PASS","product_lock_identity":lock["product_lock_identity"],"application_files":len(actual),"r2_files":len(r2lock["files"]),"platform_tree_verified":full_platform_hash,"host_dependencies":host_result,"active_graph_identity":graph["authority_identity"],"state_bootstrap_pristine":pristine,"state_integrity":"PASS","legacy_dependency_count":0,"activation_authority":activation_authority}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);p.add_argument("--skip-platform-hash",action="store_true");p.add_argument("--skip-host",action="store_true");p.add_argument("--require-pristine-state",action="store_true");a=p.parse_args();print(json.dumps(verify(a.root,not a.skip_platform_hash,not a.skip_host,a.require_pristine_state),sort_keys=True))
