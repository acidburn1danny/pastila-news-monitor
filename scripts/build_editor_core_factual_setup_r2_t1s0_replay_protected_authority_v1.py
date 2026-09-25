from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-factual-setup-r2-t1s0-replay-protected-v1'; SEEDS=(161803,271828,314159); ARMS=('T1_S0_EXISTING_CONTROL','T1_S0_REPLAY_PROTECTED')
FILES={k:ROOT/v for k,v in {'supervisor':'scripts/supervise_editor_core_factual_setup_r2_t1s0_replay_protected_v1.py','audit':'scripts/audit_editor_core_factual_setup_r2_t1s0_replay_protected_authority_v1.py','tests':'tests/test_editor_core_factual_setup_r2_t1s0_replay_protected_authority_v1.py'}.items()}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ident(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 b=json.loads((ART/f'{P}-runtime-boundary.json').read_text('utf-8')); slots=[{'slot_id':f'{a}__seed_{s}','arm':a,'seed':s,'run_limit':1,'optimizer_steps':9,'retry_allowed':False,'fresh_exact_tokenizer_zero_step_required':True,'output_root_policy':'DISTINCT_EMPTY'} for a in ARMS for s in SEEDS]
 core={'schema':'editor-factual-setup-r2-t1s0-replay-protected-execution-authority','schema_version':1,'status':'AUTHORIZED_BOUNDARY_NOT_EXECUTED','runtime_source_commit':'2aafeb6536b779ad4e5c7b0417c86188a56a6bc7','runtime_source_tree':'5f6e7298f838e9f1c1adfeb6401019890d3923d6','runtime_boundary_identity':b['runtime_boundary_identity'],'protocol_identity':b['protocol_identity'],'pack_identity':b['pack_identity'],'evaluation_identity':b['evaluation_identity'],'parent':'R2_STEP_9','parent_adapter_identity':b['parent_adapter_identity'],'recipe':'S0_CONTROL','tokenizer_sha256':b['tokenizer_sha256'],'slots':slots,'slot_count':6,'program_run_limit':1,'retry_allowed':False,'failure_policy':'STOP_PROGRAM_AT_FIRST_FAILURE','zero_step_timing':'IMMEDIATELY_BEFORE_EACH_SLOT_MODEL_LOAD','output_isolation':'DISTINCT_NEW_EMPTY_ROOT_PER_SLOT','files':{k:sha(v) for k,v in FILES.items()},'historical_holdouts_allowed':False,'parent_selection_authority':False,'promotion':False,'release':False,'execution_performed':False}
 out={**core,'authority_identity':ident(core)}; (ART/f'{P}-execution-authority.json').write_bytes((json.dumps(out,indent=2,sort_keys=True)+'\n').encode())
if __name__=='__main__': main()
