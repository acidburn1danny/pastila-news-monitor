import importlib.util,json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def mod():
 s=importlib.util.spec_from_file_location('a',R/'scripts/audit_vnext_qwen3_experimental_lora_v2.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_self_contained_auditor_passes(): assert mod().main(R)['status']=='PASS'
def test_non_promotable_and_holdout_sealed():
 a=json.loads((R/'docs/artifacts/vnext-qwen3-experimental-lora-v2-audit.json').read_text())
 e=json.loads((R/'docs/artifacts/vnext-qwen3-experimental-lora-v2-evaluation-result.json').read_text())
 assert a['terminal']=='CONTINUE_EXPERIMENTAL_EVIDENCE' and not a['promotion']
 assert e['holdout']=={'exposure':0,'unsealed':False}
def test_comparison_uses_compatible_common_set():
 e=json.loads((R/'docs/artifacts/vnext-qwen3-experimental-lora-v2-evaluation-result.json').read_text())
 assert all(v['cases']==9 for v in e['compatible_common_9_scores'].values())
 assert all(v['cases']==15 for v in e['full_validation_scores'].values())
def test_runtime_projection_not_attributed_to_weights():
 e=json.loads((R/'docs/artifacts/vnext-qwen3-experimental-lora-v2-evaluation-result.json').read_text())
 assert e['runtime_projection_effect']['safety_attribution']=='RUNTIME_CONSTRAINED_PROJECTION_NOT_MODEL_WEIGHTS'
 assert e['runtime_projection_effect']['final_unsupported_fact_rate']==0
