import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];A=R/'docs/artifacts'
def mod():s=importlib.util.spec_from_file_location('b',R/'scripts/build_vnext_gui_coherent_rollback_promotion_v1.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def load(n):return json.loads((A/n).read_text())
def test_identities_and_complete_rollback_semantics():
 b=mod();spec={'vnext-gui-coherent-current-activation-receipt-v3.json':'activation_receipt_identity','vnext-gui-coherent-current-active-state-authority-v3.json':'active_state_authority_identity','vnext-gui-coherent-canonical-rollback-manifest-v6.json':'rollback_manifest_identity','vnext-gui-coherent-rollback-product-lock-v8.json':'product_lock_identity'};vals={}
 for n,k in spec.items():d=load(n);vals[n]=d;c=d.pop(k);assert c==b.ident(d);d[k]=c
 m=vals['vnext-gui-coherent-canonical-rollback-manifest-v6.json'];a=vals['vnext-gui-coherent-current-active-state-authority-v3.json'];r=vals['vnext-gui-coherent-current-activation-receipt-v3.json'];l=vals['vnext-gui-coherent-rollback-product-lock-v8.json']
 assert m['rollback_root']==a['canonical_rollback']['root']==b.ROOTS[0][0]
 assert [x['classification'] for x in m['historical_roots']]==[x[3] for x in b.ROOTS[1:]]
 assert len({x['path'] for x in m['historical_roots']})==5
 assert r['rollback']['manifest_identity']==m['rollback_manifest_identity']==l['activation_attestation']['canonical_rollback_manifest_identity']
 assert l['gui_authority']['state']=='ACTIVE' and l['rollback_authority_successor_of_product_lock_identity']==b.ACTIVE_ID
def test_prospective_three_phase_closure_and_preservation():
 r=load('vnext-gui-coherent-rollback-promotion-result-v1.json');assert r['status']=='PASS' and r['blockers']==0
 assert [r[k]['terminal'] for k in ('prospective_install','prospective_rollback','prospective_restore')]==['EXPORTED']*3
 assert [r[k]['startup'] for k in ('prospective_install','prospective_rollback','prospective_restore')]==['PASS_STARTUP_READY']*3
 assert not r['active_root_modified'] and not r['rollback_roots_modified'] and not r['retirement_executed']
 assert r['protected_root_identity_preservation']=='PASS' and r['cli_gui_parity']=='PASS_SHARED_ORCHESTRATOR_AND_STATE' and r['canonical_startup_paths']==1
 assert r['voice']=='DISABLED_UNTIL_PROMOTION' and r['legacy_dependency_count']==0
