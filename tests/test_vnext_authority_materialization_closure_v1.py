import hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'docs'/'artifacts'
def ident(d, field):
    x=dict(d); x.pop(field,None)
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def test_product_lock_successor_semantics():
    d=json.loads((ART/'vnext-materialized-active-product-lock-successor-v1.json').read_text())
    assert d['status']=='ACTIVE' and d['active_integration_state']=='ACTIVATED'
    assert d['activation']['authorized'] is True
    assert d['legacy_dependency_count']==0
    assert d['managed_inventory_semantics']=='EXHAUSTIVE_REJECT_EXTRA_EXCEPT_DECLARED_RUNTIME_CACHE'
    assert ident(d,'product_lock_identity')==d['product_lock_identity']=='91927b608b7115e410fc8873dcf23ad851a4530a6cc68b4405dd99a94abce5db'
def test_dependency_graph_is_acyclic_and_materialized():
    d=json.loads((ART/'vnext-materialized-active-dependency-graph-v3.json').read_text())
    nodes={n['id']:n for n in d['nodes']}; seen=set(); active=set()
    def visit(k):
        assert k not in active
        if k in seen:return
        active.add(k)
        for dep in nodes[k].get('depends_on',[]): assert dep in nodes; visit(dep)
        active.remove(k);seen.add(k)
    for k in nodes:visit(k)
    assert {'active_state_authority','activation_receipt','rollback_authority','active_audit_authority','active_auditor'} <= set(nodes)
    assert d['authority_identity']=='4eb947f5c881a21f37e6424407e20b47bfaefe69a653ab8e1e4d48f44cb8b49a'
def test_standalone_auditor_has_no_repository_import():
    text=(ROOT/'scripts'/'audit_vnext_materialized_active_product_v1.py').read_text()
    assert 'sys.path' not in text and 'from pastila_scout' not in text and 'import pastila_scout' not in text
    assert "repository_dependency_count':0" in text
