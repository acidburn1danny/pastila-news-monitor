#!/usr/bin/env python3
import sys
if sys.path:sys.path.pop(0)
import argparse,hashlib,json,os,sqlite3,subprocess,tempfile,types
from pathlib import Path
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def ident(v):return hashlib.sha256(canon(v)).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(8*1024*1024),b''):h.update(c)
 return h.hexdigest()
def load(p):return json.loads(p.read_text())
def check(v,k):
 if v[k]!=ident({x:y for x,y in v.items() if x!=k}):raise RuntimeError('identity '+k)
def historical_audit_identity(att):
 h=att.get('historical_attestation',{})
 for _ in range(8):
  if 'active_audit_authority_identity' in h:return h['active_audit_authority_identity']
  h=h.get('historical_attestation',{}) if isinstance(h,dict) else {}
 raise RuntimeError('historical active audit authority')
def secure_policy(root,lock):
 p=root/'app/cli/runtime_bytes_policy.py';row={x['path']:x for x in lock['application_files']}.get('app/cli/runtime_bytes_policy.py')
 if not row or p.stat().st_size!=row['size'] or sha(p)!=row['sha256']:raise RuntimeError('policy bootstrap mismatch')
 m=types.ModuleType('runtime_bytes_policy');exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def audit(root,rollback=None,live=False):
 root=root.resolve(strict=True)
 for p in root.rglob("*"):
  meta=p.lstat()
  if meta.st_uid!=0 or meta.st_gid!=0:raise RuntimeError("product filesystem owner mismatch: "+p.relative_to(root).as_posix())
  if not p.is_symlink() and meta.st_mode & 0o022:raise RuntimeError("product filesystem permissions mismatch: "+p.relative_to(root).as_posix())
  if not (p.is_symlink() or p.is_dir() or p.is_file()):raise RuntimeError("product filesystem entry type mismatch: "+p.relative_to(root).as_posix())
  if not p.is_symlink() and p.is_file() and p.stat().st_nlink!=1:raise RuntimeError("product file ownership mismatch: "+p.relative_to(root).as_posix())
 lock=load(root/'product-lock.json');check(lock,'product_lock_identity');policy=secure_policy(root,lock)
 py=root/'platform/python-ml/bin/python';product=root/'app/cli/product.py'
 pre=subprocess.run([str(py),'-I','-B',str(product),'--root',str(root),'--preflight-only'],check=True,text=True,capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
 if json.loads(pre.stdout).get('status')!='PASS_PREFLIGHT':raise RuntimeError('canonical preflight')
 if lock['status']!='ACTIVE' or lock['active_integration_state']!='ACTIVATED' or not lock['activation']['authorized'] or not lock['activation']['product_lock_replacement']:raise RuntimeError('activation semantics')
 expected={x['path']:x for x in lock['application_files']};actual={}
 for base in ('app','config','contracts','foundation','manifest'):
  for p in sorted((root/base).rglob('*')):
   rel=p.relative_to(root).as_posix()
   if p.is_dir() and not p.is_symlink():continue
   kind=policy.classify(rel,p.is_symlink())
   if kind==policy.FORBIDDEN:raise RuntimeError('forbidden product byte '+rel)
   if kind==policy.ALLOWED_REGENERABLE_RUNTIME:continue
   if p.is_file():actual[rel]={'path':rel,'type':'file','size':p.stat().st_size,'sha256':sha(p)}
 if actual!=expected:raise RuntimeError('managed inventory mismatch')
 paths={'active_state':'manifest/authorities/vnext-active-product-lock-successor-v1.json','receipt':'manifest/activation/vnext-activation-receipt-v1.json','rollback':'manifest/rollback/vnext-canonical-rollback-manifest-v1.json','audit':'manifest/authorities/vnext-post-activation-active-audit-authority-v1.json'}
 att=lock['activation_attestation']
 if lock.get('schema_version') in (6,7,8):
  expected={'active_state':(att['current_active_state_authority_identity'],'active_state_authority_identity'),'receipt':(att['current_activation_receipt_identity'],'activation_receipt_identity'),'rollback':(att['canonical_rollback_manifest_identity'],'rollback_manifest_identity'),'audit':(historical_audit_identity(att),'manifest_identity')}
 elif lock.get('schema_version')==5:
  expected={'active_state':(att['current_active_state_authority_identity'],'active_state_authority_identity'),'receipt':(att['current_activation_receipt_identity'],'activation_receipt_identity'),'rollback':(att['historical_attestation']['rollback_manifest_identity'],'rollback_manifest_identity'),'audit':(historical_audit_identity(att),'manifest_identity')}
 elif lock.get('schema_version')==4:
  expected={'active_state':(att['active_state_authority_identity'],'product_lock_identity'),'receipt':(att['activation_receipt_identity'],'activation_receipt_identity'),'rollback':(att['rollback_manifest_identity'],'rollback_manifest_identity'),'audit':(att['active_audit_authority_identity'],'manifest_identity')}
 else:raise RuntimeError('unsupported product-lock schema')
 for n,p in paths.items():
  d=load(root/p);claimed,key=expected[n];check(d,key)
  if d[key]!=claimed:raise RuntimeError('attestation '+n)
 aa=load(root/paths['audit'])
 if aa['current_auditor_count']!=1 or aa['current_auditor']!='scripts/audit_vnext_post_activation_active_audit_authority_v1.py':raise RuntimeError('audit authority')
 g=load(root/'manifest/authorities/vnext-active-product-dependency-graph-v3.json');check(g,'authority_identity')
 if g['authority_identity']!=lock['active_graph_identity']:raise RuntimeError('graph')
 if lock.get('schema_version')in (7,8):
  bindings=lock.get('contract_authority_bindings')
  if g.get('schema_version')!=4 or g.get('contract_authority_bindings')!=bindings:raise RuntimeError('contract graph bindings')
  for name,path in {'workflow':'manifest/authorities/vnext-active-product-workflow-state-contract-v6.json','source_packet':'manifest/authorities/vnext-canonical-sourcepacket-v1-contract.json','sqlite':'manifest/authorities/vnext-consolidated-operational-state-sqlite-boundary-v7-contract.json'}.items():
   c=load(root/path);check(c,'authority_identity')
   if c['authority_identity']!=bindings[name] or c.get('status')!='ACTIVE_INSTALLED_AUTHORITY':raise RuntimeError('contract authority '+name)
 if set(lock.get('components',{}))!={'R2_REFERENCE','PYTHON_ML_PLATFORM'}:raise RuntimeError('component authority set')
 targets={n['id']:n['target_path'] for n in g['nodes']}
 if targets.get('r2')!='components/editor-r2' or targets.get('python_ml')!='platform/python-ml':raise RuntimeError('component graph')
 component_entries=list((root/'components').iterdir())
 if len(component_entries)!=1 or component_entries[0].name!='editor-r2' or component_entries[0].is_symlink() or not component_entries[0].is_dir():raise RuntimeError('component namespace mismatch')
 platform_entries=list((root/'platform').iterdir())
 if len(platform_entries)!=1 or platform_entries[0].name!='python-ml' or platform_entries[0].is_symlink() or not platform_entries[0].is_dir():raise RuntimeError('platform namespace mismatch')
 for n in g['nodes']:
  if not (root/n['target_path']).exists():raise RuntimeError('missing graph target '+n['id'])
 r2root=root/'components/editor-r2';r2=load(r2root/'dependency-lock.json');check(r2,'lock_identity')
 expected_r2={x['path'] for x in r2['files']}|{'dependency-lock.json',r2['layout']['dependency_preflight']}
 actual_r2={p.relative_to(r2root).as_posix() for p in r2root.rglob('*') if p.is_file() or p.is_symlink()}
 if actual_r2!=expected_r2:raise RuntimeError('R2 exhaustive inventory')
 for rel in actual_r2:
  p=r2root/rel
  if p.is_symlink() or p.stat().st_nlink!=1:raise RuntimeError('R2 ownership')
 for x in r2['files']:
  p=r2root/x['path']
  if not p.is_file() or p.stat().st_size!=x['size'] or sha(p)!=x['sha256']:raise RuntimeError('r2')
 if any(not x.is_symlink() and x.is_file() and x.stat().st_nlink!=1 for x in (root/'platform/python-ml').rglob('*')):raise RuntimeError('platform ownership')
 con=sqlite3.connect('file:'+(root/'state/product.sqlite3').as_posix()+'?mode=ro',uri=True);ok=con.execute('pragma integrity_check').fetchone()[0];con.close()
 if ok!='ok':raise RuntimeError('sqlite')
 live_result='NOT_RUN';startup_result='NOT_RUN'
 if live:
  start=subprocess.run([str(py),'-I','-B',str(product),'--root',str(root)],check=True,text=True,capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
  s=json.loads(start.stdout);startup_result=s['status']
  if startup_result!='PASS_STARTUP_READY':raise RuntimeError('startup')
  with tempfile.TemporaryDirectory(prefix='vnext-product-audit-',dir='/root') as td:
   out=subprocess.run([str(py),'-I','-B',str(root/'app/cli/acceptance.py'),'--root',str(root),'--workspace',td],check=True,text=True,capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
   e=json.loads(out.stdout);live_result=e['workflow_state']
   if live_result!='EXPORTED' or e.get('startup_status')!='PASS_STARTUP_READY' or e.get('startup_product_lock_identity')!=lock['product_lock_identity']:raise RuntimeError('e2e startup bypass')
 if rollback:
  rm=load(root/'manifest/rollback/vnext-canonical-rollback-manifest-v1.json')
  if sha(rollback/'product-lock.json')!=rm['authority']['product_lock_sha256']:raise RuntimeError('rollback')
 result={'status':'PASS','product_lock_identity':lock['product_lock_identity'],'active_graph_identity':g['authority_identity'],'managed_files':len(actual),'current_auditor_count':1,'startup':startup_result,'e2e':live_result,'e2e_uses_canonical_startup':live_result=='EXPORTED','sqlite_integrity':'PASS','r2_closure':'PASS','platform_closure':'PASS_BOUND_BY_PLATFORM_LOCK','rollback_integrity':'PASS' if rollback else 'NOT_RUN','legacy_dependency_count':0,'repository_dependency_count':0};result['audit_identity']=ident(result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--rollback-root',type=Path);p.add_argument('--live',action='store_true');a=p.parse_args();print(json.dumps(audit(a.root,a.rollback_root,a.live),sort_keys=True))
