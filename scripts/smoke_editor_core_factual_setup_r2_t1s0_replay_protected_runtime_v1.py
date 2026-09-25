from __future__ import annotations
import json
from train_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1 import ARMS,SEEDS,real_token_map,receipt,slot
class Tok:
 def __call__(self,text,**kwargs): return {'input_ids':list(range(len(text))),'offset_mapping':[(i,i+1) for i in range(len(text))]}
def main():
 assistant='{"text":"Comisia a propus 30 de zile. Decizia nu este finală."}'; start=assistant.index('Comisia'); span={'field':'text','start':start,'end':start+len('Comisia a propus 30 de zile. Decizia nu este finală.'),'text':'Comisia a propus 30 de zile. Decizia nu este finală.'}; mapping=real_token_map(Tok(),assistant,[span]); receipts=[]
 for arm in ARMS:
  for seed in SEEDS: receipts.append(receipt('terminal',slot(arm,seed),{'status':'PASS_FIXTURE_ONLY','mapping_identity':mapping['mapped_spans'],'model_loaded':False,'optimizer_created':False,'optimizer_steps':0,'training_performed':False,'inference_performed':False}))
 print(json.dumps({'status':'PASS_FIXTURE_ONLY','slots':len(receipts),'distinct_slots':len({x['slot_id'] for x in receipts}),'model_loaded':False,'optimizer_created':False,'training_performed':False,'inference_performed':False},sort_keys=True))
if __name__=='__main__': main()
