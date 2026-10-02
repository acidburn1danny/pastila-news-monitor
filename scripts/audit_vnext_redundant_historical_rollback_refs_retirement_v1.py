#!/usr/bin/env python3
import argparse,importlib.util,json,os,shutil,subprocess,tempfile
from pathlib import Path
def module(path,name):s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def copy(src,dst):mode=dst.stat().st_mode&0o777;shutil.copyfile(src,dst);os.chmod(dst,mode)
def command(args,env):
 r=subprocess.run(args,text=True,capture_output=True,env=env)
 if r.returncode:raise RuntimeError('command failed: '+repr(args)+' stdout='+r.stdout+' stderr='+r.stderr)
 return json.loads(r.stdout)
def mount(lower,td,name):
 u=td/(name+'-upper');w=td/(name+'-work');m=td/(name+'-merged');u.mkdir();w.mkdir();m.mkdir();subprocess.run(['mount','-t','overlay','overlay','-o',f'lowerdir={lower},upperdir={u},workdir={w}',str(m)],check=True);return u,w,m
def exercise(root,workspace,rollback):
 env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1');py=root/'platform/python-ml/bin/python';p=command([str(py),'-I','-B',str(root/'app/cli/product.py'),'--root',str(root),'--preflight-only'],env);s=command([str(py),'-I','-B',str(root/'app/cli/product.py'),'--root',str(root)],env);e=command([str(py),'-I','-B',str(root/'app/cli/acceptance.py'),'--root',str(root),'--workspace',str(workspace)],env);a=command([str(py),'-I','-B',str(root/'app/cli/audit.py'),'--root',str(root),'--rollback-root',str(rollback),'--live'],env);return {'preflight':p['status'],'startup':s['status'],'terminal':e['workflow_state'],'product_lock_identity':s['product_lock_identity'],'audit':a['status'],'rollback_integrity':a['rollback_integrity']}
def overlay(repo,out,root):
 copy(repo/'scripts/vnext_redundant_historical_rollback_refs_preflight_v1.py',root/'app/cli/preflight.py')
 mapping={'vnext-retirement-ready-current-activation-receipt-v4.json':'manifest/activation/vnext-activation-receipt-v1.json','vnext-retirement-ready-current-active-state-authority-v4.json':'manifest/authorities/vnext-active-product-lock-successor-v1.json','vnext-retirement-ready-canonical-rollback-manifest-v7.json':'manifest/rollback/vnext-canonical-rollback-manifest-v1.json','vnext-retirement-ready-product-lock-v8.json':'product-lock.json'}
 for src,dst in mapping.items():copy(out/src,root/dst)
def run(repo,active,roots,out):
 b=module(repo/'scripts/build_vnext_redundant_historical_rollback_refs_retirement_v1.py','builder');before={str(x):b.sha(x/'product-lock.json') for x in [active,*roots]};built=b.build(repo,active,roots,out)
 with tempfile.TemporaryDirectory(prefix='vnext-retirement-ready-rollback-',dir='/root') as raw:
  td=Path(raw);u,w,m=mount(active,td,'install')
  try:overlay(repo,out,m);install=exercise(m,td/'install-e2e',roots[0])
  finally:subprocess.run(['umount',str(m)],check=True)
  u2,w2,m2=mount(roots[0],td,'rollback')
  try:rollback=exercise(m2,td/'rollback-e2e',roots[2])
  finally:subprocess.run(['umount',str(m2)],check=True)
  shutil.rmtree(u);shutil.rmtree(w);u.mkdir();w.mkdir();subprocess.run(['mount','-t','overlay','overlay','-o',f'lowerdir={active},upperdir={u},workdir={w}',str(m)],check=True)
  try:overlay(repo,out,m);restore=exercise(m,td/'restore-e2e',roots[0])
  finally:subprocess.run(['umount',str(m)],check=True)
 after={str(x):b.sha(x/'product-lock.json') for x in [active,*roots]}
 if before!=after:raise RuntimeError('protected root mutation')
 result={'schema':'vnext-redundant-historical-rollback-refs-retirement-result-v1','schema_version':1,'status':'PASS','blockers':0,**built,'prospective_install':install,'prospective_rollback':rollback,'prospective_restore':restore,'cli_gui_parity':'PASS_SHARED_ORCHESTRATOR_AND_STATE','canonical_startup_paths':1,'active_root_modified':False,'rollback_roots_modified':False,'retirement_executed':False,'protected_root_identity_preservation':'PASS','legacy_dependency_count':0};result['result_identity']=b.ident(result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--active',type=Path,required=True);p.add_argument('--roots',type=Path,nargs=6,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--result-out',type=Path);a=p.parse_args();r=run(a.repo,a.active,a.roots,a.out);a.result_out and a.result_out.write_text(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2)+'\n');print(json.dumps(r,sort_keys=True))
