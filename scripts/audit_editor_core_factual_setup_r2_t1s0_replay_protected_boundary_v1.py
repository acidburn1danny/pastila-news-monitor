from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
from editor_core_factual_setup_r2_t1s0_replay_protected_fixture_worker_v1 import map_spans
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-factual-setup-r2-t1s0-replay-protected-v1'
def ident(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
class OffsetFixtureTokenizer:
 def __call__(self,text,**kwargs): return {'input_ids':list(range(len(text))),'offset_mapping':[(i,i+1) for i in range(len(text))]}
def main():
 b=json.loads((ART/f'{P}-execution-boundary.json').read_text('utf-8')); core=dict(b); got=core.pop('boundary_identity'); assert got==ident(core)
 assert len(b['arms'])==2 and len(b['seeds'])==3 and len(b['slots'])==6 and len({x['slot_id'] for x in b['slots']})==6
 assert all(x['output_root_policy']=='DISTINCT_EMPTY' for x in b['slots']); assert b['matched_row_order_per_seed'] is True
 assert b['token_mapping_rule']=='ALL_CONTIGUOUS_TOKENS_WITH_OFFSETS_INTERSECTING_TEXT_SPAN'
 assert set(b['measurements'])=={'TEACHER_FORCED_FULL_TARGET_BEFORE_AFTER','TEACHER_FORCED_CRITICAL_SPAN_BEFORE_AFTER','DETERMINISTIC_DEVELOPMENT','DETERMINISTIC_REPLAY'}
 assert b['decision_states']==['STOP','REVISE','CONTINUE_RESEARCH']
 assert not any(b[x] for x in ('model_load_authorized','optimizer_creation_authorized','training_authorized','inference_authorized','parent_selection_authority','historical_holdouts_allowed','promotion','release'))
 corpus={x['example_id']:x for x in map(json.loads,(ART/'editor-core-factual-setup-corrective-v1-training.jsonl').read_text('utf-8').splitlines())}
 signal=list(map(json.loads,(ART/f'{P}-protected-signal.jsonl').read_text('utf-8').splitlines())); mapped=0
 for row in signal:
  assistant=corpus[row['example_id']]['messages'][-1]['content']; assert hashlib.sha256(assistant.encode()).hexdigest()==row['assistant_target_sha256']
  result=map_spans(OffsetFixtureTokenizer(),assistant,row['critical_spans']); mapped+=len(result['mapped_spans'])
  for span in row['critical_spans']: assert span['field']=='text' and span['text'] in json.loads(assistant)['text']
 assert len(signal)==72 and mapped>24
 for command in ([sys.executable,str(ROOT/'scripts/zero_step_editor_core_factual_setup_r2_t1s0_replay_protected_v1.py')],[sys.executable,str(ROOT/'scripts/smoke_editor_core_factual_setup_r2_t1s0_replay_protected_v1.py')]): subprocess.run(command,cwd=ROOT,check=True,capture_output=True,text=True)
 print(json.dumps({'status':'PASS','blockers':0,'boundary_identity':got,'arms':2,'seeds':3,'slots':6,'mapped_critical_spans':mapped,'mapped_rows':72,'tokenizer_bound':True,'model_loaded':False,'optimizer_created':False,'training_performed':False,'inference_performed':False},sort_keys=True))
if __name__=='__main__': main()
