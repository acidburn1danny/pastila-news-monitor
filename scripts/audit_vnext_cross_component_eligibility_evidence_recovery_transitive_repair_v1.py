"""Current-head audit for eligibility, evidence, recovery and transitive closure repair."""
from __future__ import annotations
import ast, hashlib, json
from pathlib import Path
from pastila_scout.vnext_foundation_v1 import object_identity, scan_legacy_dependencies
from pastila_scout.vnext_state_sqlite_v1 import MIGRATION_5, SCHEMA_VERSION
from pastila_scout.vnext_workflow_v1 import STATES, TRANSITIONS
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs/artifacts'

def load(name): return json.loads((ART/name).read_text(encoding='utf-8'))
def ident(v,key): assert v[key]==object_identity({k:x for k,x in v.items() if k!=key})
def main():
    workflow=load('vnext-active-product-workflow-state-contract-v3.json')
    sqlite=load('vnext-consolidated-operational-state-sqlite-boundary-v5-contract.json')
    manifest=load('vnext-active-authority-audit-manifest-v1.json')
    closure=load('vnext-cross-component-eligibility-evidence-recovery-transitive-repair-v1.json')
    for value,key in ((workflow,'authority_identity'),(sqlite,'authority_identity'),(manifest,'manifest_identity'),(closure,'closure_identity')): ident(value,key)
    assert set(map(tuple,workflow['transitions']))==set(TRANSITIONS) and set(workflow['states'])==set(STATES)
    assert SCHEMA_VERSION==5 and any('request_identity' in row for row in MIGRATION_5)
    assert manifest['active_authorities']['sqlite']['identity']==sqlite['authority_identity']
    assert closure['authority_bindings']['active_manifest_identity']==manifest['manifest_identity']
    modules=set(manifest['active_runtime_modules'])
    assert 'src/pastila_scout/vnext_r2_consolidation_binding_v1.py' in modules
    discovered=set()
    for relative in tuple(modules):
        tree=ast.parse((ROOT/relative).read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom) and node.level==1 and node.module and node.module.startswith('vnext_'):
                candidate=f'src/pastila_scout/{node.module}.py'
                if (ROOT/candidate).exists(): discovered.add(candidate)
    assert discovered <= modules, sorted(discovered-modules)
    editor=(ROOT/'src/pastila_scout/vnext_editor_vertical_slice_v1.py').read_text()
    factual=(ROOT/'src/pastila_scout/vnext_factual_acceptance_v1.py').read_text()
    scout=(ROOT/'src/pastila_scout/vnext_scout_production_v1.py').read_text()
    assert 'parsed_text_sha256' in editor and 'registered SourcePacket payload mismatch' in factual
    assert 'request_identity' in factual and 'replayed factual evidence mismatch' in factual
    assert 'SOURCE_PACKET_INVALID' in scout
    inv=closure['invariants']; assert inv['legacy_dependency_count']==0 and not inv['active_integration'] and not inv['product_lock_replaced']
    findings=scan_legacy_dependencies(ROOT/'src/pastila_scout')
    names={Path(x).name for x in modules}; relevant=[x for x in findings if x['path'] in names]
    assert relevant==[]
    print(json.dumps({'status':'PASS','schema_version':5,'workflow_identity':workflow['authority_identity'],'sqlite_identity':sqlite['authority_identity'],'manifest_identity':manifest['manifest_identity'],'closure_identity':closure['closure_identity'],'active_modules':len(modules),'transitive_imports':len(discovered),'legacy_dependency_count':0},sort_keys=True))
if __name__=='__main__': main()
