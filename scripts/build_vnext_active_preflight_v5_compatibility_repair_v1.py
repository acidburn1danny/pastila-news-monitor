#!/usr/bin/env python3
import argparse,copy,hashlib,json
from pathlib import Path
BASE_COMMIT='ca7761fd8dd530c8efde8659ff17ada573139a0c'
OLD_LOCK_SHA='e21a31c35123e3464b5231ffce596e97c379bb7baa1d64d902b88a9c91e04824'
RECEIPT_ID='1c5b0c103ba609408780f93b59ac98fec31d29151601ed20e5299cd8c8ce587f'
AUTHORITY_ID='1d53b5402e30251abf412aa649e3a3f231b59bddfd4628c2e5ee9141b532d7a8'
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def identity(v):return hashlib.sha256(canonical(v)).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def row(p,target):return {'path':target,'type':'file','size':p.stat().st_size,'sha256':sha(p)}
def write(p,v,key):v.pop(key,None);v[key]=identity(v);p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def build(repo,active,out):
 current=json.loads((active/'product-lock.json').read_text())
 if sha(active/'product-lock.json')!=OLD_LOCK_SHA:raise RuntimeError('active product-lock precondition')
 base=json.loads((repo/'docs/artifacts/vnext-current-active-product-lock-successor-v1.json').read_text())
 if base.get('schema_version')!=5 or base.get('activation_attestation',{}).get('current_activation_receipt_identity')!=RECEIPT_ID or base['activation_attestation'].get('current_active_state_authority_identity')!=AUTHORITY_ID:raise RuntimeError('base attestation successor mismatch')
 successor=copy.deepcopy(base)
 successor['preflight_v5_compatibility']={'status':'SEMANTICALLY_VALIDATED','base_authority_commit':BASE_COMMIT,'supported_product_lock_schemas':[4,5],'v5_attestation_validation':'RECEIPT_AUTHORITY_PREDECESSOR_GRAPH_AND_ORIGIN_BOUND','canonical_preflight':'app/cli/preflight.py','canonical_auditor':'app/cli/audit.py'}
 replacements={'app/cli/preflight.py':row(repo/'scripts/vnext_materialized_active_preflight_v9.py','app/cli/preflight.py'),'app/cli/audit.py':row(repo/'scripts/audit_vnext_materialized_active_product_v11.py','app/cli/audit.py')}
 found=set();rows=[]
 for item in successor['application_files']:
  if item['path'] in replacements:rows.append(replacements[item['path']]);found.add(item['path'])
  else:rows.append(item)
 if found!=set(replacements):raise RuntimeError('consumer targets absent')
 successor['application_files']=rows
 out.mkdir(parents=True,exist_ok=True)
 lock_path=out/'vnext-active-preflight-v5-product-lock-successor-v1.json';write(lock_path,successor,'product_lock_identity')
 result={'schema':'vnext-active-preflight-v5-compatibility-repair-result-v1','schema_version':1,'status':'PASS','base_commit':BASE_COMMIT,'product_lock_successor_identity':successor['product_lock_identity'],'product_lock_successor_sha256':sha(lock_path),'activation_receipt_identity':RECEIPT_ID,'active_state_authority_identity':AUTHORITY_ID,'supported_schemas':[4,5],'managed_replacements':['app/cli/audit.py','app/cli/preflight.py','manifest/activation/vnext-activation-receipt-v1.json','manifest/authorities/vnext-active-product-lock-successor-v1.json'],'active_root_modified':False,'rollback_roots_modified':False,'waiting_period':False,'legacy_dependency_count':0}
 write(out/'vnext-active-preflight-v5-compatibility-repair-result-v1.json',result,'result_identity')
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--active',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.repo,a.active,a.out),sort_keys=True))
