from __future__ import annotations
import hashlib,json
from pathlib import Path
from editor_core_factual_setup_r2_t1s0_replay_protected_fixture_worker_v1 import ARMS,SEEDS,identity,row_order
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-factual-setup-r2-t1s0-replay-protected-v1'
def main():
 b=json.loads((ART/f'{P}-execution-boundary.json').read_text('utf-8'))
 if b['arms']!=list(ARMS) or b['seeds']!=list(SEEDS) or len(b['slots'])!=6: raise ValueError('slot closure')
 if b['parent']!='R2_STEP_9' or b['recipe']!='S0_CONTROL': raise ValueError('binding drift')
 if any(b[x] for x in ('model_load_authorized','optimizer_creation_authorized','training_authorized','inference_authorized','parent_selection_authority')): raise ValueError('authority escalation')
 core={'status':'PASS_ZERO_STEP','boundary_identity':b['boundary_identity'],'slots':6,'orders':{str(s):identity(row_order(s)) for s in SEEDS},'tokenizer_sha256':b['tokenizer_sha256'],'model_loaded':False,'optimizer_created':False,'optimizer_steps':0,'training_performed':False,'inference_performed':False}
 print(json.dumps({**core,'receipt_identity':identity(core)},sort_keys=True))
if __name__=='__main__': main()
