import json
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'docs/artifacts/vnext-qwen3-blind-commentary-adjudication-v1.json'
def load(): return json.loads(P.read_text())
def test_complete_blind_inventory():
 x=load(); assert x['unique_outputs']==24 and x['seed_outputs']==72 and x['seed_stable_cases']==24 and len(x['scores'])==24
def test_structural_contract_is_fail_closed():
 x=load(); assert x['structural_violation_outputs']==12 and x['structural_violation_cases']==['VOICE-V1-01','VOICE-V1-02','VOICE-V1-15','VOICE-V1-22']
def test_quality_and_repetition_terminal():
 x=load(); assert x['quality_composite_mean']<3 and x['terminal']=='REJECT_STRUCTURAL_AND_COMMENTARY_QUALITY'; assert x['repetition']['internal_repetition_cases']
def test_protected_state():
 x=load(); assert x['promotion'] is False and x['voice_state']=='DISABLED_UNTIL_PROMOTION' and x['legacy_dependency_count']==0
