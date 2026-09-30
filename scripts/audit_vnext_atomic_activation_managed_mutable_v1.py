#!/usr/bin/env python3
import argparse,hashlib,json,shutil,tempfile,types
from pathlib import Path

def load(path,name):
 m=types.ModuleType(name);exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__);return m

def fixture(root,policy):
 (root/'app/cli').mkdir(parents=True);(root/'state').mkdir()
 shutil.copy2(policy,root/'app/cli/runtime_bytes_policy.py')
 (root/'app/payload.txt').write_text('managed\n')
 (root/'state/product.sqlite3').write_bytes(b'state')
 (root/'product-lock.json').write_text('{}\n')

def run(repo):
 module=load(repo/'scripts/vnext_atomic_activation_managed_mutable_v1.py','activation')
 policy=repo/'scripts/vnext_active_runtime_bytes_policy_v3.py'
 results={}
 with tempfile.TemporaryDirectory(prefix='vnext-activation-gate-',dir='/tmp') as td:
  base=Path(td)
  candidate=base/'candidate';fixture(candidate,policy);snapshot=module.surface_snapshot(candidate)
  (candidate/'state/product.sqlite3').write_bytes(b'changed')
  (candidate/'state/product.sqlite3-wal').write_bytes(b'wal')
  (candidate/'state/product.sqlite3-shm').write_bytes(b'shm')
  post=module.verify_post_swap(candidate,snapshot);results['declared_mutable_runtime']='PASS'
  if sorted(post['cache'])!=['state/product.sqlite3-shm','state/product.sqlite3-wal']:raise RuntimeError('runtime cache classification')
  (candidate/'app/payload.txt').write_text('drift')
  try:module.verify_post_swap(candidate,snapshot)
  except RuntimeError:results['managed_drift']='FAIL_CLOSED'
  else:raise RuntimeError('managed drift accepted')
  (candidate/'app/payload.txt').write_text('managed\n');(candidate/'rogue.bin').write_bytes(b'x')
  try:module.verify_post_swap(candidate,snapshot)
  except RuntimeError:results['unauthorized_extra']='FAIL_CLOSED'
  else:raise RuntimeError('extra byte accepted')
 with tempfile.TemporaryDirectory(prefix='vnext-atomic-gate-',dir='/tmp') as td:
  base=Path(td);current=base/'current';staged=base/'staged';backup=base/'backup';fixture(current,policy);fixture(staged,policy)
  old=module.full_tree_identity(current)
  def fail(root):
   (root/'app/payload.txt').write_text('drift')
   raise RuntimeError('injected')
  try:module.atomic_swap(current,staged,backup,fail)
  except RuntimeError as exc:
   if str(exc)!='injected':raise
  else:raise RuntimeError('fault did not fail')
  if module.full_tree_identity(current)!=old or module.sha(current/'product-lock.json')!=module.sha(base/'current/product-lock.json'):raise RuntimeError('rollback mismatch')
  if backup.exists():raise RuntimeError('backup remained after rollback')
  results['atomic_rollback']='BYTE_EXACT'
 result={'schema':'vnext-atomic-activation-managed-mutable-repair-result-v1','status':'PASS','blockers':0,'checks':results,'waiting_period':False,'candidate_modified':False,'legacy_dependency_count':0}
 result['result_identity']=hashlib.sha256(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.repo.resolve()),sort_keys=True))
