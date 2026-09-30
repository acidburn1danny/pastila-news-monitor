#!/usr/bin/env python3
"""Atomic activation with authority bytes separated from declared mutable runtime bytes."""
import argparse,hashlib,json,os,subprocess,types
from pathlib import Path

ACTIVE=Path('/root/pastila-vnext/v1')
ROOT_CONTAINERS={'app','config','contracts','foundation','manifest','components','platform','state'}

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for chunk in iter(lambda:stream.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def canonical(value):
 return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()

def identity(value):
 return hashlib.sha256(canonical(value)).hexdigest()

def load_policy(root):
 path=root/'app/cli/runtime_bytes_policy.py'
 module=types.ModuleType('runtime_bytes_policy')
 exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
 return module

def surface_snapshot(root):
 root=root.resolve(strict=True);policy=load_policy(root);authority=[];mutable=[];cache=[]
 for path in sorted(root.rglob('*'),key=lambda p:p.relative_to(root).as_posix()):
  rel=path.relative_to(root).as_posix()
  if rel in ROOT_CONTAINERS and path.is_dir() and not path.is_symlink():continue
  kind=policy.classify(rel,False)
  if kind==policy.FORBIDDEN:raise RuntimeError('forbidden activation byte: '+rel)
  if kind==policy.ALLOWED_REGENERABLE_RUNTIME:
   if path.is_symlink() or not path.is_file():raise RuntimeError('invalid runtime cache: '+rel)
   cache.append(rel);continue
  meta=path.lstat()
  if kind==policy.MUTABLE_STATE:
   if path.is_symlink() or not path.is_file():raise RuntimeError('invalid mutable state: '+rel)
   mutable.append({'path':rel,'type':'file','uid':meta.st_uid,'gid':meta.st_gid,'mode':meta.st_mode&0o777});continue
  if path.is_symlink():row={'path':rel,'type':'symlink','target':os.readlink(path)}
  elif path.is_dir():row={'path':rel,'type':'directory'}
  elif path.is_file():row={'path':rel,'type':'file','size':meta.st_size,'sha256':sha(path)}
  else:raise RuntimeError('unsupported activation entry: '+rel)
  row.update({'uid':meta.st_uid,'gid':meta.st_gid,'mode':meta.st_mode&0o777})
  authority.append(row)
 return {'authority':authority,'mutable':mutable,'cache':cache,'authority_identity':identity(authority)}

def verify_post_swap(root,baseline):
 current=surface_snapshot(root)
 if current['authority']!=baseline['authority']:raise RuntimeError('managed authority drift')
 if current['mutable']!=baseline['mutable']:raise RuntimeError('mutable state shape drift')
 return current

def full_tree_identity(root):
 rows=[]
 for p in sorted(root.rglob('*'),key=lambda p:p.relative_to(root).as_posix()):
  rel=p.relative_to(root).as_posix()
  if p.is_symlink():rows.append({'path':rel,'type':'symlink','target':os.readlink(p)})
  elif p.is_dir():rows.append({'path':rel,'type':'directory'})
  elif p.is_file():rows.append({'path':rel,'type':'file','size':p.stat().st_size,'sha256':sha(p)})
  else:raise RuntimeError('unsupported rollback entry: '+rel)
 return identity(rows)

def atomic_swap(current,staged,backup,validate_after):
 old_tree=full_tree_identity(current);old_lock=sha(current/'product-lock.json');failed=current.parent/(current.name+'.failed-activation')
 swapped=False
 try:
  os.replace(current,backup);os.replace(staged,current);swapped=True
  result=validate_after(current)
  if full_tree_identity(backup)!=old_tree or sha(backup/'product-lock.json')!=old_lock:raise RuntimeError('rollback root drift')
  return result
 except BaseException:
  if swapped:
   if failed.exists():raise RuntimeError('failed root collision')
   os.replace(current,failed);os.replace(backup,current)
   if full_tree_identity(current)!=old_tree or sha(current/'product-lock.json')!=old_lock:raise RuntimeError('ROLLBACK_BYTE_IDENTITY_FAILURE')
  raise

def activate(active,staged,backup,protected_rollback,repo,expected_commit,expected_lock_identity,expected_lock_sha,expected_graph_identity):
 if active!=ACTIVE:raise RuntimeError('active root mismatch')
 if backup.exists() or active.parent!=staged.parent or active.stat().st_dev!=staged.stat().st_dev:raise RuntimeError('non-atomic activation roots')
 head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
 dirty=subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).strip()
 if head!=expected_commit or dirty:raise RuntimeError('assembly authority mismatch')
 lock=json.loads((staged/'product-lock.json').read_text());graph=json.loads((staged/'manifest/authorities/vnext-active-product-dependency-graph-v3.json').read_text())
 if lock['product_lock_identity']!=expected_lock_identity or sha(staged/'product-lock.json')!=expected_lock_sha or graph['authority_identity']!=expected_graph_identity or lock['active_graph_identity']!=expected_graph_identity:raise RuntimeError('staging identity mismatch')
 baseline=surface_snapshot(staged)
 py=staged/'platform/python-ml/bin/python';product=staged/'app/cli/product.py'
 subprocess.run([str(py),'-I','-B',str(product),'--root',str(staged),'--preflight-only'],check=True,capture_output=True,text=True)
 def validate_after(current):
  py=current/'platform/python-ml/bin/python';product=current/'app/cli/product.py';auditor=current/'app/cli/audit.py'
  subprocess.run([str(py),'-I','-B',str(product),'--root',str(current),'--preflight-only'],check=True,capture_output=True,text=True)
  audit=json.loads(subprocess.run([str(py),'-I','-B',str(auditor),'--root',str(current),'--rollback-root',str(protected_rollback),'--live'],check=True,capture_output=True,text=True).stdout)
  if audit['status']!='PASS' or audit['e2e']!='EXPORTED':raise RuntimeError('post-activation audit')
  post=verify_post_swap(current,baseline)
  return {'status':'PASS_ACTIVATED','authority_identity':post['authority_identity'],'runtime_cache':post['cache'],'audit':audit,'rollback_root':str(backup)}
 return atomic_swap(active,staged,backup,validate_after)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--staged',type=Path,required=True);p.add_argument('--backup',type=Path,required=True);p.add_argument('--protected-rollback',type=Path,required=True);p.add_argument('--repo',type=Path,required=True);p.add_argument('--expected-commit',required=True);p.add_argument('--expected-lock-identity',required=True);p.add_argument('--expected-lock-sha256',required=True);p.add_argument('--expected-graph-identity',required=True);a=p.parse_args()
 print(json.dumps(activate(ACTIVE,a.staged,a.backup,a.protected_rollback,a.repo,a.expected_commit,a.expected_lock_identity,a.expected_lock_sha256,a.expected_graph_identity),sort_keys=True))
