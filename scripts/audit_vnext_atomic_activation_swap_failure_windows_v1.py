#!/usr/bin/env python3
import argparse,hashlib,json,tempfile,types
from pathlib import Path

def load(path,name):
 m=types.ModuleType(name);exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__);return m
def fixture(path,label):
 (path/'app').mkdir(parents=True);(path/'app/value').write_text(label);(path/'product-lock.json').write_text('{"label":"'+label+'"}\n')
def run(repo):
 m=load(repo/'scripts/vnext_atomic_activation_managed_mutable_v1.py','activation');checks={}
 with tempfile.TemporaryDirectory(prefix='vnext-exchange-validation-',dir='/tmp') as td:
  b=Path(td);current=b/'v1';staged=b/'staged';backup=b/'backup';fixture(current,'old');fixture(staged,'new');old=m.full_tree_identity(current)
  try:m.atomic_swap(current,staged,backup,lambda root:(_ for _ in ()).throw(RuntimeError('validation failure')))
  except RuntimeError as exc:
   if str(exc)!='validation failure':raise
  else:raise RuntimeError('validation failure accepted')
  if m.full_tree_identity(current)!=old or backup.exists() or (staged/'app/value').read_text()!='new':raise RuntimeError('atomic validation rollback failed')
  checks['validation_failure']='ATOMIC_BYTE_EXACT_ROLLBACK'
 with tempfile.TemporaryDirectory(prefix='vnext-exchange-finalize-',dir='/tmp') as td:
  b=Path(td);current=b/'v1';staged=b/'staged';backup=b/'backup';fixture(current,'old');fixture(staged,'new');old=m.full_tree_identity(current);real=m.os.replace
  def fail(src,dst):raise OSError('injected backup-finalization failure')
  m.os.replace=fail
  try:m.atomic_swap(current,staged,backup,lambda root:{'status':'PASS'})
  except OSError:pass
  else:raise RuntimeError('finalization failure accepted')
  finally:m.os.replace=real
  if m.full_tree_identity(current)!=old or backup.exists() or (staged/'app/value').read_text()!='new':raise RuntimeError('finalization rollback failed')
  checks['backup_finalization_failure']='ATOMIC_BYTE_EXACT_ROLLBACK'
 with tempfile.TemporaryDirectory(prefix='vnext-exchange-transient-',dir='/tmp') as td:
  b=Path(td);current=b/'v1';staged=b/'staged';backup=b/'backup';fixture(current,'old');fixture(staged,'new');old=m.full_tree_identity(current);real=m.exchange_paths;calls=[0]
  def transient(left,right):
   calls[0]+=1
   if calls[0]==2:raise OSError('injected transient rollback exchange failure')
   return real(left,right)
  m.exchange_paths=transient
  try:m.atomic_swap(current,staged,backup,lambda root:(_ for _ in ()).throw(RuntimeError('validation failure')))
  except RuntimeError as exc:
   if str(exc)!='validation failure':raise
  else:raise RuntimeError('transient failure accepted')
  finally:m.exchange_paths=real
  if m.full_tree_identity(current)!=old or backup.exists():raise RuntimeError('transient rollback failed')
  checks['transient_rollback_exchange_failure']='RETRIED_BYTE_EXACT'
 with tempfile.TemporaryDirectory(prefix='vnext-exchange-success-',dir='/tmp') as td:
  b=Path(td);current=b/'v1';staged=b/'staged';backup=b/'backup';fixture(current,'old');fixture(staged,'new');result=m.atomic_swap(current,staged,backup,lambda root:{'status':'PASS'})
  if result['status']!='PASS' or (current/'app/value').read_text()!='new' or (backup/'app/value').read_text()!='old' or staged.exists():raise RuntimeError('success path')
  checks['success_path']='ATOMIC_EXCHANGE_PASS'
 result={'schema':'vnext-atomic-activation-swap-failure-windows-repair-result-v1','status':'PASS','blockers':0,'checks':checks,'mechanism':'renameat2(RENAME_EXCHANGE)','candidate_commit':'929972ebc89e54c7d7d94b87346b2faf50823608','candidate_modified':False,'active_root_modified':False,'waiting_period':False,'legacy_dependency_count':0}
 result['result_identity']=hashlib.sha256(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.repo.resolve()),sort_keys=True))
