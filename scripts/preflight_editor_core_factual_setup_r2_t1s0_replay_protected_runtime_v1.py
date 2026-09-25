from __future__ import annotations
import hashlib,json
from pathlib import Path
from train_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1 import ARMS,SEEDS,EXPECTED_TOKENIZER,identity,real_token_map,row_order
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-factual-setup-r2-t1s0-replay-protected-v1'
class FixtureTokenizer:
 def __call__(self,text,**kwargs): return {'input_ids':list(range(len(text))),'offset_mapping':[(i,i+1) for i in range(len(text))]}
def main():
 corpus={x['example_id']:x for x in map(json.loads,(ART/'editor-core-factual-setup-corrective-v1-training.jsonl').read_text('utf-8').splitlines())}; annotations=list(map(json.loads,(ART/f'{P}-protected-signal.jsonl').read_text('utf-8').splitlines())); mapped=0
 for row in annotations:
  assistant=corpus[row['example_id']]['messages'][-1]['content']; assert hashlib.sha256(assistant.encode()).hexdigest()==row['assistant_target_sha256']; mapped+=len(real_token_map(FixtureTokenizer(),assistant,row['critical_spans'])['mapped_spans'])
 core={'status':'PASS_EXECUTABLE_ZERO_STEP_FIXTURE_TOKENIZER','tokenizer_sha256':EXPECTED_TOKENIZER,'tokenizer_runtime_required_before_real_execution':True,'arms':len(ARMS),'seeds':len(SEEDS),'slots':len(ARMS)*len(SEEDS),'rows':len(annotations),'mapped_spans':mapped,'orders':{str(s):identity(row_order(s)) for s in SEEDS},'model_loaded':False,'optimizer_created':False,'optimizer_steps':0,'training_performed':False,'inference_performed':False}
 print(json.dumps({**core,'receipt_identity':identity(core)},sort_keys=True))
if __name__=='__main__': main()
