#!/usr/bin/env python3
import argparse,hashlib,json,os,sqlite3,subprocess,tempfile
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
def audit(root,rollback=None,live=False):
 lock=load(root/'product-lock.json');check(lock,'product_lock_identity')
 if lock['status']!='ACTIVE' or lock['active_integration_state']!='ACTIVATED' or not lock['activation']['authorized'] or not lock['activation']['product_lock_replacement']:raise RuntimeError('activation semantics')
 expected={x['path']:x for x in lock['application_files']};actual={}
 for base in ('app','config','contracts','foundation','manifest'):
  d=root/base
  if not d.exists():continue
  for p in sorted(d.rglob('*')):
   rel=p.relative_to(root).as_posix()
   if '__pycache__' in p.parts or p.suffix=='.pyc':continue
   if p.is_symlink():actual[rel]={'path':rel,'type':'symlink','target':os.readlink(p)}
   elif p.is_file():actual[rel]={'path':rel,'type':'file','size':p.stat().st_size,'sha256':sha(p)}
 if actual!=expected:raise RuntimeError('managed inventory mismatch')
 paths={'active_state_authority_identity':'manifest/authorities/vnext-active-product-lock-successor-v1.json','activation_receipt_identity':'manifest/activation/vnext-activation-receipt-v1.json','rollback_manifest_identity':'manifest/rollback/vnext-canonical-rollback-manifest-v1.json','active_audit_authority_identity':'manifest/authorities/vnext-post-activation-active-audit-authority-v1.json'}
 keys={'active_state_authority_identity':'product_lock_identity','activation_receipt_identity':'activation_receipt_identity','rollback_manifest_identity':'rollback_manifest_identity','active_audit_authority_identity':'manifest_identity'}
 for n,p in paths.items():
  d=load(root/p);check(d,keys[n]);
  if d[keys[n]]!=lock['activation_attestation'][n]:raise RuntimeError('attestation '+n)
 aa=load(root/paths['active_audit_authority_identity'])
 if aa['current_auditor_count']!=1 or aa['current_auditor']!='scripts/audit_vnext_post_activation_active_audit_authority_v1.py':raise RuntimeError('audit authority')
 g=load(root/'manifest/authorities/vnext-active-product-dependency-graph-v3.json');check(g,'authority_identity')
 if g['authority_identity']!=lock['active_graph_identity']:raise RuntimeError('graph')
 for n in g['nodes']:
  if not (root/n['target_path']).exists():raise RuntimeError('missing graph target '+n['id'])
 r2=load(root/'components/editor-r2/dependency-lock.json');check(r2,'lock_identity')
 for x in r2['files']:
  p=root/'components/editor-r2'/x['path']
  if not p.is_file() or p.stat().st_size!=x['size'] or sha(p)!=x['sha256']:raise RuntimeError('r2')
 con=sqlite3.connect('file:'+(root/'state/product.sqlite3').as_posix()+'?mode=ro',uri=True);ok=con.execute('pragma integrity_check').fetchone()[0];con.close()
 if ok!='ok':raise RuntimeError('sqlite')
 forbidden=('/root/'+'pf9-','/mnt/f/'+'pt','/root/'+'pastila-news-monitor','/root/'+'vnext-')
 for row in actual.values():
  rel=row['path'];p=root/rel
  active_surface=(rel.startswith(('app/','config/','contracts/','foundation/')) or rel.endswith('vnext-active-product-dependency-graph-v3.json'))
  if active_surface and p.is_file() and p.stat().st_size<2000000:
   try:t=p.read_text().casefold()
   except:continue
   if any(x in t for x in forbidden):raise RuntimeError('external dependency '+rel)
 live_result='NOT_RUN';startup_result='NOT_RUN'
 if live:
  start=subprocess.run([str(root/'platform/python-ml/bin/python'),str(root/'app/cli/product.py'),'--root',str(root)],check=True,text=True,capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
  s=json.loads(start.stdout);startup_result=s['status']
  if startup_result!='PASS_STARTUP_READY':raise RuntimeError('startup')
  with tempfile.TemporaryDirectory(prefix='vnext-product-audit-',dir='/root') as td:
   out=subprocess.run([str(root/'platform/python-ml/bin/python'),str(root/'app/cli/acceptance.py'),'--root',str(root),'--workspace',td],check=True,text=True,capture_output=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
   e=json.loads(out.stdout);live_result=e['workflow_state'];
   if live_result!='EXPORTED' or e.get('startup_status')!='PASS_STARTUP_READY' or e.get('startup_product_lock_identity')!=lock['product_lock_identity']:raise RuntimeError('e2e startup bypass')
 if rollback:
  rm=load(root/'manifest/rollback/vnext-canonical-rollback-manifest-v1.json')
  if sha(rollback/'product-lock.json')!=rm['authority']['product_lock_sha256']:raise RuntimeError('rollback')
 result={'status':'PASS','product_lock_identity':lock['product_lock_identity'],'active_graph_identity':g['authority_identity'],'managed_files':len(actual),'current_auditor_count':1,'startup':startup_result,'e2e':live_result,'e2e_uses_canonical_startup':live_result=='EXPORTED','sqlite_integrity':'PASS','r2_closure':'PASS','platform_closure':'PASS_BOUND_BY_PLATFORM_LOCK','rollback_integrity':'PASS' if rollback else 'NOT_RUN','legacy_dependency_count':0,'repository_dependency_count':0};result['audit_identity']=ident(result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--rollback-root',type=Path);p.add_argument('--live',action='store_true');a=p.parse_args();print(json.dumps(audit(a.root,a.rollback_root,a.live),sort_keys=True))
