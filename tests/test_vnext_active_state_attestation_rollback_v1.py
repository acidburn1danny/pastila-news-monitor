import importlib.util, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
B=mod('builder','scripts/build_vnext_active_state_attestation_rollback_v1.py')
A=mod('auditor','scripts/audit_vnext_active_state_attestation_rollback_v1.py')
def artifact(name):return json.loads((ROOT/'docs/artifacts'/name).read_text(encoding='utf-8'))
def valid(v,key):return v[key]==B.identity({k:x for k,x in v.items() if k!=key})

def test_successor_identity(): assert valid(artifact('vnext-active-product-lock-successor-v1.json'),'product_lock_identity')
def test_receipt_identity(): assert valid(artifact('vnext-activation-receipt-v1.json'),'activation_receipt_identity')
def test_rollback_manifest_identity(): assert valid(artifact('vnext-canonical-rollback-manifest-v1.json'),'rollback_manifest_identity')
def test_successor_is_activated():
 d=artifact('vnext-active-product-lock-successor-v1.json');assert d['status']=='ACTIVE' and d['active_integration_state']=='ACTIVATED' and d['activation']['authorized'] and d['activation']['product_lock_replacement']
def test_candidate_is_immutable_binding():
 d=artifact('vnext-active-product-lock-successor-v1.json');assert d['installed_candidate_product_lock']=={'identity':B.CANDIDATE_LOCK_ID,'sha256':B.CANDIDATE_LOCK_SHA}
def test_receipt_cross_bindings():
 l=artifact('vnext-active-product-lock-successor-v1.json');r=artifact('vnext-activation-receipt-v1.json');m=artifact('vnext-canonical-rollback-manifest-v1.json');assert r['active']['successor_product_lock_identity']==l['product_lock_identity'];assert r['rollback_manifest_identity']==m['rollback_manifest_identity']
def test_rollback_manifest_separates_cache_and_history():
 d=artifact('vnext-canonical-rollback-manifest-v1.json');assert '**/*.pyc' in d['regenerable_runtime_bytes']['rules'];assert set(d['excluded_non_authoritative_paths'])=={'components/voice-candidates-v1','reviews','runs'};assert d['pre_activation_raw_tree_claim']['status']=='UNRECONCILED_NON_AUTHORITATIVE'
def test_fault_injection_all_windows():
 f,r=A.atomic_proof();assert r=='PASS_RESTORE_AND_CONTROLLED_RETURN';assert [x['failpoint'] for x in f]==['BEFORE_BACKUP','AFTER_BACKUP','AFTER_ACTIVATE'];assert all(x['status']=='PASS_BYTE_EXACT_RECOVERY' for x in f)
def test_identity_tamper_is_detected():
 d=artifact('vnext-activation-receipt-v1.json');d['status']='ALTERED';assert not valid(d,'activation_receipt_identity')
def test_result_is_reproducible_and_pass():
 d=artifact('vnext-active-state-attestation-rollback-proof-result-v1.json');assert valid(d,'result_identity');assert d['status']=='PASS' and d['blockers']==0 and d['legacy_dependency_count']==0 and d['live']['terminal']=='EXPORTED'
