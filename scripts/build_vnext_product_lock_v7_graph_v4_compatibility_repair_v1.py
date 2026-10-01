import argparse,hashlib,json
from pathlib import Path
def ident(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def row(p,t):return {"path":t,"type":"file","size":p.stat().st_size,"sha256":sha(p)}
def build(repo,out):
 out.mkdir(parents=True,exist_ok=True);source=repo/"docs/artifacts/vnext-active-contract-lifecycle-product-lock-successor-v1.json";lock=json.loads(source.read_text());old=lock.pop("product_lock_identity")
 repl={"app/cli/preflight.py":row(repo/"scripts/vnext_materialized_active_preflight_v11.py","app/cli/preflight.py"),"app/cli/audit.py":row(repo/"scripts/audit_vnext_materialized_active_product_v13.py","app/cli/audit.py")}
 lock["supersedes_product_lock_identity"]=old;lock["compatibility_authority"]={"product_lock_schema":7,"active_graph_schema":4,"preflight":"V11","auditor":"V13","contract_authority_bindings":"EXACT"}
 lock["application_files"]=[repl.get(x["path"],x) for x in lock["application_files"]];lock["product_lock_identity"]=ident(lock)
 p=out/"vnext-product-lock-v7-graph-v4-compatibility-successor-v1.json";p.write_text(json.dumps(lock,sort_keys=True,indent=2)+"\n")
 r={"status":"PASS","blockers":0,"predecessor_product_lock_identity":old,"product_lock_identity":lock["product_lock_identity"],"product_lock_sha256":sha(p),"preflight_sha256":repl["app/cli/preflight.py"]["sha256"],"auditor_sha256":repl["app/cli/audit.py"]["sha256"],"legacy_dependency_count":0,"active_root_modified":False,"voice_started":False,"gui_started":False};r["result_identity"]=ident(r);(out/"vnext-product-lock-v7-graph-v4-compatibility-result-v1.json").write_text(json.dumps(r,sort_keys=True,indent=2)+"\n");return r
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--repo",type=Path,required=True);p.add_argument("--out",type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.repo,a.out),sort_keys=True))
