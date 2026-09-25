from __future__ import annotations
import importlib.util,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod); return mod
def run():
 worker=load(ROOT/'scripts'/'execute_editor_core_factual_setup_r2_causal_diagnostic_v1.py','diag_worker')
 zero=load(ROOT/'scripts'/'launch_editor_core_factual_setup_r2_causal_diagnostic_zero_step_v1.py','diag_zero')
 fixture=json.loads((ROOT/'tests'/'fixtures'/'editor_core_factual_setup_r2_causal_diagnostic_v1'/'fixture.json').read_text('utf-8'))
 root=ROOT/'.editor-core-causal-diagnostic-fixture-output'
 if root.exists(): raise ValueError('fixture output collision')
 root.mkdir()
 try:
  pre=zero.run(root); result=worker.fixture_run(fixture,root)
 finally:
  shutil.rmtree(root)
 return {'status':'PASS_FIXTURE_ONLY','zero_step_identity':pre['receipt_identity'],'fixture_receipt_identity':result['receipt_identity'],'slots':result['slots'],'arms':result['arms'],'model_loaded':False,'optimizer_created':False,'optimizer_steps':0,'training_performed':False,'inference_performed':False}
if __name__=='__main__': print(json.dumps(run(),sort_keys=True,separators=(',',':')))
