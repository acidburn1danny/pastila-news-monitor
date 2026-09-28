"""Audit VNext Core Workflow to Deterministic FINAL Vertical Slice v1."""
from __future__ import annotations
import ast,json
from pathlib import Path
from pastila_scout.vnext_foundation_v1 import object_identity, scan_legacy_dependencies
from pastila_scout.vnext_state_sqlite_v1 import MIGRATION_6,SCHEMA_VERSION
from pastila_scout.vnext_workflow_v1 import STATES,TRANSITIONS
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs/artifacts'
def load(name): return json.loads((ART/name).read_text(encoding='utf-8'))
def ident(v,key): assert v[key]==object_identity({k:x for k,x in v.items() if k!=key})
def main():
 workflow=load('vnext-active-product-workflow-state-contract-v3.json'); sqlite=load('vnext-consolidated-operational-state-sqlite-boundary-v6-contract.json'); manifest=load('vnext-active-authority-audit-manifest-v1.json'); closure=load('vnext-core-workflow-deterministic-final-v1.json')
 for v,k in ((workflow,'authority_identity'),(sqlite,'authority_identity'),(manifest,'manifest_identity'),(closure,'closure_identity')): ident(v,k)
 assert set(map(tuple,workflow['transitions']))==set(TRANSITIONS) and set(workflow['states'])==set(STATES)
 assert SCHEMA_VERSION==6 and any('CREATE TABLE policy_sessions' in x for x in MIGRATION_6)
 assert manifest['active_authorities']['sqlite']['identity']==sqlite['authority_identity'] and closure['authority_bindings']['active_manifest_identity']==manifest['manifest_identity']
 modules=set(manifest['active_runtime_modules']); assert 'src/pastila_scout/vnext_core_final_v1.py' in modules
 discovered=set()
 for rel in modules:
  tree=ast.parse((ROOT/rel).read_text(encoding='utf-8'))
  for node in ast.walk(tree):
   if isinstance(node,ast.ImportFrom) and node.level==1 and node.module and node.module.startswith('vnext_'):
    candidate=f'src/pastila_scout/{node.module}.py'
    if (ROOT/candidate).exists(): discovered.add(candidate)
 assert discovered<=modules,sorted(discovered-modules)
 core=(ROOT/'src/pastila_scout/vnext_core_final_v1.py').read_text(encoding='utf-8')
 for marker in ('policy_sessions','APPROVED_FOR_FINAL','DETERMINISTIC_PASSTHROUGH_V1','VOICE_DISABLED','EXPORTED'): assert marker in core
 inv=closure['invariants']; assert not inv['active_integration'] and not inv['product_lock_replaced'] and inv['legacy_dependency_count']==0 and inv['voice']=='DISABLED_UNTIL_PROMOTION' and inv['stop_all_candidates']
 findings=scan_legacy_dependencies(ROOT/'src/pastila_scout'); names={Path(x).name for x in modules}; assert [x for x in findings if x['path'] in names]==[]
 print(json.dumps({'status':'PASS','schema_version':6,'workflow_identity':workflow['authority_identity'],'sqlite_identity':sqlite['authority_identity'],'manifest_identity':manifest['manifest_identity'],'closure_identity':closure['closure_identity'],'active_modules':len(modules),'transitive_imports':len(discovered),'legacy_dependency_count':0},sort_keys=True))
if __name__=='__main__': main()
