#!/usr/bin/env python3
"""Full-root atomic activation and rollback simulation; never targets the active product root."""
import argparse,hashlib,json,os
from pathlib import Path
ACTIVE=Path("/root/pastila-vnext/v1")
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b""):h.update(chunk)
 return h.hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def tree_identity(root):
 rows=[]
 for p in sorted(root.rglob("*"),key=lambda x:x.relative_to(root).as_posix()):
  rel=p.relative_to(root).as_posix()
  if p.is_symlink():rows.append({"path":rel,"type":"symlink","target":p.readlink().as_posix()})
  elif p.is_dir():rows.append({"path":rel,"type":"directory"})
  elif p.is_file():rows.append({"path":rel,"type":"file","size":p.stat().st_size,"sha256":sha(p)})
  else:raise RuntimeError("unsupported root entry: "+rel)
 return hashlib.sha256(canonical(rows)).hexdigest()
def require_identity(root,expected,label):
 actual=tree_identity(root)
 if actual!=expected:raise RuntimeError(label+" tree identity mismatch")
 return actual
def simulate(current:Path,staged:Path,failpoint:str):
 current=current.resolve(strict=True);staged=staged.resolve(strict=True)
 if current==ACTIVE or staged==ACTIVE or current.parent!=staged.parent or current.stat().st_dev!=staged.stat().st_dev:raise RuntimeError("unsafe or non-atomic roots")
 parent=current.parent;backup=parent/(current.name+".activation-backup")
 if backup.exists():raise RuntimeError("backup already exists")
 old_lock=sha(current/"product-lock.json");new_lock=sha(staged/"product-lock.json")
 old_tree=tree_identity(current);new_tree=tree_identity(staged)
 def result(status):
  current_tree=require_identity(current,old_tree,"current")
  staged_tree=require_identity(staged,new_tree,"staged")
  if sha(current/"product-lock.json")!=old_lock or sha(staged/"product-lock.json")!=new_lock:raise RuntimeError("product-lock rollback mismatch")
  return {"status":status,"failpoint":failpoint,"current_lock_sha256":old_lock,"staged_lock_sha256":new_lock,"current_tree_identity":current_tree,"staged_tree_identity":staged_tree,"full_root_tree_verified":True,"rollback_byte_exact":True}
 if failpoint=="BEFORE_BACKUP":return result("PASS_RECOVERED")
 os.replace(current,backup)
 if failpoint=="AFTER_BACKUP":
  os.replace(backup,current)
  return result("PASS_RECOVERED")
 os.replace(staged,current)
 require_identity(current,new_tree,"activated")
 os.replace(current,staged);os.replace(backup,current)
 return result("PASS_ROLLED_BACK")
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--current",type=Path,required=True);p.add_argument("--staged",type=Path,required=True);p.add_argument("--failpoint",choices=("BEFORE_BACKUP","AFTER_BACKUP","AFTER_ACTIVATE"),required=True);a=p.parse_args();print(json.dumps(simulate(a.current,a.staged,a.failpoint),sort_keys=True))
