import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];A=R/'docs/artifacts'
def ident(d,k):x=dict(d);x.pop(k,None);return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def test_active_lock_and_graph():
 l=json.loads((A/'vnext-materialized-active-product-lock-successor-v2.json').read_text());g=json.loads((A/'vnext-materialized-active-dependency-graph-v3-startup-repair.json').read_text());assert l['status']=='ACTIVE' and l['active_integration_state']=='ACTIVATED' and l['schema_version']==4;assert ident(l,'product_lock_identity')==l['product_lock_identity']=='63c547f5d5bb794a9a6d5b7aea3c71fd10dc418063494267ea3fbd03e8399646';assert ident(g,'authority_identity')==g['authority_identity']==l['active_graph_identity']=='dcac0c59b8ebacc492e8c053e00894b03dd654d569617b325e78073e67a8239f'
def test_single_canonical_startup():
 p=(R/'scripts/vnext_materialized_active_preflight_v1.py').read_text();a=(R/'scripts/vnext_materialized_active_acceptance_v1.py').read_text();assert 'CANDIDATE_NOT_ACTIVATED' not in p and '"ACTIVATED"' in p;assert 'from product import startup' in a and 'startup_result=startup(root)' in a
def test_auditor_runs_startup_and_e2e():
 s=(R/'scripts/audit_vnext_materialized_active_product_v2.py').read_text();assert "app/cli/product.py" in s and "app/cli/acceptance.py" in s and 'e2e startup bypass' in s
def test_fault_matrix_is_complete():
 s=(R/'scripts/test_vnext_materialized_active_startup_faults_v1.py').read_text();assert all(x in s for x in ('LOCK_STATE','LOCK_IDENTITY','GRAPH_IDENTITY','GRAPH_LOCK_BINDING','MANAGED_DRIFT','MISSING_MANAGED','EXTRA_MANAGED','AUDITOR_INCOMPATIBLE','E2E_NO_BYPASS'))