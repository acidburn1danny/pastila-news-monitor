"""Fixture-only causal boundary for fact-plan interventions."""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-r2-factorized-fact-plan-diagnostic-v1'
def sha(b): return hashlib.sha256(b).hexdigest()
def load(art,n): return json.loads((art/n).read_text(encoding='utf-8'))
def rows(art,n): return [json.loads(x) for x in (art/n).read_text(encoding='utf-8').splitlines()]
def validate(m,p,i,e,c,o):
 assert len(c)==len(o)==48 and len({x['case_id'] for x in c})==48
 assert {x['case_id'] for x in c}=={x['case_id'] for x in o}; assert all(not x['oracle_plan_exposed'] and not x['assistant_target_exposed'] for x in c)
 assert len(i['interventions'])==4 and i['slots']==12 and len(i['seeds'])==3
 assert p['parent']=='R2_STEP_9' and not p['model_load_authorized'] and not p['optimizer_creation_authorized'] and not p['training_authorized'] and not p['parent_selection_authority']
 assert e['partitions']=={'DEVELOPMENT':24,'REPLAY_RETENTION':24} and 'ANY_MATERIAL_REPLAY_REGRESSION' in e['stop_rules']['STOP']
 assert all(2==x['setup_constraints']['minimum_sentences'] and 3==x['setup_constraints']['maximum_sentences'] for x in o)
 assert all(x['actors_entities'] for x in o)
 for x in o:
  expected=[n for s in x['authority_inventory'] for n in re.findall(r'(?<!\w)\d+(?:[.,]\d+)?(?!\w)',s['text'])]
  assert [n['surface'] for n in x['numbers']]==expected
 assert all(all(n['support_span_id'] in {s['span_id'] for s in x['authority_inventory']} for n in x['numbers']) for x in o)
 return {'status':'PASS_FIXTURE_ONLY','cases':48,'oracle_plans':48,'interventions':4,'slots':12,'model_loaded':False,'optimizer_created':False,'training_performed':False,'historical_holdouts_read':False}
def run(art=ART):
 m=load(art,P+'-manifest.json'); p=load(art,P+'-protocol.json'); i=load(art,P+'-interventions.json'); e=load(art,P+'-evaluation.json'); c=rows(art,P+'-cases.jsonl'); o=rows(art,P+'-oracle-plans.jsonl')
 assert m['files']=={n:sha((art/n).read_bytes()) for n in m['files']}
 return validate(m,p,i,e,c,o)
if __name__=='__main__': print(json.dumps(run(),sort_keys=True))
