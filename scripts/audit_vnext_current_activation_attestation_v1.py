#!/usr/bin/env python3
import argparse,json,types
from pathlib import Path
def load(path,name):
 m=types.ModuleType(name);exec(compile(path.read_bytes(),str(path),'exec'),m.__dict__);return m
def verify(v,key,b):
 claim=v[key];copy={k:x for k,x in v.items() if k!=key}
 if claim!=b.identity(copy):raise RuntimeError('identity mismatch '+key)
def audit(repo,active,rollback,protected):
 b=load(repo/'scripts/build_vnext_current_activation_attestation_v1.py','builder');art=repo/'docs/artifacts'
 receipt=json.loads((art/'vnext-current-activation-receipt-v1.json').read_text());lock=json.loads((art/'vnext-current-active-product-lock-successor-v1.json').read_text());authority=json.loads((art/'vnext-current-active-state-authority-v1.json').read_text())
 verify(receipt,'activation_receipt_identity',b);verify(lock,'product_lock_identity',b);verify(authority,'active_state_authority_identity',b)
 if receipt['temporal_claim']!={'activated_at':None,'status':'NOT_RECORDED_NO_RETROACTIVE_FABRICATION'}:raise RuntimeError('temporal evidence fabrication')
 if receipt['candidate']['product_lock_identity']!=b.LOCK_ID or receipt['candidate']['product_lock_sha256']!=b.LOCK_SHA or receipt['atomic_swap']['mechanism']!='renameat2(RENAME_EXCHANGE)':raise RuntimeError('receipt binding')
 if authority['activation_receipt_identity']!=receipt['activation_receipt_identity'] or authority['installed_product_lock']!={'identity':b.LOCK_ID,'sha256':b.LOCK_SHA}:raise RuntimeError('authority binding')
 if lock['activation_attestation']['current_activation_receipt_identity']!=receipt['activation_receipt_identity'] or lock['activation_attestation']['current_active_state_authority_identity']!=authority['active_state_authority_identity'] or lock['supersedes_product_lock_identity']!=b.LOCK_ID:raise RuntimeError('lock successor binding')
 current=json.loads((active/'product-lock.json').read_text())
 if current['product_lock_identity']!=b.LOCK_ID or b.sha(active/'product-lock.json')!=b.LOCK_SHA:raise RuntimeError('active lock drift')
 current_rows={x['path']:x for x in current['application_files']};next_rows={x['path']:x for x in lock['application_files']}
 if set(current_rows)!=set(next_rows):raise RuntimeError('managed path set drift')
 expected={b.RECEIPT_TARGET:b.row(art/'vnext-current-activation-receipt-v1.json',b.RECEIPT_TARGET),b.AUTHORITY_TARGET:b.row(art/'vnext-current-active-state-authority-v1.json',b.AUTHORITY_TARGET)}
 for path,row in next_rows.items():
  if path in expected:
   if row!=expected[path]:raise RuntimeError('successor managed row mismatch '+path)
  elif row!=current_rows[path]:raise RuntimeError('unjustified managed row change '+path)
 controller=b.load_controller(repo);surface=controller.surface_snapshot(active)
 if surface['authority_identity']!=b.SURFACE_ID:raise RuntimeError('active surface drift')
 if b.sha(rollback/'product-lock.json')!=b.ROLLBACK_LOCK_SHA or b.sha(protected/'product-lock.json')!=b.PROTECTED_ROLLBACK_LOCK_SHA:raise RuntimeError('rollback drift')
 result={'schema':'vnext-current-activation-attestation-repair-result-v1','status':'PASS','blockers':0,'activation_receipt_identity':receipt['activation_receipt_identity'],'product_lock_successor_identity':lock['product_lock_identity'],'product_lock_successor_sha256':b.sha(art/'vnext-current-active-product-lock-successor-v1.json'),'active_state_authority_identity':authority['active_state_authority_identity'],'active_surface_identity':surface['authority_identity'],'managed_inventory_updates':sorted(expected),'prospective_installability':'PASS_EXACT_TWO_MANAGED_REPLACEMENTS','active_root_modified':False,'rollback_roots_modified':False,'candidate_modified':False,'waiting_period':False,'legacy_dependency_count':0}
 result['result_identity']=b.identity(result);return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--active',type=Path,required=True);p.add_argument('--rollback',type=Path,required=True);p.add_argument('--protected-rollback',type=Path,required=True);a=p.parse_args();print(json.dumps(audit(a.repo,a.active,a.rollback,a.protected_rollback),sort_keys=True))
