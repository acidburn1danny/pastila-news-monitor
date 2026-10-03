from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def ident(x):return hashlib.sha256(canon(x)).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main(repo):
 repo=Path(repo);a=repo/'docs/artifacts';c=load(a/'vnext-qwen3-voice-a2-candidate-interventions-v1.json');d=load(a/'vnext-qwen3-voice-a2-design-freeze-v1.json');u=load(a/'vnext-qwen3-voice-a2-design-audit-v1.json')
 assert c['candidate_matrix_identity']==ident({k:v for k,v in c.items() if k!='candidate_matrix_identity'})
 assert d['design_identity']==ident({k:v for k,v in d.items() if k!='design_identity'})
 assert u['audit_identity']==ident({k:v for k,v in u.items() if k!='audit_identity'})
 assert d['authority']['commit']=='54551baae91e1d97922afd16a6e5d14138a52bf1' and d['authority']['tree']=='2371a91178b1fb32ad5e713ad65775af45572107'
 assert d['selected_intervention']['id']=='TARGET_RELATIVE_TERMINAL_EOS_LOSS_SHARE' and d['selected_intervention']['tau_terminal']==.05
 assert d['selected_intervention']['definition']['per_example_total_loss_mass']==1.0
 assert d['frozen_seeds']==[2111,3407,4933] and len(set(d['frozen_seeds'])&{1701,2903,4517,1811,3001,4621,1913,3203,4729})==0
 assert d['held_constant']['uniform_c0_sampling'] and 'length-stratified record weights' in d['not_inherited_from_a1']
 assert not d['execution_authorized'] and not d['training_performed'] and d['holdout_exposure']==0 and d['qwen3_bakeoff_exposure']==0
 assert u['checks']['new_semantic_owner_authority_invented'] is False and u['checks']['training_executed'] is False; assert all(v for k,v in u['checks'].items() if k not in ('new_semantic_owner_authority_invented','training_executed')) and u['verdict']=='A2_DESIGN_DEFENSIBLE' and not u['blockers'] and not u['training_performed']
 out={'status':'PASS','candidate_matrix':c['candidate_matrix_identity'],'design':d['design_identity'],'audit':u['audit_identity'],'training_performed':False,'holdout_exposure':0,'voice_state':'DISABLED_UNTIL_PROMOTION'};print(json.dumps(out,sort_keys=True));return out
if __name__=='__main__':main(Path(sys.argv[1]))
