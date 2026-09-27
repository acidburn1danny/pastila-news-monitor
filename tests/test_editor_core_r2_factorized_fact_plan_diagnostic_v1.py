import json,re,subprocess,sys
from pathlib import Path

def test_build_and_fixture_boundary():
 b=subprocess.run([sys.executable,'-B','scripts/build_editor_core_r2_factorized_fact_plan_diagnostic_v1.py'],check=True,capture_output=True,text=True)
 assert json.loads(b.stdout)['status']=='PASS_BUILD'
 f=subprocess.run([sys.executable,'-B','scripts/fixture_editor_core_r2_factorized_fact_plan_diagnostic_v1.py'],check=True,capture_output=True,text=True)
 assert json.loads(f.stdout)=={'cases':48,'historical_holdouts_read':False,'interventions':4,'model_loaded':False,'optimizer_created':False,'oracle_plans':48,'slots':12,'status':'PASS_FIXTURE_ONLY','training_performed':False}

def test_protocol_closes_old_mechanisms_and_authority():
 p=json.loads(Path('docs/artifacts/editor-core-r2-factorized-fact-plan-diagnostic-v1-protocol.json').read_text(encoding='utf-8'))
 assert p['parent']=='R2_STEP_9' and p['one_pass_reweighting_closed']
 assert p['weighted_sft_t1s0']=='CLOSED_REFERENCE_ONLY' and p['contrastive_and_kl_forms_tested']=='CLOSED'
 assert not p['model_load_authorized'] and not p['optimizer_creation_authorized'] and not p['training_authorized'] and not p['parent_selection_authority']

def test_oracle_plan_fields_are_nonempty_and_source_bound():
 rows=[json.loads(x) for x in Path('docs/artifacts/editor-core-r2-factorized-fact-plan-diagnostic-v1-oracle-plans.jsonl').read_text(encoding='utf-8').splitlines()]
 assert len(rows)==48
 for row in rows:
  spans={x['span_id'] for x in row['authority_inventory']}
  assert row['actors_entities'] and row['selected_facts']
  expected=[n for span in row['authority_inventory'] for n in re.findall(r'(?<!\w)\d+(?:[.,]\d+)?(?!\w)',span['text'])]
  assert [n['surface'] for n in row['numbers']]==expected
  assert all(x['support_span_id'] in spans for x in row['actors_entities']+row['numbers'])
