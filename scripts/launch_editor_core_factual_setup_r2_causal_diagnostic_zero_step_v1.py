from __future__ import annotations
import hashlib,json,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-factual-setup-r2-causal-diagnostic-v1'
def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def load(n): return json.loads((ART/f'{P}-{n}').read_text('utf-8'))
def run(output_root: Path|None=None):
 boundary=load('execution-boundary.json'); ident=boundary.pop('boundary_identity');
 if hashlib.sha256(canonical(boundary)).hexdigest()!=ident: raise ValueError('boundary identity mismatch')
 bindings={'protocol_identity':load('protocol.json')['protocol_identity'],'pack_identity':load('manifest.json')['pack_identity'],'recipes_identity':load('recipes.json')['recipes_identity'],'evaluation_identity':load('evaluation.json')['evaluation_identity']}
 if any(boundary[k]!=v for k,v in bindings.items()): raise ValueError('published binding mismatch')
 if boundary['status']!='FIXTURE_ONLY_REAL_RUNS_NOT_AUTHORIZED' or any(boundary[k] for k in ('model_load_authorized','optimizer_creation_authorized','training_authorized','inference_authorized','parent_selection_authority')) or boundary['optimizer_steps_authorized']!=0: raise ValueError('execution authority drift')
 if len(boundary['arms'])!=4 or boundary['slots']!=12 or boundary['seeds']!=[161803,271828,314159]: raise ValueError('slot authority mismatch')
 if output_root is not None and (output_root.is_symlink() or not output_root.is_dir() or any(output_root.iterdir())): raise ValueError('zero-step output root must be distinct and empty')
 core={'schema':'editor-factual-setup-r2-causal-diagnostic-zero-step','schema_version':1,'status':'PASS_ZERO_STEP_FIXTURE_ONLY','boundary_identity':ident,**bindings,'parent':'R2_STEP_9','arms':4,'slots':12,'output_root_empty':True,'model_loaded':False,'optimizer_created':False,'optimizer_steps':0,'training_performed':False,'inference_performed':False,'real_runs_authorized':False}
 return {**core,'receipt_identity':hashlib.sha256(canonical(core)).hexdigest()}
if __name__=='__main__': print(json.dumps(run(),sort_keys=True,separators=(',',':')))
