import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];A=R/'docs/artifacts'
def ident(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def test_result_identity():
 x=json.loads((A/'vnext-filesystem-entry-type-integrity-repair-result-v1.json').read_text());i=x.pop('result_identity');assert i==ident(x);assert x['entry_type_faults_passed']==x['entry_type_faults_total']==8
def test_preflight_rejects_unsupported_filesystem_entry_types():
 x=(R/'scripts/vnext_materialized_active_preflight_v7.py').read_text();assert 'product filesystem entry type mismatch' in x;assert 'p.is_symlink() or p.is_dir() or p.is_file()' in x
def test_auditor_independently_rejects_unsupported_entry_types():
 x=(R/'scripts/audit_vnext_materialized_active_product_v9.py').read_text();assert 'product filesystem entry type mismatch' in x
def test_builder_binds_successors():
 x=(R/'scripts/build_vnext_filesystem_entry_type_integrity_repair_v1.py').read_text();assert 'preflight_v7.py' in x;assert 'product_v9.py' in x;assert '7305b1d83ff94dd0a512b5f85558050710a27c87' in x
