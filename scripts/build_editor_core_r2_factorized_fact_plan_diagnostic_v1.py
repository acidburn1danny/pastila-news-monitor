"""Build the fixture-only R2 factorized fact-plan diagnostic."""
from __future__ import annotations
import hashlib, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-r2-factorized-fact-plan-diagnostic-v1'
SEEDS=(161803,271828,314159)
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def identified(v,key): v=dict(v); v[key]=sha(canonical(v)); return v
def rows(p): return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
def write_json(name,v): (ART/name).write_bytes((json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode())
def write_jsonl(name,v): (ART/name).write_bytes(b''.join(canonical(x)+b'\n' for x in v))

dev_req=rows(ART/'editor-core-factual-setup-benchmark-v1-requests.jsonl')
dev_key={x['example_id']:x for x in rows(ART/'editor-core-factual-setup-benchmark-v1-answer-key.jsonl')}
train=rows(ART/'editor-core-factual-setup-corrective-v1-training.jsonl')
replay=[x for x in train if x.get('split')=='REPLAY_PROTECTION']
assert len(dev_req)==len(dev_key)==len(replay)==24

schema=identified({'schema':'editor-r2-factorized-fact-plan-schema','schema_version':1,'fields':{
 'case_id':'EXACT_INPUT_CASE_ID','authority_inventory':'ORDERED_SOURCE_BOUND_SPANS','selected_facts':'ORDERED_REQUIRED_FACT_ATOMS',
 'actors_entities':'SOURCE_BOUND_ACTORS_AND_ENTITIES','numbers':'VALUE_UNIT_ROLE_SOURCE_BINDING','epistemic_status':'CLAIM_ATTRIBUTION_MODALITY_CERTAINTY',
 'procedural_status':'PROPOSAL_DECISION_STAGE_CURRENT_EFFECT','contradictions':'SUPPORTED_CROSS_SOURCE_RELATIONS','setup_constraints':'TWO_TO_THREE_SENTENCES_FACTUAL_ONLY'},
 'invariants':['NO_UNSUPPORTED_ATOM','EVERY_ATOM_HAS_SOURCE_SPAN','NUMBERS_KEEP_ROLE_AND_UNIT','CLAIM_STATUS_EXPLICIT','PROCEDURAL_CURRENT_EFFECT_EXPLICIT','NO_VOICE_OR_COMMENTARY']},'schema_identity')

cases=[]; plans=[]
def add(request_row,key_row,partition,failure_class,target):
 payload=json.loads(request_row['messages'][1]['content'].split('\nINPUT=',1)[1]); spans=payload['authority_spans']
 cases.append({'case_id':payload['case_id'],'partition':partition,'failure_class':failure_class,'messages':request_row['messages'],'request_identity':payload['request_identity'],'oracle_plan_exposed':False,'assistant_target_exposed':False})
 required=key_row.get('required_evidence',[]) if key_row else []
 entities=[]; numbers=[]
 for s in spans:
  for value in re.findall(r'\b(?:Entitatea\s+[\w_-]+(?:\s+\d+)?|[A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț_-]+(?:\s+[A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț_-]+){0,3})',s['text']):
   item={'surface':value,'support_span_id':s['span_id']}
   if item not in entities: entities.append(item)
  for value in re.findall(r'(?<!\w)\d+(?:[.,]\d+)?(?!\w)',s['text']):
   numbers.append({'surface':value,'role':'SOURCE_BOUND_UNCHANGED','support_span_id':s['span_id']})
 low=' '.join(s['text'] for s in spans).casefold()
 epistemic=[x for x in ('afirmă','susține','estimează','ar fi','contest') if x in low]
 procedural=[x for x in ('propus','propunere','urmează','vot','decizie finală','rămâne în vigoare','în curs','nu a fost încă') if x in low]
 contradictions=[{'relation':'SUPPORTED_CONTEST_OR_CONTRADICTION','support_span_ids':[s['span_id'] for s in spans]}] if ('contest' in low or failure_class in ('ATTRIBUTED_CONTEST','CATEGORICAL_ALLEGATION')) else []
 plan={'schema':'editor-r2-factorized-fact-plan','schema_version':1,'case_id':payload['case_id'],'request_identity':payload['request_identity'],
  'authority_inventory':[{'span_id':s['span_id'],'source_id':s['source_id'],'text':s['text']} for s in spans],
  'selected_facts':[{'fact_id':f"f{i}",'surface_requirement':x,'support_span_ids':[s['span_id'] for s in spans]} for i,x in enumerate(required,1)] or [{'fact_id':f"s{i}",'surface_requirement':s['text'],'support_span_ids':[s['span_id']]} for i,s in enumerate(spans,1)],
  'actors_entities':entities,'numbers':numbers,'epistemic_status':{'failure_class':failure_class,'markers':epistemic},'procedural_status':{'markers':procedural,'source_bound':True},'contradictions':contradictions,'setup_constraints':{'minimum_sentences':2,'maximum_sentences':3,'factual_only':True},'oracle_setup_target':target}
 plans.append(identified(plan,'plan_identity'))
for r in dev_req:
 k=dev_key[r['example_id']]; add(r,k,'DEVELOPMENT',k['operator'],json.loads(k['assistant_target'])['text'])
for r in replay:
 req={'messages':r['messages'][:2]}; add(req,None,'REPLAY_RETENTION',r['failure_class'],json.loads(r['messages'][2]['content'])['text'])

interventions=identified({'schema':'editor-r2-factorized-intervention-matrix','schema_version':1,'seeds':list(SEEDS),'interventions':[
 {'id':'I0_ONE_PASS_R2','plan_source':'NONE','realizer':'R2_STEP_9','purpose':'ONE_PASS_CONTROL'},
 {'id':'I1_ORACLE_PLAN_SCORE','plan_source':'ORACLE','realizer':'NONE','purpose':'PLAN_VALIDITY_CEILING'},
 {'id':'I2_ORACLE_PLAN_TO_R2_SETUP','plan_source':'ORACLE','realizer':'R2_STEP_9','purpose':'ISOLATE_PLAN_TO_TEXT_REALIZATION'},
 {'id':'I3_R2_PLAN_TO_R2_SETUP','plan_source':'R2_GENERATED','realizer':'R2_STEP_9','purpose':'END_TO_END_FACTORIZED_AND_PLAN_CONSTRUCTION_GAP'}],
 'causal_contrasts':{'PLAN_CONSTRUCTION':'I3_PLAN_VS_I1_ORACLE','PLAN_TO_TEXT':'I2_VS_ORACLE_SETUP_TARGET','FACTORIZATION':'I3_VS_I0','ORACLE_INTERVENTION':'I2_VS_I0'},
 'matched':['CASES','ROW_ORDER_PER_SEED','R2_PARENT','TOKENIZER','DECODING','EVALUATOR','SENTENCE_CONTRACT'],'slots':12},'intervention_identity')

evaluation=identified({'schema':'editor-r2-factorized-evaluation-contract','schema_version':1,'partitions':{'DEVELOPMENT':24,'REPLAY_RETENTION':24},
 'plan_metrics':['UNSUPPORTED_ATOMS','MISSING_REQUIRED_FACTS','ACTOR_ENTITY_FIDELITY','NUMBER_ROLE_FIDELITY','EPISTEMIC_STATUS','PROCEDURAL_STATUS','CONTRADICTION_BINDING'],
 'setup_metrics':['PLAN_TO_TEXT_ENTAILMENT','PLAN_COVERAGE','NO_FACT_BEYOND_PLAN','TWO_TO_THREE_SENTENCES','FUNCTIONAL_ROMANIAN','REPETITION'],
 'seed_stability':'SAME_DIRECTION_AND_NO_MATERIAL_REGRESSION_IN_AT_LEAST_2_OF_3_SEEDS',
 'stop_rules':{'STOP':['ANY_NOVEL_ACTOR','ANY_MATERIAL_NUMBER_ROLE_LOSS','ANY_EPISTEMIC_OR_PROCEDURAL_UPGRADE','ANY_MATERIAL_REPLAY_REGRESSION'],
 'REVISE':['ORACLE_PLAN_IMPROVES_BUT_GENERATED_PLAN_FAILS','PLAN_VALID_BUT_PLAN_TO_TEXT_FAITHFULNESS_FAILS','SEED_DIRECTION_UNSTABLE'],
 'CONTINUE_RESEARCH':['ORACLE_CAUSAL_CEILING_POSITIVE','GENERATED_PLAN_VALIDITY_GAIN_REPLICATED','PLAN_TO_TEXT_FAITHFULNESS_PASS','ZERO_MATERIAL_REPLAY_REGRESSIONS']},
 'claims_forbidden':['PARENT_SELECTION','NATURALISTIC_TRANSFER','PROMOTION','RELEASE']},'evaluation_identity')

protocol=identified({'schema':'editor-r2-factorized-fact-plan-learnability-protocol','schema_version':1,'status':'DESIGN_FIXTURE_ONLY_NO_MODEL_AUTHORITY','parent':'R2_STEP_9','parent_adapter_identity':'c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02','editor_output':'FACTUAL_SETUP_MAX_2_TO_3_SENTENCES','learning_mechanism':'FACTORIZED_PLAN_SUPERVISION_THEN_PLAN_CONDITIONED_REALIZATION','one_pass_reweighting_closed':True,'weighted_sft_t1s0':'CLOSED_REFERENCE_ONLY','contrastive_and_kl_forms_tested':'CLOSED','historical_holdouts_allowed':False,'parent_selection_authority':False,'model_load_authorized':False,'optimizer_creation_authorized':False,'training_authorized':False,'seeds':list(SEEDS),'intervention_identity':interventions['intervention_identity'],'evaluation_identity':evaluation['evaluation_identity'],'schema_identity':schema['schema_identity']},'protocol_identity')

write_json(f'{P}-fact-plan-schema.json',schema); write_jsonl(f'{P}-cases.jsonl',cases); write_jsonl(f'{P}-oracle-plans.jsonl',plans); write_json(f'{P}-interventions.json',interventions); write_json(f'{P}-evaluation.json',evaluation); write_json(f'{P}-protocol.json',protocol)
hashes={n:sha((ART/n).read_bytes()) for n in [f'{P}-fact-plan-schema.json',f'{P}-cases.jsonl',f'{P}-oracle-plans.jsonl',f'{P}-interventions.json',f'{P}-evaluation.json',f'{P}-protocol.json']}
manifest=identified({'schema':'editor-r2-factorized-fact-plan-diagnostic-pack','schema_version':1,'cases':48,'development':24,'replay':24,'oracle_plans':48,'interventions':4,'seeds':list(SEEDS),'fixture_slots':12,'files':hashes,'protocol_identity':protocol['protocol_identity'],'historical_holdouts_read':False,'voice_or_chief_objective':False},'pack_identity')
write_json(f'{P}-manifest.json',manifest)
print(json.dumps({'status':'PASS_BUILD','pack_identity':manifest['pack_identity'],'protocol_identity':protocol['protocol_identity'],'cases':48,'slots':12},sort_keys=True))
