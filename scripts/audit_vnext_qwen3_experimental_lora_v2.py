from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def ident(x):return hashlib.sha256(canon(x)).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def load(a,n):return json.loads((a/n).read_text(encoding='utf-8'))
def main(repo):
 repo=Path(repo);a=repo/'docs/artifacts'
 cfg=load(a,'vnext-qwen3-experimental-lora-v2-frozen-config.json');tr=load(a,'vnext-qwen3-experimental-lora-v2-training-result.json');ev=load(a,'vnext-qwen3-experimental-lora-v2-evaluation-result.json');pm=load(a,'vnext-qwen3-experimental-lora-v2-package-manifest.json');au=load(a,'vnext-qwen3-experimental-lora-v2-audit.json')
 assert cfg['config_identity']==ident({k:v for k,v in cfg.items() if k!='config_identity'})
 assert tr['result_identity']==ident({k:v for k,v in tr.items() if k!='result_identity'})
 assert ev['result_identity']==ident({k:v for k,v in ev.items() if k!='result_identity'})
 assert pm['manifest_identity']==ident({k:v for k,v in pm.items() if k!='manifest_identity'})
 assert au['audit_identity']==ident({k:v for k,v in au.items() if k!='audit_identity'})
 assert cfg['dataset_identity']=='b48426314ce66a8bfb8f1e773cf171c07de0116b170dafec2a9c85228439c4e6'
 assert cfg['corpus_freeze_identity']=='e2f94bb1266cbe64ea48eb244d95637c4d5f1dfdb7d250b3857834c4dc445a8c'
 assert cfg['seeds']==[1811,3001,4621] and [r['seed'] for r in tr['runs']]==[1811,3001,4621]
 for p in pm['packages']:
  root=Path(p['external_path']); assert root.is_dir()
  assert sha(root/'adapter_model.safetensors')==p['adapter_sha256']
 assert ev['holdout']=={'exposure':0,'unsealed':False}
 assert ev['acceptance']['unsupported_fact_rate_after_projection_zero']
 assert ev['acceptance']['projection_violations_zero']
 assert ev['acceptance']['setup_commentary_boundary_violations_zero']
 assert all(ev['full_validation_scores'][f'LORA2_SEED_{s}']['memorization']['exact_train_commentary_copies']==0 for s in (1811,3001,4621))
 assert au['status']=='PASS_0_INTEGRITY_BLOCKERS_NON_PROMOTABLE' and au['terminal']=='CONTINUE_EXPERIMENTAL_EVIDENCE'
 assert not au['active_product_modified'] and not au['canonical_rollback_modified'] and not au['adapter_installed'] and not au['promotion']
 out={'status':'PASS','config':cfg['config_identity'],'training':tr['result_identity'],'evaluation':ev['result_identity'],'manifest':pm['manifest_identity'],'audit':au['audit_identity'],'packages':[p['package_identity'] for p in pm['packages']],'holdout_exposure':0,'voice_state':'DISABLED_UNTIL_PROMOTION'}
 print(json.dumps(out,sort_keys=True));return out
if __name__=='__main__':main(sys.argv[1])
