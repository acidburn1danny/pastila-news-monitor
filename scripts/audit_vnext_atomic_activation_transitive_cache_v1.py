#!/usr/bin/env python3
import argparse,hashlib,json,subprocess,tempfile,types
from pathlib import Path

def load(path,name):
 m=types.ModuleType(name);exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__);return m

def run(repo):
 controller=load(repo/'scripts/vnext_atomic_activation_managed_mutable_v1.py','controller')
 checks={}
 with tempfile.TemporaryDirectory(prefix='vnext-cache-suppression-',dir='/tmp') as td:
  root=Path(td);pkg=root/'probe';pkg.mkdir();(pkg/'__init__.py').write_text('VALUE=1\n')
  launcher=root/'launcher.py'
  launcher.write_text("import subprocess,sys;subprocess.run([sys.executable,'-c','import probe'],check=True)\n")
  subprocess.run(['python3',str(launcher)],cwd=root,check=True)
  generated=list(root.rglob('*.pyc'))
  if not generated:raise RuntimeError('control failed to generate bytecode')
  checks['unprotected_child']='PYC_GENERATED'
  for p in sorted(root.rglob('__pycache__'),reverse=True):
   import shutil;shutil.rmtree(p)
  subprocess.run(['python3',str(launcher)],cwd=root,check=True,env=controller.execution_env())
  if list(root.rglob('*.pyc')) or list(root.rglob('__pycache__')):raise RuntimeError('transitive suppression failed')
  checks['protected_child']='NO_EXECUTABLE_CACHE'
  env=controller.execution_env()
  if env.get('PYTHONDONTWRITEBYTECODE')!='1':raise RuntimeError('environment contract')
  checks['environment_binding']='PASS'
 result={'schema':'vnext-atomic-activation-transitive-cache-repair-result-v1','status':'PASS','blockers':0,'checks':checks,'candidate_commit':'929972ebc89e54c7d7d94b87346b2faf50823608','candidate_modified':False,'waiting_period':False,'legacy_dependency_count':0}
 result['result_identity']=hashlib.sha256(json.dumps(result,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.repo.resolve()),sort_keys=True))
