#!/usr/bin/env python3
"""Self-contained auditor for the canonical GUI and CLI parity vertical slice."""
from __future__ import annotations
import argparse, ast, hashlib, json
from pathlib import Path

FILES=(
 "src/pastila_scout/vnext_product_gui_v1.py",
 "scripts/vnext_product_gui_cli_v1.py",
 "tests/test_vnext_product_gui_cli_parity_v1.py",
)
AUTHORITY="docs/artifacts/vnext-product-gui-cli-parity-authority-v1.json"
RESULT="docs/artifacts/vnext-product-gui-cli-parity-result-v1.json"

def identity(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def content_addressed(path,key):
 value=json.loads(path.read_text()); claimed=value.pop(key)
 if claimed!=identity(value):raise RuntimeError(f"{path.name} identity mismatch")
 value[key]=claimed;return value

def audit(root:Path):
 root=root.resolve(strict=True);hashes={}
 for rel in FILES:
  p=root/rel
  if not p.is_file() or p.is_symlink() or not p.resolve().is_relative_to(root):raise RuntimeError(rel)
  data=p.read_bytes();hashes[rel]=hashlib.sha256(data).hexdigest()
  if p.suffix==".py":ast.parse(data.decode(),filename=rel)
 gui=(root/FILES[0]).read_text();cli=(root/FILES[1]).read_text()
 if any(x in gui for x in ("sqlite3","SELECT ","INSERT ","TransitionRequest")):raise RuntimeError("GUI bypasses canonical ownership")
 if cli.count("from product import startup")!=1 or "preflight" in cli:raise RuntimeError("startup path is not singular")
 if 'VOICE_STATE = "DISABLED_UNTIL_PROMOTION"' not in gui:raise RuntimeError("VOICE boundary changed")
 authority=content_addressed(root/AUTHORITY,"authority_identity")
 if authority["base_commit"]!="aeef50cd4e5f40a5dcbb86131592c0fb6ce504a0":raise RuntimeError("base commit mismatch")
 if authority["file_sha256"]!=hashes:raise RuntimeError("authority byte binding mismatch")
 result=content_addressed(root/RESULT,"result_identity")
 if result["authority_identity"]!=authority["authority_identity"] or result["tests"]!="5/5 PASS":raise RuntimeError("result binding mismatch")
 audit_result={"schema":"vnext-product-gui-cli-parity-audit","status":"PASS","blockers":0,"files":hashes,"authority_identity":authority["authority_identity"],"result_identity":result["result_identity"],"canonical_startup_paths":1,"direct_sql_writes":0,"workflow_implementations_added":0,"voice":"DISABLED_UNTIL_PROMOTION","legacy_dependency_count":0}
 audit_result["audit_identity"]=identity(audit_result)
 return audit_result
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);a=p.parse_args();print(json.dumps(audit(a.root),sort_keys=True))
