import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];A=R/'docs/artifacts'
def mod():s=importlib.util.spec_from_file_location('b',R/'scripts/build_vnext_redundant_historical_rollback_refs_retirement_v1.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def load(n):return json.loads((A/n).read_text())
def test_identities_and_complete_rollback_semantics():
 b=mod();spec={'vnext-retirement-ready-current-activation-receipt-v4.json':'activation_receipt_identity','vnext-retirement-ready-current-active-state-authority-v4.json':'active_state_authority_identity','vnext-retirement-ready-canonical-rollback-manifest-v7.json':'rollback_manifest_identity','vnext-retirement-ready-product-lock-v8.json':'product_lock_identity'};vals={}
 for n,k in spec.items():d=load(n);vals[n]=d;c=d.pop(k);assert c==b.ident(d);d[k]=c
 m=vals['vnext-retirement-ready-canonical-rollback-manifest-v7.json'];a=vals['vnext-retirement-ready-current-active-state-authority-v4.json'];r=vals['vnext-retirement-ready-current-activation-receipt-v4.json'];l=vals['vnext-retirement-ready-product-lock-v8.json']
 assert m['rollback_root']==a['canonical_rollback']['root']==b.ROOTS[0][0]
 assert [x['classification'] for x in m['historical_roots']]==[b.ROOTS[i][3] for i in (2,3,5)]
 assert len({x['path'] for x in m['historical_roots']})==3
 assert [x['path'] for x in m['historical_roots']]==[b.ROOTS[i][0] for i in (2,3,5)]
 blob='\n'.join(json.dumps(x,sort_keys=True) for x in (m,a,r,l));assert b.ROOTS[1][0] not in blob and b.ROOTS[4][0] not in blob
 assert l['redundant_historical_root_retirement_readiness']['authority_references']==0
 assert r['rollback']['manifest_identity']==m['rollback_manifest_identity']==l['activation_attestation']['canonical_rollback_manifest_identity']
 assert l['gui_authority']['state']=='ACTIVE' and l['rollback_authority_successor_of_product_lock_identity']==b.ACTIVE_ID
def test_prospective_three_phase_closure_and_preservation():
 r=load('vnext-redundant-historical-rollback-refs-retirement-result-v1.json');assert r['status']=='PASS' and r['blockers']==0
 assert [r[k]['terminal'] for k in ('prospective_install','prospective_rollback','prospective_restore')]==['EXPORTED']*3
 assert [r[k]['startup'] for k in ('prospective_install','prospective_rollback','prospective_restore')]==['PASS_STARTUP_READY']*3
 assert not r['active_root_modified'] and not r['rollback_roots_modified'] and not r['retirement_executed']
 assert r['protected_root_identity_preservation']=='PASS' and r['cli_gui_parity']=='PASS_SHARED_ORCHESTRATOR_AND_STATE' and r['canonical_startup_paths']==1
 assert r['voice']=='DISABLED_UNTIL_PROMOTION' and r['legacy_dependency_count']==0
