#!/usr/bin/env python3
"""Build the inactive, self-contained VNext product candidate."""
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
MODULES=("vnext_foundation_v1.py","vnext_workflow_v1.py","vnext_state_sqlite_v1.py","vnext_scout_production_v1.py","vnext_r2_consolidation_binding_v1.py","vnext_editor_vertical_slice_v1.py","vnext_factual_acceptance_v1.py","vnext_core_final_v1.py","vnext_product_orchestrator_v1.py")
AUTH=("vnext-active-authority-audit-manifest-v1.json","vnext-canonical-sourcepacket-v1-contract.json","vnext-consolidated-operational-state-sqlite-boundary-v7-contract.json","vnext-active-product-workflow-state-contract-v6.json","vnext-active-product-dependency-graph-v1.json","vnext-active-product-component-migration-matrix-v1.json","vnext-active-product-consolidation-acceptance-gates-v1.json")
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def ident(v):return hashlib.sha256(canon(v)).hexdigest()
def fh(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for c in iter(lambda:f.read(8*1024*1024),b""):h.update(c)
 return h.hexdigest()
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n")
def copytree(a,b):
 b.parent.mkdir(parents=True,exist_ok=True);subprocess.run(["cp","-a",str(a),str(b)],check=True)
def descriptor(root,path,name,role):
 v={"schema":"vnext-active-component","schema_version":1,"component":name,"role":role,"source_commit":"c211a07551284627a8e23c6e84d7dbf7e1125681","legacy_dependency_count":0};v["component_identity"]=ident(v);write(root/path/"component.json",v)
def build(repo,source,target):
 if target.exists():raise RuntimeError("target must be new")
 target.mkdir(parents=True)
 sys.path.insert(0,str(repo/"scripts"));from preflight_vnext_active_integration_candidate_v1 import tree_identity
 copytree(source/"components/r2-reference-v1",target/"components/editor-r2")
 copytree(source/"platform/python-ml-v1",target/"platform/python-ml")
 pkg=target/"app/workflow/pastila_scout";pkg.mkdir(parents=True);(pkg/"__init__.py").write_text("",encoding="utf-8")
 for n in MODULES:shutil.copy2(repo/"src/pastila_scout"/n,pkg/n)
 cli=target/"app/cli";cli.mkdir(parents=True)
 for n in ("preflight_vnext_active_integration_candidate_v1.py","accept_vnext_active_integration_candidate_v1.py"):shutil.copy2(repo/"scripts"/n,cli/n)
 (target/"config").mkdir(parents=True);shutil.copy2(source/"runtime/scout-v1/sources.json",target/"config/sources.json")
 (target/"contracts").mkdir(parents=True);shutil.copy2(repo/"docs/artifacts/vnext-canonical-sourcepacket-v1-contract.json",target/"contracts/source-packet.json")
 auth=target/"manifest/authorities";auth.mkdir(parents=True)
 for n in AUTH:shutil.copy2(repo/"docs/artifacts"/n,auth/n)
 descriptor(target,Path("app/scout"),"SCOUT","discovery_capture_grouping")
 descriptor(target,Path("app/editor"),"EDITOR","editor_draft")
 descriptor(target,Path("app/acceptance"),"FACTUAL_ACCEPTANCE","accepted_setup_or_safe_disposition")
 descriptor(target,Path("app/policy"),"POLICY","explicit_publication_decision")
 descriptor(target,Path("app/final"),"FINAL","deterministic_atomic_export")
 descriptor(target,Path("foundation"),"FOUNDATION","canonical_identity_and_boundary")
 shutil.copy2(source/"product-lock.json",target/"manifest/prior-product-lock.json")
 platform_identity=tree_identity(target/"platform/python-ml")
 platform={"schema":"vnext-platform-lock","schema_version":1,"tree_identity":platform_identity,"path":"platform/python-ml","platform_dependency":True};platform["lock_identity"]=ident(platform);write(target/"manifest/platform-lock.json",platform)
 sys.path.insert(0,str(target/"app/workflow"))
 from pastila_scout.vnext_state_sqlite_v1 import SQLiteStateStore
 state=target/"state";state.mkdir();store=SQLiteStateStore(root=state,database=Path("product.sqlite3"),writer_identity="candidate-bootstrap");store.bootstrap()
 files=[]
 for base in ("app","config","contracts","foundation","manifest/authorities","state"):
  for p in sorted((target/base).rglob("*")):
   if p.is_file():files.append({"path":p.relative_to(target).as_posix(),"size":p.stat().st_size,"sha256":fh(p)})
 for p in (target/"manifest/platform-lock.json",target/"manifest/prior-product-lock.json"):
  files.append({"path":p.relative_to(target).as_posix(),"size":p.stat().st_size,"sha256":fh(p)})
 r2=json.loads((target/"components/editor-r2/dependency-lock.json").read_text())
 lock={"schema":"vnext-product-lock-candidate","schema_version":1,"source_commit":"c211a07551284627a8e23c6e84d7dbf7e1125681","product_root":"/root/pastila-vnext/v1","active_integration_state":"CANDIDATE_NOT_ACTIVATED","application_files":sorted(files,key=lambda x:x["path"]),"components":{"R2_REFERENCE":{"path":"components/editor-r2","lock_identity":r2["lock_identity"],"file_count":len(r2["files"]),"total_bytes":sum(x["size"] for x in r2["files"])},"PYTHON_ML_PLATFORM":{"path":"platform/python-ml","tree_identity":platform_identity}},"excluded_categories":["VOICE_CANDIDATES","EVALUATION","HISTORICAL_RECEIPTS","LEGACY_RUNTIME"],"legacy_dependency_count":0,"activation":{"prepared":True,"authorized":False,"atomic_product_lock_replacement":False}}
 lock["product_lock_identity"]=ident(lock);write(target/"manifest/product-lock.json",lock)
 return {"status":"PASS","target":str(target),"product_lock_identity":lock["product_lock_identity"],"application_files":len(files),"r2_files":len(r2["files"])}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--source-root",type=Path,required=True);p.add_argument("--target",type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.repo.resolve(),a.source_root.resolve(),a.target.resolve()),sort_keys=True))
