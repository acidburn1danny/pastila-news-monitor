import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('p',R/'scripts/vnext_active_runtime_bytes_policy_v1.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P)
def test_classification_matrix_17():
 cases=[('app/cli/__pycache__/valid.pyc',P.ALLOWED_REGENERABLE_RUNTIME),('app/cli/a.pyc',P.ALLOWED_REGENERABLE_RUNTIME),('state/product.sqlite3-wal',P.ALLOWED_REGENERABLE_RUNTIME),('state/product.sqlite3-shm',P.ALLOWED_REGENERABLE_RUNTIME),('state/product.sqlite3',P.MUTABLE_STATE),('app/cli/a.py',P.MANAGED),('components/editor-r2/x',P.MANAGED),('platform/python-ml/x',P.MANAGED),('evil.pyc',P.FORBIDDEN),('app/cli/__pycache__/evil.bin',P.FORBIDDEN),('extra.bin',P.FORBIDDEN),('../x',P.FORBIDDEN),('/abs',P.FORBIDDEN),('app/../x',P.FORBIDDEN),('app/x',P.FORBIDDEN,True)]
 assert all(P.classify(c[0],c[2] if len(c)>2 else False)==c[1] for c in cases)
 lock=json.loads((R/'docs/artifacts/vnext-active-runtime-cache-policy-product-lock-v1.json').read_text());assert tuple(lock['runtime_cache_policy']['allowed'])==P.DECLARED_ALLOWED
 for f in ('scripts/build_vnext_active_runtime_cache_policy_repair_v1.py','scripts/vnext_materialized_active_preflight_v2.py','scripts/audit_vnext_materialized_active_product_v3.py'):assert 'runtime_bytes_policy' in (R/f).read_text()
def test_authority_identity_stable_with_cache_policy():
 d=json.loads((R/'docs/artifacts/vnext-active-runtime-cache-policy-product-lock-v1.json').read_text());assert d['product_lock_identity']=='b8fe4dd7c7d1e9482388a7435e4655b9c9ef0436adaf1d224befac0530949514';assert all('__pycache__' not in x['path'] and not x['path'].endswith('.pyc') for x in d['application_files'])
def test_single_policy_no_parallel_copy():
 assert P.DECLARED_ALLOWED==('**/__pycache__/**','**/*.pyc','state/*.sqlite3-wal','state/*.sqlite3-shm')