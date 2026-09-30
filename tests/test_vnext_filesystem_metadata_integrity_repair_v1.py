import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];A=R/'docs/artifacts'
def ident(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def test_result_identity():
 x=json.loads((A/'vnext-filesystem-metadata-integrity-repair-result-v1.json').read_text());i=x.pop('result_identity');assert i==ident(x);assert x['metadata_faults_passed']==x['metadata_faults_total']==16
def test_preflight_rejects_owner_and_permission_drift():
 x=(R/'scripts/vnext_materialized_active_preflight_v8.py').read_text();assert 'product filesystem owner mismatch' in x;assert 'product filesystem permissions mismatch' in x
def test_auditor_independently_rejects_metadata_drift():
 x=(R/'scripts/audit_vnext_materialized_active_product_v10.py').read_text();assert 'product filesystem owner mismatch' in x;assert 'product filesystem permissions mismatch' in x
def test_builder_normalizes_and_binds_successors():
 x=(R/'scripts/build_vnext_filesystem_metadata_integrity_repair_v1.py').read_text();assert 'p.stat().st_mode & ~0o022' in x;assert 'preflight_v8.py' in x;assert 'product_v10.py' in x
