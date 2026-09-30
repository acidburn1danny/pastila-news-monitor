#!/usr/bin/env python3
import argparse,copy,hashlib,json,types
from pathlib import Path
CONTROLLER_COMMIT='bbb7068777a0010132f0ee1e39dd345cf9eb6fa7'
CANDIDATE_COMMIT='929972ebc89e54c7d7d94b87346b2faf50823608'
LOCK_ID='5e31722e1e78fb44d2abd74c51a00e4074a67ff254c5497bfde64e228e7b9653'
LOCK_SHA='e21a31c35123e3464b5231ffce596e97c379bb7baa1d64d902b88a9c91e04824'
GRAPH_ID='5a3129321375e45491eed0ade83ad218c2a74f3a5ea6241bdc3d68acc111100c'
SURFACE_ID='db997a11045e8aef32891743d9aaed282cac436d6cc3fcb113f07ab140e9e738'
AUDIT_ID='57c0630dc366d36d42c7c8a5356cb8499dcfac024daae387906eb9eeb5cb4045'
ROLLBACK_LOCK_SHA='0ff93c4d9f550c8458d2223ae91627903bf02dc24973c59d3069fa94ada1100e'
PROTECTED_ROLLBACK_LOCK_SHA='2ddc484171f3b58f0f10ce4c4c73c1db51323d5c545320c578dc17ebb3edb4e6'
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def identity(v):return hashlib.sha256(canonical(v)).hexdigest()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v,key):v.pop(key,None);v[key]=identity(v);p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def load_controller(repo):
 p=repo/'scripts/vnext_atomic_activation_managed_mutable_v1.py';m=types.ModuleType('controller');exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);return m
def build(repo,active,rollback,protected,out):
 current=json.loads((active/'product-lock.json').read_text())
 if current['product_lock_identity']!=LOCK_ID or sha(active/'product-lock.json')!=LOCK_SHA or current['active_graph_identity']!=GRAPH_ID:raise RuntimeError('active identity mismatch')
 controller=load_controller(repo);surface=controller.surface_snapshot(active)
 if surface['authority_identity']!=SURFACE_ID:raise RuntimeError('active surface mismatch')
 if sha(rollback/'product-lock.json')!=ROLLBACK_LOCK_SHA or sha(protected/'product-lock.json')!=PROTECTED_ROLLBACK_LOCK_SHA:raise RuntimeError('rollback binding mismatch')
 receipt={'schema':'vnext-current-activation-receipt-v1','schema_version':1,'status':'ATTESTED_CURRENT_ACTIVATION','temporal_claim':{'activated_at':None,'status':'NOT_RECORDED_NO_RETROACTIVE_FABRICATION'},'controller_authority_commit':CONTROLLER_COMMIT,'candidate_commit':CANDIDATE_COMMIT,'candidate':{'product_lock_identity':LOCK_ID,'product_lock_sha256':LOCK_SHA,'active_graph_identity':GRAPH_ID},'atomic_swap':{'mechanism':'renameat2(RENAME_EXCHANGE)','active_root':'/root/pastila-vnext/v1','result':'PASS_ACTIVATED'},'active':{'authority_surface_identity':SURFACE_ID,'audit_identity':AUDIT_ID,'startup':'PASS_STARTUP_READY','integrated_e2e':'EXPORTED','managed_files':30},'rollback':{'current_root':'/root/pastila-vnext/.rollback-pre-exchange-5e31722e','product_lock_sha256':ROLLBACK_LOCK_SHA,'protected_historical_root':'/root/pastila-vnext/.rollback-pre-68fb2c347367','protected_product_lock_sha256':PROTECTED_ROLLBACK_LOCK_SHA},'repository_dependency_count':0,'legacy_dependency_count':0}
 receipt['activation_receipt_identity']=identity(receipt)
 successor=copy.deepcopy(current);successor['schema_version']=5;successor['supersedes_product_lock_identity']=LOCK_ID;successor['activation_attestation']={'current_activation_receipt_identity':receipt['activation_receipt_identity'],'controller_authority_commit':CONTROLLER_COMMIT,'candidate_commit':CANDIDATE_COMMIT,'active_authority_surface_identity':SURFACE_ID,'audit_identity':AUDIT_ID,'mechanism':'renameat2(RENAME_EXCHANGE)','rollback_product_lock_sha256':ROLLBACK_LOCK_SHA,'historical_attestation':current.get('activation_attestation')}
 successor.pop('product_lock_identity',None);successor['product_lock_identity']=identity(successor)
 authority={'schema':'vnext-current-active-state-authority-v1','schema_version':1,'status':'ACTIVATED_ATTESTED','active_root':'/root/pastila-vnext/v1','installed_product_lock':{'identity':LOCK_ID,'sha256':LOCK_SHA},'attestation_successor_product_lock':{'identity':successor['product_lock_identity'],'sha256':None},'activation_receipt_identity':receipt['activation_receipt_identity'],'controller_authority_commit':CONTROLLER_COMMIT,'candidate_commit':CANDIDATE_COMMIT,'active_graph_identity':GRAPH_ID,'active_authority_surface_identity':SURFACE_ID,'audit_identity':AUDIT_ID,'rollback':receipt['rollback'],'legacy_dependency_count':0}
 out.mkdir(parents=True,exist_ok=True)
 write(out/'vnext-current-activation-receipt-v1.json',receipt,'activation_receipt_identity')
 write(out/'vnext-current-active-product-lock-successor-v1.json',successor,'product_lock_identity')
 authority['attestation_successor_product_lock']['sha256']=sha(out/'vnext-current-active-product-lock-successor-v1.json')
 authority['active_state_authority_identity']=identity(authority)
 write(out/'vnext-current-active-state-authority-v1.json',authority,'active_state_authority_identity')
 return {'activation_receipt_identity':receipt['activation_receipt_identity'],'product_lock_successor_identity':successor['product_lock_identity'],'product_lock_successor_sha256':sha(out/'vnext-current-active-product-lock-successor-v1.json'),'active_state_authority_identity':authority['active_state_authority_identity'],'active_surface_identity':surface['authority_identity'],'status':'PASS'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--active',type=Path,required=True);p.add_argument('--rollback',type=Path,required=True);p.add_argument('--protected-rollback',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.repo,a.active,a.rollback,a.protected_rollback,a.out),sort_keys=True))
