import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];A=R/'docs/artifacts'
def ident(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def test_result_identity():
 x=json.loads((A/'vnext-platform-ownership-integrity-repair-result-v1.json').read_text());i=x.pop('result_identity');assert i==ident(x);assert x['platform_hardlink_preflight']==x['platform_hardlink_auditor']=='FAIL_CLOSED'
def test_preflight_rejects_shared_regular_platform_files():
 x=(R/'scripts/vnext_materialized_active_preflight_v5.py').read_text();assert 'not x.is_symlink() and x.is_file() and x.stat().st_nlink!=1' in x
def test_auditor_independently_rejects_shared_regular_platform_files():
 x=(R/'scripts/audit_vnext_materialized_active_product_v7.py').read_text();assert 'not x.is_symlink() and x.is_file() and x.stat().st_nlink!=1' in x
def test_builder_binds_successors():
 x=(R/'scripts/build_vnext_platform_ownership_integrity_repair_v1.py').read_text();assert 'preflight_v5.py' in x;assert 'product_v7.py' in x
