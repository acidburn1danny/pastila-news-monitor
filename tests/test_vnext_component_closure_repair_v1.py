import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];A=R/'docs/artifacts'
def load(n):return json.loads((A/n).read_text())
def test_component_authority_exact():
 l=load('vnext-component-closure-product-lock-v1.json');assert set(l['components'])=={'R2_REFERENCE','PYTHON_ML_PLATFORM'};assert l['components']['R2_REFERENCE']['verification']=='EXHAUSTIVE_LOCK_SET_EQUALITY';assert l['components']['PYTHON_ML_PLATFORM']['verification']=='FULL_TREE_IDENTITY'
def test_graph_lock_component_binding():
 l=load('vnext-component-closure-product-lock-v1.json');g=load('vnext-component-closure-graph-v1.json');t={x['id']:x['target_path'] for x in g['nodes']};assert t['r2']==l['components']['R2_REFERENCE']['path']=='components/editor-r2';assert t['python_ml']==l['components']['PYTHON_ML_PLATFORM']['path']=='platform/python-ml'
def test_policy_rejects_unknown_components_and_aliases():
 s=importlib.util.spec_from_file_location('p',R/'scripts/vnext_active_runtime_bytes_policy_v2.py');p=importlib.util.module_from_spec(s);s.loader.exec_module(p);assert p.classify('components/editor-r2/x')==p.MANAGED;assert p.classify('platform/python-ml/x')==p.MANAGED;assert all(p.classify(x)==p.FORBIDDEN for x in ('components/rogue/x','components/editor-r20/x','components/Editor-R2/x','components/../editor-r2/x','/components/editor-r2/x'))
def test_all_consumers_share_policy():
 for f in ('scripts/build_vnext_component_closure_repair_v1.py','scripts/vnext_materialized_active_preflight_v3.py','scripts/audit_vnext_materialized_active_product_v4.py'):assert 'runtime_bytes_policy' in (R/f).read_text()