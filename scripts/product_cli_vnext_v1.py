#!/usr/bin/env python3
"""Real no-load startup boundary for the consolidated VNext product."""
import argparse,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
def startup(root:Path):
 root=root.resolve(strict=True)
 sys.path.insert(0,str(root/"app/cli"));from preflight import verify
 preflight=verify(root,full_platform_hash=True)
 sys.path.insert(0,str(root/"app/workflow"))
 from pastila_scout.vnext_state_sqlite_v1 import SQLiteStateStore
 store=SQLiteStateStore(root=root/"state",database=Path("product.sqlite3"),writer_identity="vnext-product-runtime-v1")
 integrity=store.verify_integrity()
 sources=json.loads((root/"config/sources.json").read_text(encoding="utf-8"))
 if integrity.get("status")!="PASS" or not isinstance(sources,(list,dict)):raise RuntimeError("startup contract failed")
 return {"status":"PASS_STARTUP_READY","product_lock_identity":preflight["product_lock_identity"],"state_integrity":"PASS","model_load":False,"inference":False,"legacy_dependency_count":0}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);a=p.parse_args();print(json.dumps(startup(a.root),sort_keys=True))
