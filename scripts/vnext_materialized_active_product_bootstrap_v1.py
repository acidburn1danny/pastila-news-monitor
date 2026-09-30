#!/usr/bin/env python3
"""Canonical trust bootstrap and startup boundary."""
import sys
if sys.path: sys.path.pop(0)
sys.dont_write_bytecode=True
import argparse,hashlib,json
from pathlib import Path
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def ident(v):return hashlib.sha256(canon(v)).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(8*1024*1024),b''):h.update(c)
 return h.hexdigest()
def trusted_inventory(root):
 lock=json.loads((root/'product-lock.json').read_text(encoding='utf-8'))
 if lock.get('product_lock_identity')!=ident({k:v for k,v in lock.items() if k!='product_lock_identity'}):raise RuntimeError('bootstrap product-lock identity')
 expected={x['path']:x for x in lock['application_files']};actual={}
 for base in ('app','config','contracts','foundation','manifest'):
  for p in sorted((root/base).rglob('*')):
   rel=p.relative_to(root).as_posix()
   if p.is_dir() and not p.is_symlink():continue
   if p.is_symlink() or p.suffix=='.pyc' or '__pycache__' in p.parts:raise RuntimeError('bootstrap executable cache/symlink: '+rel)
   if p.is_file():actual[rel]={'path':rel,'type':'file','size':p.stat().st_size,'sha256':sha(p)}
 if actual!=expected:raise RuntimeError('bootstrap managed inventory mismatch')
 for rel in ('app/cli/preflight.py','app/cli/runtime_bytes_policy.py'):
  if rel not in expected:raise RuntimeError('bootstrap module missing: '+rel)
 return lock
def startup(root:Path,preflight_only=False):
 root=root.resolve(strict=True);lock=trusted_inventory(root)
 sys.path.insert(0,str(root/'app/cli'))
 from preflight import verify
 preflight=verify(root,full_platform_hash=True)
 if preflight_only:return {'status':'PASS_PREFLIGHT','product_lock_identity':preflight['product_lock_identity'],'legacy_dependency_count':0}
 sys.path.insert(0,str(root/'app/workflow'))
 from pastila_scout.vnext_state_sqlite_v1 import SQLiteStateStore
 store=SQLiteStateStore(root=root/'state',database=Path('product.sqlite3'),writer_identity='vnext-product-runtime-v1')
 integrity=store.verify_integrity();sources=json.loads((root/'config/sources.json').read_text(encoding='utf-8'))
 if integrity.get('status')!='PASS' or not isinstance(sources,(list,dict)):raise RuntimeError('startup contract failed')
 return {'status':'PASS_STARTUP_READY','product_lock_identity':preflight['product_lock_identity'],'state_integrity':'PASS','model_load':False,'inference':False,'legacy_dependency_count':0}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--preflight-only',action='store_true');a=p.parse_args();print(json.dumps(startup(a.root,a.preflight_only),sort_keys=True))
