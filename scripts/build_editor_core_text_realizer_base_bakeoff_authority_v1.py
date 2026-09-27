from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).parents[1]; ART=ROOT/'docs/artifacts'
def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def ident(v:dict,key:str)->dict:
 v[key]=hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest();return v
def main():
 files={p:sha(ROOT/p) for p in ['scripts/editor_core_text_realizer_base_bakeoff_runtime_v1.py','scripts/preflight_editor_core_text_realizer_base_bakeoff_runtime_v1.py','scripts/supervise_editor_core_text_realizer_base_bakeoff_v1.py']}
 core={'schema':'editor-text-realizer-base-bakeoff-execution-authority','schema_version':1,'runtime_source_commit':'7156d5744c0bf7542ed9a12f09d80a8893a8d606','runtime_source_tree':'e052e2659249e744b695d08d73e06178c4ede022','protocol_identity':'1159a4cd2c658437065485d596178b13d2f2e716c707b48a87ab901f4c2b9e4c','pack_identity':'1c6a6a6eccf1b23bb8627b7a91832936fdd7df56b34dc8cde3ad923a0653cfc3','acquisition_authority_identity':'52346e1d315ab7a6245a3c81a24ce8518355b5bd586636cea6a36253d3c3536f','acquisition_receipt_identity':'3529f416d9aa9e2a96d6a254609ea51decbd6cf20906e2302afa61ece5bb685c','runtime_python':'/root/pf9-ml-runtime-20260926/bin/python','candidates':{'C0_R2_MINISTRAL':{'model':'/root/pf9-v12-recovery-replay-20260917/models/A','tokenizer':'/root/pf9-v12-recovery-replay-20260917/tokenizers/A','adapter':'/root/pf9-editor-core-v10-v12-targeted-r2-output/checkpoint-000009/adapter','adapter_identity':'c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02'},'C1_QWEN3_8B':{'model':'/root/pf9-editor-model-store/sha256/be259728abcc2c864bdf4d035267a8fcf8ccc57e4e277f8bd5d0934f1963fbc7','revision':'b968826d9c46dd6066d109eabc6255188de91218'},'C2_QWEN25_7B':{'model':'/root/pf9-editor-model-store/sha256/5fe636f259ab71443c94837b3c19420e0b796c3d9edcd371332b8ff88577e8fd','revision':'a09a35458c702b33eeacc393d103063234e8bc28'}},'runs':['PRIMARY','BYTE_EXACT_REPLAY'],'slots':6,'fresh_zero_step_per_slot':True,'distinct_empty_roots':True,'deterministic_decoding':True,'retry_authorized':False,'stop_on_first_failure':True,'semantic_scoring_authorized':False,'parent_selection_authority':False,'training_authorized':False,'files':files}
 a=ident(core,'authority_identity');(ART/'editor-core-text-realizer-base-bakeoff-v1-execution-authority.json').write_text(json.dumps(a,sort_keys=True,indent=2)+'\n')
 print(json.dumps({'status':'PASS_BUILD','authority_identity':a['authority_identity']},sort_keys=True))
if __name__=='__main__':main()
