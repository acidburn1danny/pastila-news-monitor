from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-factual-setup-r2-t1s0-replay-protected-v1'
FILES={
 'worker':ROOT/'scripts/editor_core_factual_setup_r2_t1s0_replay_protected_fixture_worker_v1.py',
 'zero_step':ROOT/'scripts/zero_step_editor_core_factual_setup_r2_t1s0_replay_protected_v1.py',
 'smoke':ROOT/'scripts/smoke_editor_core_factual_setup_r2_t1s0_replay_protected_v1.py',
 'audit':ROOT/'scripts/audit_editor_core_factual_setup_r2_t1s0_replay_protected_boundary_v1.py',
 'fixture':ROOT/'tests/fixtures/editor_core_factual_setup_r2_t1s0_replay_protected_v1/fixture.json'}
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ident(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 protocol=json.loads((ART/f'{P}-protocol.json').read_text('utf-8')); pack=json.loads((ART/f'{P}-manifest.json').read_text('utf-8'))
 slots=[{'slot_id':f'{a}__seed_{s}','arm':a,'seed':s,'output_root_policy':'DISTINCT_EMPTY'} for a in ('T1_S0_EXISTING_CONTROL','T1_S0_REPLAY_PROTECTED') for s in (161803,271828,314159)]
 core={'schema':'editor-factual-setup-r2-t1s0-replay-protected-fixture-boundary','schema_version':1,'status':'FIXTURE_ONLY_REAL_RUNS_NOT_AUTHORIZED','published_source_commit':'d576541042a2312bc9c1cacdd9b0d91921ae4882','published_source_tree':'dbf816450e24d7030be5a3ea073acc3f54fe99b8','protocol_identity':protocol['protocol_identity'],'pack_identity':pack['pack_identity'],'parent':'R2_STEP_9','recipe':'S0_CONTROL','tokenizer_sha256':'d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135','token_mapping_rule':'ALL_CONTIGUOUS_TOKENS_WITH_OFFSETS_INTERSECTING_TEXT_SPAN','arms':['T1_S0_EXISTING_CONTROL','T1_S0_REPLAY_PROTECTED'],'seeds':[161803,271828,314159],'slots':slots,'matched_row_order_per_seed':True,'measurements':['TEACHER_FORCED_FULL_TARGET_BEFORE_AFTER','TEACHER_FORCED_CRITICAL_SPAN_BEFORE_AFTER','DETERMINISTIC_DEVELOPMENT','DETERMINISTIC_REPLAY'],'decision_states':['STOP','REVISE','CONTINUE_RESEARCH'],'output_isolation':'DISTINCT_EMPTY_ROOT_PER_SLOT','terminal_rule':'TERMINAL_RECEIPT_LAST_NO_PARTIAL_ELIGIBLE_EVIDENCE','files':{k:sha(v) for k,v in FILES.items()},'model_load_authorized':False,'optimizer_creation_authorized':False,'optimizer_steps_authorized':0,'training_authorized':False,'inference_authorized':False,'parent_selection_authority':False,'historical_holdouts_allowed':False,'promotion':False,'release':False}
 out={**core,'boundary_identity':ident(core)}; (ART/f'{P}-execution-boundary.json').write_bytes((json.dumps(out,indent=2,sort_keys=True)+'\n').encode('utf-8'))
if __name__=='__main__': main()
