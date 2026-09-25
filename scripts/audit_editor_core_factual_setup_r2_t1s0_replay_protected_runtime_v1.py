from __future__ import annotations
import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-factual-setup-r2-t1s0-replay-protected-v1'
def ident(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 b=json.loads((ART/f'{P}-runtime-boundary.json').read_text('utf-8')); core=dict(b); assert core.pop('runtime_boundary_identity')==ident(core)
 assert b['published_source_commit']=='cc5e1894506372afca0a915a6ed202968c7b7f10' and b['parent']=='R2_STEP_9' and b['recipe']=='S0_CONTROL' and b['slots']==6
 assert b['learning_measurement_separation'] and b['common_measurement_annotations_sha256']==b['protected_learning_signal_sha256'] and b['control_learning_signal_sha256']!=b['protected_learning_signal_sha256']
 assert not any(b[x] for x in ('model_load_authorized','optimizer_creation_authorized','training_authorized','inference_authorized','historical_holdouts_allowed','parent_selection_authority','promotion','release'))
 for script in ('run_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1.py --preflight-only','run_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1.py --fixture-only','preflight_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1.py','smoke_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1.py'):
  subprocess.run([sys.executable,*[str(ROOT/'scripts'/x) if i==0 else x for i,x in enumerate(script.split())]],cwd=ROOT,check=True,capture_output=True,text=True)
 worker=(ROOT/'scripts/train_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1.py').read_text('utf-8'); assert 'learning_mapping' in worker and 'measurement token drift' in worker and 'T1S0_REPLAY_PROTECTED_REAL_RUN_AUTHORIZED' in worker
 print(json.dumps({'status':'PASS','blockers':0,'runtime_boundary_identity':b['runtime_boundary_identity'],'slots':6,'learning_measurement_separation':True,'model_loaded':False,'optimizer_created':False,'training_performed':False,'inference_performed':False},sort_keys=True))
if __name__=='__main__': main()
