import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_editor_core_factual_setup_corrective_v1 import audit
def test_closure():
    r=audit();assert r['status']=='PASS';assert (r['targeted_rows'],r['replay_rows'],r['holdout_rows'])==(48,24,24);assert r['exact_target_contamination']==0;assert not r['historical_holdouts_read']
def test_holdout_is_blind_and_disjoint():
    art=ROOT/'docs/artifacts';p='editor-core-factual-setup-corrective-v1-';tr=[json.loads(x) for x in (art/(p+'training.jsonl')).read_bytes().splitlines()];hr=[json.loads(x) for x in (art/(p+'holdout-requests.jsonl')).read_bytes().splitlines()];assert {x['example_id'] for x in tr}.isdisjoint({x['example_id'] for x in hr});assert all(len(x['messages'])==2 for x in hr)
def test_no_voice_or_chief_objective():
    raw=(ROOT/'docs/artifacts/editor-core-factual-setup-corrective-v1-config.json').read_text(encoding='utf-8');assert 'c680d686' in raw;assert json.loads(raw)['voice_or_chief_objective'] is False
