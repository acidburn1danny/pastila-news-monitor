import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];A=R/'docs/artifacts'
def ident(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def test_result_identity():
 x=json.loads((A/'vnext-product-file-ownership-integrity-repair-result-v1.json').read_text());i=x.pop('result_identity');assert i==ident(x);assert x['ownership_faults_passed']==x['ownership_faults_total']==8
def test_preflight_rejects_every_shared_regular_product_file():
 x=(R/'scripts/vnext_materialized_active_preflight_v6.py').read_text();assert 'for p in root.rglob("*")' in x;assert 'product file ownership mismatch' in x
def test_auditor_independently_rejects_every_shared_regular_product_file():
 x=(R/'scripts/audit_vnext_materialized_active_product_v8.py').read_text();assert 'for p in root.rglob("*")' in x;assert 'product file ownership mismatch' in x
def test_builder_binds_successors():
 x=(R/'scripts/build_vnext_product_file_ownership_integrity_repair_v1.py').read_text();assert 'preflight_v6.py' in x;assert 'product_v8.py' in x;assert '3c0a17a8c23fd4b7c24c983a016a7ca1d03024d0' in x
