import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];A=R/'docs/artifacts'
def ident(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def test_result_identity():
 x=json.loads((A/'vnext-component-namespace-integrity-repair-result-v1.json').read_text());i=x.pop('result_identity');assert i==ident(x);assert x['namespace_faults_passed']==x['namespace_faults_total']==4
def test_preflight_exhaustive_namespace_types():
 x=(R/'scripts/vnext_materialized_active_preflight_v4.py').read_text();assert 'component_entries=list' in x;assert 'platform_entries=list' in x;assert x.count('is_symlink()')>=2
def test_auditor_exhaustive_namespace_types():
 x=(R/'scripts/audit_vnext_materialized_active_product_v6.py').read_text();assert 'component namespace mismatch' in x;assert 'platform namespace mismatch' in x
def test_builder_binds_successors():
 x=(R/'scripts/build_vnext_component_namespace_integrity_repair_v1.py').read_text();assert 'preflight_v4.py' in x;assert 'product_v6.py' in x
