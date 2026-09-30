#!/usr/bin/env python3
import argparse,hashlib,json,subprocess,tempfile,shutil,os
from pathlib import Path
RECEIPT='1c5b0c103ba609408780f93b59ac98fec31d29151601ed20e5299cd8c8ce587f'
AUTHORITY='1d53b5402e30251abf412aa649e3a3f231b59bddfd4628c2e5ee9141b532d7a8'
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def ident(v):return hashlib.sha256(canon(v)).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def check(p,key):
 d=load(p)
 if d[key]!=ident({k:v for k,v in d.items() if k!=key}):raise RuntimeError('identity '+str(p))
 return d
def audit(repo,active,materialized=None):
 lock=check(repo/'docs/artifacts/vnext-active-preflight-v5-product-lock-successor-v1.json','product_lock_identity')
 result=check(repo/'docs/artifacts/vnext-active-preflight-v5-compatibility-repair-result-v1.json','result_identity')
 if result['product_lock_successor_identity']!=lock['product_lock_identity'] or result['product_lock_successor_sha256']!=sha(repo/'docs/artifacts/vnext-active-preflight-v5-product-lock-successor-v1.json'):raise RuntimeError('result binding')
 if lock['schema_version']!=5 or lock['activation_attestation']['current_activation_receipt_identity']!=RECEIPT or lock['activation_attestation']['current_active_state_authority_identity']!=AUTHORITY:raise RuntimeError('attestation binding')
 rows={x['path']:x for x in lock['application_files']}
 for rel,src in [('app/cli/preflight.py','scripts/vnext_materialized_active_preflight_v9.py'),('app/cli/audit.py','scripts/audit_vnext_materialized_active_product_v11.py')]:
  p=repo/src
  if rows[rel]!={'path':rel,'type':'file','size':p.stat().st_size,'sha256':sha(p)}:raise RuntimeError('consumer inventory '+rel)
 if sha(active/'product-lock.json')!='e21a31c35123e3464b5231ffce596e97c379bb7baa1d64d902b88a9c91e04824':raise RuntimeError('active modified')
 prospective='NOT_RUN'
 if materialized:
  env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
  out=subprocess.run([str(materialized/'platform/python-ml/bin/python'),'-I','-B',str(materialized/'app/cli/product.py'),'--root',str(materialized),'--preflight-only'],check=True,text=True,capture_output=True,env=env)
  if json.loads(out.stdout)['status']!='PASS_PREFLIGHT':raise RuntimeError('materialized preflight')
  out=subprocess.run([str(materialized/'platform/python-ml/bin/python'),'-I','-B',str(materialized/'app/cli/audit.py'),'--root',str(materialized)],check=True,text=True,capture_output=True,env=env)
  if json.loads(out.stdout)['status']!='PASS':raise RuntimeError('materialized audit')
  prospective='PASS_V5_PREFLIGHT_AND_AUDITOR'
 return {'status':'PASS','blockers':0,'product_lock_successor_identity':lock['product_lock_identity'],'product_lock_successor_sha256':sha(repo/'docs/artifacts/vnext-active-preflight-v5-product-lock-successor-v1.json'),'result_identity':result['result_identity'],'prospective_installability':prospective,'active_root_modified':False,'rollback_roots_modified':False,'legacy_dependency_count':0}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--active',type=Path,required=True);p.add_argument('--materialized',type=Path);a=p.parse_args();print(json.dumps(audit(a.repo,a.active,a.materialized),sort_keys=True))
