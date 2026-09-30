import hashlib,importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];A=R/'docs/artifacts'
def load(n):return json.loads((A/n).read_text())
def ident(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def test_result_and_authority_identities():
 x=load('vnext-startup-trust-bootstrap-repair-result-v1.json');i=x.pop('result_identity');assert i==ident(x);assert x['status']=='PASS';assert x['dedicated_adversarial']=={'passed':8,'total':8}
 l=load('vnext-startup-trust-bootstrap-product-lock-v1.json');i=l.pop('product_lock_identity');assert i==ident(l)
 g=load('vnext-startup-trust-bootstrap-graph-v1.json');i=g.pop('authority_identity');assert i==ident(g)
def test_policy_forbids_all_executable_cache_forms():
 s=importlib.util.spec_from_file_location('p',R/'scripts/vnext_active_runtime_bytes_policy_v3.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p)
 for x in ('app/cli/x.pyc','app/cli/__pycache__/x.cpython-312.pyc','app/workflow/pastila_scout/x.pyc'):assert p.classify(x)==p.FORBIDDEN
 assert p.classify('state/product.sqlite3-wal')==p.ALLOWED_REGENERABLE_RUNTIME
def test_bootstrap_precedes_product_imports():
 t=(R/'scripts/vnext_materialized_active_product_bootstrap_v1.py').read_text()
 assert t.index('sys.path.pop(0)')<t.index('import argparse')
 assert 'bootstrap managed inventory mismatch' in t and 'from preflight import verify' in t
def test_consumers_use_successor_policy_and_isolated_startup():
 b=(R/'scripts/build_vnext_startup_trust_bootstrap_repair_v1.py').read_text();a=(R/'scripts/audit_vnext_materialized_active_product_v5.py').read_text()
 assert 'vnext_active_runtime_bytes_policy_v3.py' in b and 'vnext_materialized_active_product_bootstrap_v1.py' in b
 assert "'-I','-B'" in a and 'R2 exhaustive inventory' in a and 'unknown component directory' in a
