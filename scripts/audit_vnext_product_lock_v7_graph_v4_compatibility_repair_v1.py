import argparse,importlib.util,json,tempfile
from pathlib import Path
def run(repo):
 s=importlib.util.spec_from_file_location("b",repo/"scripts/build_vnext_product_lock_v7_graph_v4_compatibility_repair_v1.py");b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
 with tempfile.TemporaryDirectory(dir="/tmp") as td:
  o=Path(td);r=b.build(repo,o)
  for p in o.iterdir():
   q=repo/"docs/artifacts"/p.name
   if q.read_bytes()!=p.read_bytes():raise RuntimeError("reproduction "+p.name)
  lock=json.loads((o/"vnext-product-lock-v7-graph-v4-compatibility-successor-v1.json").read_text())
  if lock["schema_version"]!=7 or lock["compatibility_authority"]["active_graph_schema"]!=4:raise RuntimeError("compatibility")
  if lock["supersedes_product_lock_identity"]!="3229ddda9f36971f2928ea3fdb6b78e145e956d240ede2b5d781fe3fbb0cd7a2":raise RuntimeError("predecessor")
  return {"status":"PASS","blockers":0,**r}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.repo),sort_keys=True))
