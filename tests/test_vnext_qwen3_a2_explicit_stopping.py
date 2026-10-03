import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def load(n):return json.loads((R/'docs/artifacts'/n).read_text())
def auditor():
 s=importlib.util.spec_from_file_location('a',R/'scripts/audit_vnext_qwen3_a2_explicit_stopping.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_self_contained_auditor_passes():assert auditor().main(R)['status']=='PASS'
def test_frozen_intervention_and_seeds():
 c=load('vnext-qwen3-a2-explicit-stopping-frozen-config.json');assert c['seeds']==[2111,3407,4933];assert c['intervention']['content_loss_share']==.95 and c['intervention']['terminal_eos_loss_share']==.05;assert c['intervention']['sampling']=='C0_UNIFORM'
def test_failure_is_per_seed_and_not_hidden():
 e=load('vnext-qwen3-a2-explicit-stopping-evaluation-result.json');assert e['terminal']=='A2_ACCEPTANCE_NOT_MET';assert all(not x['pass'] for x in e['a2_per_seed'].values())
def test_payoff_and_eos_safeguards_recorded():
 e=load('vnext-qwen3-a2-explicit-stopping-evaluation-result.json');assert all(x['length_and_completion']['payoff_counts']['INCOMPLETE_PAYOFF']>0 for x in e['a2_per_seed'].values());assert all(x['length_and_completion']['generation_cap_hits']>0 for x in e['a2_per_seed'].values())
def test_runtime_projection_separate_and_surfaces_sealed():
 e=load('vnext-qwen3-a2-explicit-stopping-evaluation-result.json');assert e['runtime_projection_effect']['safety_attribution']=='RUNTIME_CONSTRAINED_PROJECTION_NOT_MODEL_WEIGHTS';assert e['holdout']=={'exposure':0,'unsealed':False} and e['qwen3_bakeoff_exposure']==0
