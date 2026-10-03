from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def ident(x):return hashlib.sha256(canon(x)).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(a,n):return json.loads((a/n).read_text(encoding='utf-8'))
def main(repo):
 repo=Path(repo);a=repo/'docs/artifacts';stem='vnext-qwen3-length-stratified-a1-'
 cfg=load(a,stem+'frozen-config.json');tr=load(a,stem+'training-result.json');ev=load(a,stem+'evaluation-result.json');pm=load(a,stem+'package-manifest.json');au=load(a,stem+'audit.json')
 for obj,key in ((cfg,'config_identity'),(tr,'result_identity'),(ev,'result_identity'),(pm,'manifest_identity'),(au,'audit_identity')):assert obj[key]==ident({k:v for k,v in obj.items() if k!=key})
 assert cfg['authority_commit']=='d998f259dd05080e39548866edbb22b2c66e2259'
 assert cfg['dataset_identity']=='b48426314ce66a8bfb8f1e773cf171c07de0116b170dafec2a9c85228439c4e6' and cfg['corpus_freeze_identity']=='e2f94bb1266cbe64ea48eb244d95637c4d5f1dfdb7d250b3857834c4dc445a8c'
 assert cfg['seeds']==[1913,3203,4729] and [x['seed'] for x in tr['runs']]==cfg['seeds']
 sa=cfg['sampling_algorithm'];assert sa['counts']=={'concise':12,'medium':19,'long':8} and sa['record_duplication'] is False and sa['record_omission'] is False
 assert abs(sum(sa['counts'][k]*sa['weights'][k] for k in sa['counts'])-39)<1e-12
 for p in pm['packages']:
  root=Path(p['external_path']);assert root.is_dir() and sha(root/'adapter_model.safetensors')==p['adapter_sha256']
 assert ev['terminal']=='STOP_ABLATION_ACCEPTANCE_NOT_MET' and not any(x['pass'] for x in ev['per_seed_acceptance'].values())
 assert ev['holdout']=={'exposure':0,'unsealed':False} and ev['runtime_projection_effect']['final_unsupported_fact_rate']==0
 assert all(ev['full_validation_scores'][f'A1_SEED_{s}']['memorization']['exact_train_commentary_copies']==0 for s in cfg['seeds'])
 assert au['status']=='PASS_0_INTEGRITY_BLOCKERS_NON_PROMOTABLE' and au['distribution_hypothesis']=='FALSIFIED_OR_INSUFFICIENT_BY_FROZEN_CRITERIA'
 assert not au['active_product_modified'] and not au['canonical_rollback_modified'] and not au['adapter_installed'] and not au['promotion']
 out={'status':'PASS','config':cfg['config_identity'],'sampling':cfg['sampling_identity'],'training':tr['result_identity'],'evaluation':ev['result_identity'],'manifest':pm['manifest_identity'],'audit':au['audit_identity'],'holdout_exposure':0,'voice_state':'DISABLED_UNTIL_PROMOTION'};print(json.dumps(out,sort_keys=True));return out
if __name__=='__main__':main(sys.argv[1])
