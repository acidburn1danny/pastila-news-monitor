from __future__ import annotations
import json
from pathlib import Path
from editor_core_factual_setup_r2_t1s0_replay_protected_fixture_worker_v1 import ARMS,SEEDS,run_fixture
ROOT=Path(__file__).resolve().parents[1]
class FixtureTokenizer:
 def __call__(self,text,**kwargs): return {'input_ids':list(range(len(text))),'offset_mapping':[(i,i+1) for i in range(len(text))]}
def main():
 f=json.loads((ROOT/'tests/fixtures/editor_core_factual_setup_r2_t1s0_replay_protected_v1/fixture.json').read_text('utf-8')); results=[]
 for arm in ARMS:
  for seed in SEEDS:
   sid=f'{arm}__seed_{seed}'; result=run_fixture(FixtureTokenizer(),f['assistant'],f['critical_spans'],sid,arm,seed); assert result['publication_order'][-1]=='terminal.json'; results.append(result)
 print(json.dumps({'status':'PASS_FIXTURE_ONLY','slots':len(results),'distinct_output_roots':len({x['terminal']['slot_id'] for x in results}),'model_loaded':False,'optimizer_created':False,'optimizer_steps':0,'training_performed':False,'inference_performed':False},sort_keys=True))
if __name__=='__main__': main()
