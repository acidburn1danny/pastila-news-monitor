import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def load(n):return json.loads((R/'docs/artifacts'/n).read_text())
def auditor():
 s=importlib.util.spec_from_file_location('a',R/'scripts/audit_vnext_qwen3_voice_a2_design_v1.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_design_auditor_passes():assert auditor().main(R)['status']=='PASS'
def test_one_objective_dimension_and_c0_sampling():
 d=load('vnext-qwen3-voice-a2-design-freeze-v1.json');assert len(d['changed_vs_c0'])==1;assert d['held_constant']['uniform_c0_sampling'];assert 'length-stratified record weights' in d['not_inherited_from_a1']
def test_terminal_objective_is_target_relative_and_mass_preserving():
 d=load('vnext-qwen3-voice-a2-design-freeze-v1.json');x=d['selected_intervention'];assert x['tau_terminal']==.05;assert x['definition']['per_example_total_loss_mass']==1;assert x['new_annotations_required'] is False
def test_execution_and_protected_surfaces_remain_closed():
 d=load('vnext-qwen3-voice-a2-design-freeze-v1.json');assert not d['execution_authorized'] and not d['training_performed'];assert d['holdout_exposure']==0 and d['qwen3_bakeoff_exposure']==0 and d['voice_state']=='DISABLED_UNTIL_PROMOTION'
def test_seed_novelty_and_fail_closed_acceptance():
 d=load('vnext-qwen3-voice-a2-design-freeze-v1.json');assert not(set(d['frozen_seeds'])&{1701,2903,4517,1811,3001,4621,1913,3203,4729});assert d['acceptance']['failure_rule'].startswith('Any seed')
