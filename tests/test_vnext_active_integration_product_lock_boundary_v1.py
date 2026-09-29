import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from preflight_vnext_active_integration_candidate_v1 import identity
from audit_vnext_active_integration_product_lock_boundary_v1 import rollback

def load(name): return json.loads((ROOT/'docs/artifacts'/name).read_text(encoding='utf-8'))
def test_boundary_result_identity_and_terminal_state():
 v=load('vnext-active-integration-atomic-product-lock-boundary-v1.json')
 claimed=v.pop('boundary_identity');assert identity(v)==claimed
 assert v['status']=='PASS_CANDIDATE_NOT_ACTIVATED'
 assert v['active_state']['root_mutated'] is False
 assert v['active_state']['product_lock_replaced'] is False
 assert v['closure']['legacy_dependency_count']==0

def test_candidate_lock_is_content_addressed_and_inactive():
 v=load('vnext-active-integration-product-lock-candidate-v1.json')
 claimed=v.pop('product_lock_identity');assert identity(v)==claimed
 assert v['product_root']=='/root/pastila-vnext/v1'
 assert v['active_integration_state']=='CANDIDATE_NOT_ACTIVATED'
 assert v['activation']=={'prepared':True,'authorized':False,'atomic_product_lock_replacement':False}
 assert set(v['components'])=={'R2_REFERENCE','PYTHON_ML_PLATFORM'}
 assert v['legacy_dependency_count']==0

def test_atomic_rollback_restores_exact_bytes():
 old=b'old-product-lock\n';new=b'candidate-product-lock\n';r=rollback(old,new)
 assert r['status']=='PASS' and r['rollback_byte_exact'] is True
 assert r['old_lock_sha256']==hashlib.sha256(old).hexdigest()
 assert r['candidate_lock_sha256']==hashlib.sha256(new).hexdigest()

def test_scripts_do_not_claim_activation():
 for name in ('build_vnext_active_integration_product_lock_boundary_v1.py','preflight_vnext_active_integration_candidate_v1.py','accept_vnext_active_integration_candidate_v1.py','audit_vnext_active_integration_product_lock_boundary_v1.py'):
  text=(ROOT/'scripts'/name).read_text(encoding='utf-8')
  assert 'CANDIDATE_NOT_ACTIVATED' in text or name.startswith(('accept_','audit_'))
