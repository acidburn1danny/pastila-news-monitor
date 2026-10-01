import importlib.util, json
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
def mod(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def test_identities_and_exact_rollback_binding(tmp_path):
 b=mod(REPO/'scripts/build_vnext_canonical_rollback_consolidation_v1.py','b')
 result=b.build(REPO,Path('/root/pastila-vnext/v1'),Path('/root/pastila-vnext/.rollback-pre-exchange-5e31722e'),Path('/root/pastila-vnext/.rollback-pre-68fb2c347367'),tmp_path)
 assert result['status']=='PASS'
 manifest=json.loads((tmp_path/'vnext-canonical-rollback-manifest-v2.json').read_text())
 assert manifest['authority']['product_lock_identity']==b.ROLLBACK_LOCK_ID
 assert manifest['historical_root']['classification'].startswith('HISTORICAL_NON_CANONICAL')

def test_direct_predecessor_is_separate_from_activation_candidate(tmp_path):
 b=mod(REPO/'scripts/build_vnext_canonical_rollback_consolidation_v1.py','b2')
 b.build(REPO,Path('/root/pastila-vnext/v1'),Path('/root/pastila-vnext/.rollback-pre-exchange-5e31722e'),Path('/root/pastila-vnext/.rollback-pre-68fb2c347367'),tmp_path)
 lock=json.loads((tmp_path/'vnext-canonical-rollback-product-lock-successor-v1.json').read_text())
 assert lock['supersedes_product_lock_identity']==b.ACTIVE_LOCK_ID
 assert lock['activation_attestation']['activation_candidate_product_lock_identity']==b.ACTIVATION_CANDIDATE_ID
 assert b.ACTIVE_LOCK_ID!=b.ACTIVATION_CANDIDATE_ID

def test_active_and_both_rollback_roots_remain_bound():
 b=mod(REPO/'scripts/build_vnext_canonical_rollback_consolidation_v1.py','b3')
 assert b.sha(Path('/root/pastila-vnext/v1/product-lock.json'))==b.ACTIVE_LOCK_SHA
 assert b.sha(Path('/root/pastila-vnext/.rollback-pre-exchange-5e31722e/product-lock.json'))==b.ROLLBACK_LOCK_SHA
 assert b.sha(Path('/root/pastila-vnext/.rollback-pre-68fb2c347367/product-lock.json'))==b.HISTORICAL_LOCK_SHA


def test_preflight_pins_canonical_rollback_semantics(tmp_path):
 b=mod(REPO/'scripts/build_vnext_canonical_rollback_consolidation_v1.py','b4')
 import sys
 sys.path.insert(0,str(REPO/'scripts'))
 sys.modules['runtime_bytes_policy']=mod(REPO/'scripts/vnext_active_runtime_bytes_policy_v3.py','runtime_bytes_policy')
 pf=mod(REPO/'scripts/vnext_materialized_active_preflight_v10.py','pf')
 out=tmp_path/'out'; b.build(REPO,Path('/root/pastila-vnext/v1'),Path('/root/pastila-vnext/.rollback-pre-exchange-5e31722e'),Path('/root/pastila-vnext/.rollback-pre-68fb2c347367'),out)
 root=tmp_path/'root'; (root/'manifest/activation').mkdir(parents=True); (root/'manifest/authorities').mkdir(); (root/'manifest/rollback').mkdir()
 import shutil
 shutil.copy2('/root/pastila-vnext/v1/manifest/activation/vnext-activation-receipt-v1.json',root/'manifest/activation/vnext-activation-receipt-v1.json')
 shutil.copy2(out/'vnext-current-active-state-authority-v2.json',root/'manifest/authorities/vnext-active-product-lock-successor-v1.json')
 shutil.copy2(out/'vnext-canonical-rollback-manifest-v2.json',root/'manifest/rollback/vnext-canonical-rollback-manifest-v1.json')
 lock=json.loads((out/'vnext-canonical-rollback-product-lock-successor-v1.json').read_text())
 assert pf.verify_activation_authority(root,lock)=='V6_CANONICAL_ROLLBACK'
 rollback=json.loads((root/'manifest/rollback/vnext-canonical-rollback-manifest-v1.json').read_text()); rollback['rollback_root']='/tmp/not-authorized'; rollback.pop('rollback_manifest_identity'); rollback['rollback_manifest_identity']=b.identity(rollback)
 (root/'manifest/rollback/vnext-canonical-rollback-manifest-v1.json').write_text(json.dumps(rollback))
 authority=json.loads((root/'manifest/authorities/vnext-active-product-lock-successor-v1.json').read_text()); authority['canonical_rollback']['manifest_identity']=rollback['rollback_manifest_identity']; authority['canonical_rollback']['root']='/tmp/not-authorized'; authority.pop('active_state_authority_identity'); authority['active_state_authority_identity']=b.identity(authority); (root/'manifest/authorities/vnext-active-product-lock-successor-v1.json').write_text(json.dumps(authority))
 lock['activation_attestation']['canonical_rollback_manifest_identity']=rollback['rollback_manifest_identity']; lock['activation_attestation']['current_active_state_authority_identity']=authority['active_state_authority_identity']; lock.pop('product_lock_identity'); lock['product_lock_identity']=b.identity(lock)
 import pytest
 with pytest.raises(RuntimeError,match='canonical rollback target'):pf.verify_activation_authority(root,lock)
