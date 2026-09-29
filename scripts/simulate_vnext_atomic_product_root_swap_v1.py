#!/usr/bin/env python3
"""Full-root atomic activation and rollback simulation; never targets the active product root."""
import argparse,hashlib,json,os
from pathlib import Path
ACTIVE=Path("/root/pastila-vnext/v1")
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def simulate(current:Path,staged:Path,failpoint:str):
 current=current.resolve(strict=True);staged=staged.resolve(strict=True)
 if current==ACTIVE or staged==ACTIVE or current.parent!=staged.parent or current.stat().st_dev!=staged.stat().st_dev:raise RuntimeError("unsafe or non-atomic roots")
 parent=current.parent;backup=parent/(current.name+".activation-backup")
 if backup.exists():raise RuntimeError("backup already exists")
 old=sha(current/"product-lock.json");new=sha(staged/"product-lock.json")
 if failpoint=="BEFORE_BACKUP":
  return {"status":"PASS_RECOVERED","failpoint":failpoint,"current_lock_sha256":sha(current/"product-lock.json"),"staged_lock_sha256":sha(staged/"product-lock.json")}
 os.replace(current,backup)
 if failpoint=="AFTER_BACKUP":
  os.replace(backup,current)
  return {"status":"PASS_RECOVERED","failpoint":failpoint,"current_lock_sha256":sha(current/"product-lock.json"),"staged_lock_sha256":sha(staged/"product-lock.json")}
 os.replace(staged,current)
 if sha(current/"product-lock.json")!=new:raise RuntimeError("candidate activation mismatch")
 os.replace(current,staged);os.replace(backup,current)
 if sha(current/"product-lock.json")!=old or sha(staged/"product-lock.json")!=new:raise RuntimeError("rollback mismatch")
 return {"status":"PASS_ROLLED_BACK","failpoint":failpoint,"current_lock_sha256":old,"staged_lock_sha256":new,"full_root_rename":True,"rollback_byte_exact":True}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--current",type=Path,required=True);p.add_argument("--staged",type=Path,required=True);p.add_argument("--failpoint",choices=("BEFORE_BACKUP","AFTER_BACKUP","AFTER_ACTIVATE"),required=True);a=p.parse_args();print(json.dumps(simulate(a.current,a.staged,a.failpoint),sort_keys=True))
