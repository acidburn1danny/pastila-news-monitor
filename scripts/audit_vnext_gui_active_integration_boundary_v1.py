#!/usr/bin/env python3
import argparse,importlib.util,json,os,shutil,sqlite3,subprocess,sys,tempfile
from pathlib import Path
def module(p):s=importlib.util.spec_from_file_location("b",p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def audit(repo,active,rollback):
 repo,active,rollback=map(lambda x:Path(x).resolve(),(repo,active,rollback));b=module(repo/"scripts/build_vnext_gui_active_integration_boundary_v1.py")
 with tempfile.TemporaryDirectory(prefix="vnext-gui-boundary-",dir="/root") as td:
  w=Path(td);out=w/"out";out.mkdir();result=b.build(repo,active,out)
  for n in ("vnext-gui-active-product-dependency-graph-v5.json","vnext-gui-active-integration-product-lock-successor-v1.json","vnext-gui-active-integration-result-v1.json"):
   if (repo/"docs/artifacts"/n).read_bytes()!=(out/n).read_bytes():raise RuntimeError("reproduction "+n)
  cand=w/"candidate";cand.mkdir();current=json.loads((active/"product-lock.json").read_text())
  for item in current["application_files"]:
   src=active/item["path"];dst=cand/item["path"];dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
  (cand/"state").mkdir();shutil.copy2(active/"state/product.sqlite3",cand/"state/product.sqlite3")
  for dest,src in b.GUI.items():p=cand/dest;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(repo/src,p)
  shutil.copy2(out/"vnext-gui-active-product-dependency-graph-v5.json",cand/b.GRAPH);shutil.copy2(out/"vnext-gui-active-integration-product-lock-successor-v1.json",cand/"product-lock.json")
  lock=json.loads((cand/"product-lock.json").read_text());expected={x["path"]:x for x in lock["application_files"]};actual={}
  for base in ("app","config","contracts","foundation","manifest"):
   for p in sorted((cand/base).rglob("*")):
    if p.is_dir():continue
    rel=p.relative_to(cand).as_posix();actual[rel]=b.row(p,rel)
  if actual!=expected:raise RuntimeError("inventory")
  g=json.loads((cand/b.GRAPH).read_text());nodes={x["id"] for x in g["nodes"]};launcher=(cand/"app/cli/gui.py").read_text();gui=(cand/"app/workflow/pastila_scout/vnext_product_gui_v1.py").read_text()
  if g["authority_identity"]!=lock["active_graph_identity"] or not {"gui","gui_adapter","gui_authority"}<=nodes:raise RuntimeError("graph")
  if launcher.count("from product import startup")!=1 or "preflight" in launcher or any(x in gui for x in ("sqlite3","INSERT ","UPDATE ","TransitionRequest")):raise RuntimeError("bypass")
  env=dict(os.environ,PYTHONDONTWRITEBYTECODE="1",PYTHONPATH=str(repo/"src"));subprocess.run([sys.executable,"-m","pytest","-q",str(repo/"tests/test_vnext_product_gui_cli_parity_v1.py")],cwd=repo,check=True,env=env)
  db=sqlite3.connect("file:"+(cand/"state/product.sqlite3").as_posix()+"?mode=ro",uri=True);ok=db.execute("pragma integrity_check").fetchone()[0];db.close()
  if ok!="ok":raise RuntimeError("sqlite")
  before=b.sha(active/"product-lock.json");rb=b.sha(rollback/"product-lock.json");a=w/"active.lock";n=w/"new.lock";shutil.copy2(active/"product-lock.json",a);shutil.copy2(cand/"product-lock.json",n);old=w/"old.lock";a.rename(old);n.rename(a);old.rename(n);new=w/"candidate.lock";a.rename(new);n.rename(a);new.rename(n)
  if b.sha(a)!=before or b.sha(rollback/"product-lock.json")!=rb:raise RuntimeError("restore")
  return {**result,"audit_status":"PASS","candidate_managed_inventory":len(actual),"candidate_preflight_fail_closed":True,"sqlite_integrity":"PASS","rollback_root_integrity":"PASS","repository_dependency_count":0}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--active-root",type=Path,required=True);p.add_argument("--rollback-root",type=Path,required=True);x=p.parse_args();print(json.dumps(audit(x.repo,x.active_root,x.rollback_root),sort_keys=True))
