from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-factual-setup-r2-t1s0-replay-protected-v1'
def ident(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 a=json.loads((ART/f'{P}-execution-authority.json').read_text('utf-8')); core=dict(a); assert core.pop('authority_identity')==ident(core)
 assert a['runtime_source_commit']=='2aafeb6536b779ad4e5c7b0417c86188a56a6bc7' and a['parent']=='R2_STEP_9' and a['recipe']=='S0_CONTROL'
 assert a['slot_count']==6 and len(a['slots'])==6 and len({x['slot_id'] for x in a['slots']})==6
 assert all(x['optimizer_steps']==9 and x['run_limit']==1 and not x['retry_allowed'] and x['fresh_exact_tokenizer_zero_step_required'] for x in a['slots'])
 assert a['zero_step_timing']=='IMMEDIATELY_BEFORE_EACH_SLOT_MODEL_LOAD' and a['failure_policy']=='STOP_PROGRAM_AT_FIRST_FAILURE'
 assert not any(a[x] for x in ('historical_holdouts_allowed','parent_selection_authority','promotion','release','execution_performed'))
 r=subprocess.run([sys.executable,str(ROOT/'scripts/supervise_editor_core_factual_setup_r2_t1s0_replay_protected_v1.py'),'--audit-only'],cwd=ROOT,check=True,capture_output=True,text=True); assert json.loads(r.stdout)['status']=='PASS_AUTHORITY_AUDIT_ONLY'
 print(json.dumps({'status':'PASS','blockers':0,'authority_identity':a['authority_identity'],'slots':6,'steps_per_slot':9,'program_steps_ceiling':54,'retry_allowed':False,'execution_performed':False,'model_loaded':False,'optimizer_created':False,'training_performed':False},sort_keys=True))
if __name__=='__main__': main()
