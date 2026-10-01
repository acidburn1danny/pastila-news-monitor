import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];A=R/'docs/artifacts'
def mod():s=importlib.util.spec_from_file_location('b',R/'scripts/build_vnext_gui_attestation_rollback_promotion_v1.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def load(n):return json.loads((A/n).read_text())
def test_identities_and_rollback_semantics():
 b=mod();spec={'vnext-gui-current-activation-receipt-v2.json':'activation_receipt_identity','vnext-gui-current-active-state-authority-v2.json':'active_state_authority_identity','vnext-gui-attestation-canonical-rollback-manifest-v5.json':'rollback_manifest_identity','vnext-gui-attestation-rollback-product-lock-v8.json':'product_lock_identity'};vals={}
 for n,k in spec.items():d=load(n);vals[n]=d;c=d.pop(k);assert c==b.ident(d);d[k]=c
 m=vals['vnext-gui-attestation-canonical-rollback-manifest-v5.json'];a=vals['vnext-gui-current-active-state-authority-v2.json'];r=vals['vnext-gui-current-activation-receipt-v2.json'];l=vals['vnext-gui-attestation-rollback-product-lock-v8.json']
 assert m['rollback_root']==a['canonical_rollback']['root']==b.IMMEDIATE_ROOT
 assert [x['classification'] for x in m['historical_roots']]==['HISTORICAL_NON_CANONICAL','HISTORICAL_NON_CANONICAL_PENDING_RETIREMENT']
 assert r['rollback']['manifest_identity']==m['rollback_manifest_identity']
 assert l['activation_attestation']['canonical_rollback_manifest_identity']==m['rollback_manifest_identity']
 assert l['supersedes_product_lock_identity']=='4d45f169ed4f6eba530e181a7e61ce4ade02d63e8d21f5177b3d4d18d15a0738'
 assert l['rollback_authority_successor_of_product_lock_identity']==b.ACTIVE_ID
def test_prospective_three_phase_closure():
 r=load('vnext-gui-attestation-rollback-promotion-result-v1.json');assert r['status']=='PASS' and r['blockers']==0
 assert [r[k]['terminal'] for k in ('prospective_install','prospective_rollback','prospective_restore')]==['EXPORTED']*3
 assert [r[k]['startup'] for k in ('prospective_install','prospective_rollback','prospective_restore')]==['PASS_STARTUP_READY']*3
 assert not r['active_root_modified'] and not r['rollback_roots_modified'] and not r['retirement_executed']
 assert r['voice']=='DISABLED_UNTIL_PROMOTION' and r['legacy_dependency_count']==0
