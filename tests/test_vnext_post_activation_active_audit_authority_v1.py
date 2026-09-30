import importlib.util,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def mod(name,path):s=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
B=mod('builder','scripts/build_vnext_post_activation_active_audit_authority_v1.py')
def load(n):return json.loads((ROOT/'docs/artifacts'/n).read_text())
def ident(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
M=lambda:load('vnext-post-activation-active-audit-authority-v1.json')
def test_manifest_identity():d=M();assert d['manifest_identity']==ident({k:v for k,v in d.items() if k!='manifest_identity'})
def test_exactly_one_current_auditor():d=M();assert d['current_auditor_count']==1 and d['exclusive_current_auditor'] and d['current_auditor']==B.CURRENT_AUDITOR
def test_predecessor_is_historical_commit_only():
 d=M();rows=[x for x in d['historical_commit_only_auditors'] if x['path']==B.PREDECESSOR_AUDITOR];assert len(rows)==1 and rows[0]['commit']==B.PREDECESSOR_COMMIT and rows[0]['reason']=='PRE_ACTIVATION_PRODUCT_LOCK_ASSERTION'
def test_predecessor_evidence_unchanged():
 d=M();assert d['historical_evidence_mutated'] is False;assert d['supersedes']['manifest_identity']==B.PREDECESSOR_ID;assert B.sha(ROOT/B.PREDECESSOR_AUDITOR)==[x for x in d['historical_commit_only_auditors'] if x['path']==B.PREDECESSOR_AUDITOR][0]['sha256']
def test_historical_test_classified_and_replaced():
 d=M();t=d['historical_tests'][0];assert t['path']==B.HISTORICAL_TEST and t['classification']=='PRE_ACTIVATION_COMMIT_ONLY' and t['active_coverage_replacement']==B.CURRENT_AUDITOR
def test_active_bindings_exact():
 assert M()['active_bindings']=={'active_product_lock_sha256':B.LOCK_SHA,'active_state_authority_identity':B.ACTIVE_STATE_ID,'activation_receipt_identity':B.RECEIPT_ID,'rollback_manifest_identity':B.ROLLBACK_ID}
def test_pre_activation_coverage_is_complete_snapshot():
 d=M();p=load('vnext-active-authority-audit-manifest-v1.json');s=d['coverage']['pre_activation_invariant_snapshot'];assert s['keys']==sorted(p['invariants']) and s['identity']==ident(p['invariants'])
def test_post_activation_coverage_has_all_gates():
 r=set(M()['coverage']['post_activation_required_checks']);assert {'ACTIVE_PRODUCT_LOCK','ACTIVE_STATE_AUTHORITY','ACTIVATION_RECEIPT','CANONICAL_ROLLBACK_MANIFEST','ACTIVE_ROOT_MANAGED_BYTES','ACTIVE_DEPENDENCY_GRAPH','R2_BYTES','PLATFORM_TREE','SQLITE_INTEGRITY','STARTUP','INTEGRATED_E2E_EXPORTED','ROLLBACK_RESTORE_FAULT_INJECTION','LEGACY_DEPENDENCY_COUNT_ZERO'}==r
def test_result_identity_and_pass():
 d=load('vnext-post-activation-active-audit-authority-result-v1.json');assert d['result_identity']==ident({k:v for k,v in d.items() if k!='result_identity'});assert d['status']=='PASS' and d['blockers']==0 and d['current_auditor_count']==1 and d['post_activation_coverage']=='COMPLETE'
def test_no_legacy_and_no_root_mutation():
 d=load('vnext-post-activation-active-audit-authority-result-v1.json');assert d['legacy_dependency_count']==0 and not d['active_root_mutated'] and not d['rollback_root_mutated']
