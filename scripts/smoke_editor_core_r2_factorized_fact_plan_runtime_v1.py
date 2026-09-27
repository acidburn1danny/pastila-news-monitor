"""Fixture-only phase and isolation smoke."""
import json
from pathlib import Path
from editor_core_r2_factorized_fact_plan_runtime_v1 import INTERVENTIONS,execute_fixture
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-r2-factorized-fact-plan-diagnostic-v1'
cases={x['case_id']:x for x in map(json.loads,(ART/(P+'-cases.jsonl')).read_text(encoding='utf-8').splitlines())}; plans={x['case_id']:x for x in map(json.loads,(ART/(P+'-oracle-plans.jsonl')).read_text(encoding='utf-8').splitlines())}; cid=next(iter(cases)); outputs={i:execute_fixture(i,cases[cid],plans[cid]) for i in INTERVENTIONS}
assert not any(x.get('model_loaded') for rs in outputs.values() for x in rs); assert outputs['I1_ORACLE_PLAN_SCORE'][-1]['status']=='PASS_PLAN_VALID'; assert outputs['I0_ONE_PASS_R2'][-1]['mode']=='ONE_PASS_CONTROL'; assert outputs['I2_ORACLE_PLAN_TO_R2_SETUP'][-1]['mode']=='PLAN_CONDITIONED'; assert outputs['I3_R2_PLAN_TO_R2_SETUP'][0]['phase']=='PLAN_GENERATION'
print(json.dumps({'status':'PASS_FIXTURE_SMOKE','interventions':4,'model_loaded':False,'optimizer_created':False,'training_performed':False},sort_keys=True))
