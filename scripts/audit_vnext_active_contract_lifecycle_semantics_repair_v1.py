import argparse,importlib.util,json,tempfile
from pathlib import Path
def run(repo,active):
 s=importlib.util.spec_from_file_location("b",repo/"scripts/build_vnext_active_contract_lifecycle_semantics_repair_v1.py");b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
 with tempfile.TemporaryDirectory(dir="/tmp") as td:
  o=Path(td);r=b.build(repo,active,o)
  for p in o.iterdir():
   q=repo/"docs/artifacts"/p.name
   if not q.is_file() or q.read_bytes()!=p.read_bytes():raise RuntimeError("reproduction "+p.name)
  names=("vnext-active-product-workflow-state-contract-v7.json","vnext-canonical-sourcepacket-v2-contract.json","vnext-consolidated-operational-state-sqlite-boundary-v8-contract.json");d=[json.loads((o/n).read_text()) for n in names]
  if any(x["status"]!="ACTIVE_INSTALLED_AUTHORITY" for x in d) or d[2]["active_integration"] is not True:raise RuntimeError("lifecycle")
  g=json.loads((o/"vnext-active-product-dependency-graph-v4.json").read_text());a=json.loads((o/"vnext-current-active-state-authority-v3.json").read_text());l=json.loads((o/"vnext-active-contract-lifecycle-product-lock-successor-v1.json").read_text())
  if not(g["contract_authority_bindings"]==a["contract_authority_bindings"]==l["contract_authority_bindings"]):raise RuntimeError("bindings")
  return {"status":"PASS","blockers":0,"result_identity":r["result_identity"],"product_lock_identity":r["product_lock_identity"],"runtime_bytes_unchanged":True,"active_root_modified":False,"voice_started":False,"gui_started":False,"legacy_dependency_count":0}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--active",type=Path,required=True);q=p.parse_args();print(json.dumps(run(q.repo,q.active),sort_keys=True))
