#!/usr/bin/env python3
import argparse,hashlib,importlib.util,json,os,shutil,subprocess
from pathlib import Path
BASE='7305b1d83ff94dd0a512b5f85558050710a27c87';RUNTIME='c211a07551284627a8e23c6e84d7dbf7e1125681'
def canon(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def ident(v):return hashlib.sha256(canon(v)).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(8*1024*1024),b''):h.update(c)
 return h.hexdigest()
def write(p,v,key):v[key]=ident(v);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,ensure_ascii=False,sort_keys=True)+'\n')
def build(repo,source,target):
 if target.exists():raise RuntimeError('target exists')
 subprocess.run(['cp','-a',str(source),str(target)],check=True)
 for p in list(target.rglob('__pycache__')):shutil.rmtree(p)
 for p in list(target.rglob('*.pyc')):p.unlink()
 old=target/'manifest/authorities/vnext-active-authority-audit-manifest-v1.json';hist=target/'manifest/history/vnext-active-authority-audit-manifest-v1.json';hist.parent.mkdir(parents=True);shutil.move(old,hist)
 copies=[('docs/artifacts/vnext-active-product-lock-successor-v1.json','manifest/authorities/vnext-active-product-lock-successor-v1.json'),('docs/artifacts/vnext-activation-receipt-v1.json','manifest/activation/vnext-activation-receipt-v1.json'),('docs/artifacts/vnext-canonical-rollback-manifest-v1.json','manifest/rollback/vnext-canonical-rollback-manifest-v1.json'),('docs/artifacts/vnext-post-activation-active-audit-authority-v1.json','manifest/authorities/vnext-post-activation-active-audit-authority-v1.json'),('scripts/audit_vnext_materialized_active_product_v9.py','app/cli/audit.py'),('scripts/vnext_materialized_active_preflight_v7.py','app/cli/preflight.py'),('scripts/vnext_materialized_active_acceptance_v2.py','app/cli/acceptance.py'),('scripts/vnext_active_runtime_bytes_policy_v3.py','app/cli/runtime_bytes_policy.py'),('scripts/vnext_materialized_active_product_bootstrap_v1.py','app/cli/product.py')]
 for a,b in copies:
  q=target/b;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(repo/a,q)
 graph_path=target/'manifest/authorities/vnext-active-product-dependency-graph-v2.json';g=json.loads(graph_path.read_text());g['schema']='vnext-active-product-dependency-graph-v3';g['schema_version']=3;g['bound_commit']=BASE;g['status']='ACTIVE_SELF_CONTAINED_AUTHORITY_CLOSURE';g['supersedes']=g.pop('authority_identity');g['nodes']=[n for n in g['nodes'] if n['id'] not in {'active_audit','activation_authority'}]+[
 {'id':'active_state_authority','target_path':'manifest/authorities/vnext-active-product-lock-successor-v1.json','depends_on':['activation_receipt','rollback_authority']},
 {'id':'activation_receipt','target_path':'manifest/activation/vnext-activation-receipt-v1.json','depends_on':['rollback_authority']},
 {'id':'rollback_authority','target_path':'manifest/rollback/vnext-canonical-rollback-manifest-v1.json','depends_on':[]},
 {'id':'active_audit_authority','target_path':'manifest/authorities/vnext-post-activation-active-audit-authority-v1.json','depends_on':['active_auditor']},
 {'id':'active_auditor','target_path':'app/cli/audit.py','depends_on':['product_cli','platform_lock','r2','state']}]
 g.pop('authority_identity',None);g['authority_identity']=ident(g);newg=target/'manifest/authorities/vnext-active-product-dependency-graph-v3.json';newg.write_text(json.dumps(g,indent=2,sort_keys=True)+'\n');graph_path.unlink()
 spec=importlib.util.spec_from_file_location('byte_policy',repo/'scripts/vnext_active_runtime_bytes_policy_v3.py');policy=importlib.util.module_from_spec(spec);spec.loader.exec_module(policy);rows=[]
 for base in ('app','config','contracts','foundation','manifest'):
  d=target/base
  if not d.exists():continue
  for p in sorted(d.rglob('*')):
   rel=p.relative_to(target).as_posix()
   if p.is_dir() and not p.is_symlink():continue
   kind=policy.classify(rel,p.is_symlink())
   if kind==policy.FORBIDDEN:raise RuntimeError('forbidden product byte: '+rel)
   if kind==policy.ALLOWED_REGENERABLE_RUNTIME:continue
   if p.is_file():rows.append({'path':rel,'type':'file','size':p.stat().st_size,'sha256':sha(p)})
 oldlock=json.loads((target/'product-lock.json').read_text());r2=json.loads((target/'components/editor-r2/dependency-lock.json').read_text());platform=json.loads((target/'manifest/platform-lock.json').read_text())
 components={'R2_REFERENCE':dict(oldlock['components']['R2_REFERENCE'],role='REFERENCE_REALIZER',verification='EXHAUSTIVE_LOCK_SET_EQUALITY'),'PYTHON_ML_PLATFORM':dict(oldlock['components']['PYTHON_ML_PLATFORM'],role='DECLARED_PLATFORM_DEPENDENCY',verification='FULL_TREE_IDENTITY')}
 lock={'schema':'vnext-product-lock','schema_version':4,'status':'ACTIVE','product_root':'/root/pastila-vnext/v1','active_integration_state':'ACTIVATED','runtime_source_commit':RUNTIME,'assembly_authority_commit':BASE,'activation_attestation':{'active_state_authority_identity':'f7ab34467d316c9ef0a827c5483eab291ea1976036f38f8d0578edc471eed164','activation_receipt_identity':'2d79120f5b2b294ae9067e1596f7460778035e1837e849bf0b45896e2335e9d2','rollback_manifest_identity':'2d86d60806ca15eb8051dcbf61952c10c0d669e077f3ff4e7d167bf3b5509485','active_audit_authority_identity':'7449832298f2e16ee65dfe2611af97cb9d44b0de3e12da5b40162971fc16c29d'},'activation':{'authorized':True,'prepared':False,'product_lock_replacement':True,'full_root_atomic_swap_required':True},'active_graph_identity':g['authority_identity'],'application_files':rows,'mutable_state':oldlock['mutable_state'],'runtime_cache_policy':{'allowed':list(policy.DECLARED_ALLOWED),'authoritative':False,'regenerable':True},'components':components,'excluded_categories':oldlock['excluded_categories'],'legacy_dependency_count':0,'managed_inventory_semantics':'EXHAUSTIVE_REJECT_EXTRA_EXCEPT_DECLARED_RUNTIME_CACHE'}
 write(target/'product-lock.json',lock,'product_lock_identity')
 return {'product_lock_identity':lock['product_lock_identity'],'product_lock_sha256':sha(target/'product-lock.json'),'active_graph_identity':g['authority_identity'],'managed_files':len(rows),'status':'PASS'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--target',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.repo,a.source,a.target),sort_keys=True))
