from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def ident(x):return hashlib.sha256(canon(x)).hexdigest()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(a,n):return json.loads((a/n).read_text(encoding='utf-8'))
def main(repo):
 repo=Path(repo);a=repo/'docs/artifacts';stem='vnext-qwen3-a2-explicit-stopping-'
 cfg=load(a,stem+'frozen-config.json');tr=load(a,stem+'training-result.json');ev=load(a,stem+'evaluation-result.json');pm=load(a,stem+'package-manifest.json');au=load(a,stem+'audit.json')
 for obj,key in ((cfg,'config_identity'),(tr,'result_identity'),(ev,'result_identity'),(pm,'manifest_identity'),(au,'audit_identity')):assert obj[key]==ident({k:v for k,v in obj.items() if k!=key})
 assert cfg['published_design_identity']=='0e58b1de172e151936c7d3e9060e37d601cc9286af1296fbe0453a039a70a49a'
 assert cfg['implementation_identity']==sha(repo/'scripts/run_vnext_qwen3_a2_explicit_stopping.py') and cfg['intervention']['content_loss_share']==.95 and cfg['intervention']['terminal_eos_loss_share']==.05
 assert cfg['seeds']==[2111,3407,4933] and [x['seed'] for x in tr['runs']]==cfg['seeds']
 assert cfg['intervention']['sampling']=='C0_UNIFORM' and cfg['intervention']['per_example_total_loss_mass']==1.0
 for p in pm['packages']:
  root=Path(p['external_path']);assert root.is_dir() and sha(root/'adapter_model.safetensors')==p['adapter_sha256']
 assert ev['terminal']=='A2_ACCEPTANCE_NOT_MET' and all(not x['pass'] for x in ev['a2_per_seed'].values())
 assert ev['holdout']=={'exposure':0,'unsealed':False} and ev['qwen3_bakeoff_exposure']==0
 assert all(ev['full_validation_scores'][f'A2_SEED_{s}']['memorization']['exact_train_commentary_copies']==0 for s in cfg['seeds'])
 assert au['status']=='PASS_0_INTEGRITY_BLOCKERS_NON_PROMOTABLE' and not au['active_product_modified'] and not au['canonical_rollback_modified'] and not au['adapter_installed'] and not au['promotion']
 out={'status':'PASS','design':cfg['published_design_identity'],'config':cfg['config_identity'],'intervention':cfg['intervention_identity'],'implementation':cfg['implementation_identity'],'training':tr['result_identity'],'evaluation':ev['result_identity'],'manifest':pm['manifest_identity'],'audit':au['audit_identity'],'packages':[p['package_identity'] for p in pm['packages']],'holdout_exposure':0,'voice_state':'DISABLED_UNTIL_PROMOTION'};print(json.dumps(out,sort_keys=True));return out
if __name__=='__main__':main(Path(sys.argv[1]))
