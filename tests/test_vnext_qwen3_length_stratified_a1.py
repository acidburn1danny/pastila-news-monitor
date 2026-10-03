import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def mod():
 s=importlib.util.spec_from_file_location('a',R/'scripts/audit_vnext_qwen3_length_stratified_a1.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_self_contained_auditor_passes():assert mod().main(R)['status']=='PASS'
def test_only_sampling_weighting_changed_and_mass_preserved():
 c=json.loads((R/'docs/artifacts/vnext-qwen3-length-stratified-a1-frozen-config.json').read_text());s=c['sampling_algorithm'];assert s['name']=='ALL_RECORDS_ONCE_PER_EPOCH_STRATUM_LOSS_WEIGHTING';assert sum(s['counts'][k]*s['weights'][k] for k in s['counts'])==39
def test_frozen_failure_is_not_hidden_by_aggregate():
 e=json.loads((R/'docs/artifacts/vnext-qwen3-length-stratified-a1-evaluation-result.json').read_text());assert e['terminal']=='STOP_ABLATION_ACCEPTANCE_NOT_MET';assert all(not x['pass'] for x in e['per_seed_acceptance'].values())
def test_projection_separate_and_holdout_sealed():
 e=json.loads((R/'docs/artifacts/vnext-qwen3-length-stratified-a1-evaluation-result.json').read_text());assert e['runtime_projection_effect']['safety_attribution']=='RUNTIME_CONSTRAINED_PROJECTION_NOT_MODEL_WEIGHTS';assert e['holdout']=={'exposure':0,'unsealed':False}
