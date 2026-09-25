import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()

def test_terminal_result_is_fail_closed_and_bounded():
    p=ROOT/'docs/artifacts/editor-core-factual-setup-r2-causal-diagnostic-terminal-result-v1.json'
    v=json.loads(p.read_text(encoding='utf-8')); ident=v.pop('result_identity')
    assert ident==hashlib.sha256(canonical(v)).hexdigest()
    assert v['decision']=={'T1_S1':'STOP','S1_HIGHER_PLASTICITY':'STOP_FOR_CURRENT_CONTINUATION','T1_S0':'HYPOTHESIS_ONLY_REQUIRES_REDESIGNED_REPLAY_PROTECTIONS','development_parent':'R2_STEP_9','parent_selection_authority':False,'promotion':False,'release':False}
    assert v['stop_rule_triggered']=='STOP_ON_REPLAY_REGRESSION_ABOVE_ZERO_MATERIAL_CASES'
    assert v['replay']['material_regression'] is True
    assert v['historical_holdouts_accessed'] is False
    assert v['training_performed_during_evaluation'] is False and v['optimizer_steps_during_evaluation']==0

def test_replay_inputs_have_no_assistant_targets():
    p=ROOT/'docs/artifacts/editor-core-factual-setup-r2-causal-replay-requests-v1.jsonl'
    rows=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
    assert len(rows)==24 and len({x['example_id'] for x in rows})==24
    assert all(x['split']=='REPLAY_RETENTION' and len(x['messages'])==2 for x in rows)
    assert all(not any(m['role']=='assistant' for m in x['messages']) for x in rows)
