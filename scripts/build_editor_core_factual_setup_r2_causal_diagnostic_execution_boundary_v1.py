from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'
P='editor-core-factual-setup-r2-causal-diagnostic-v1'
def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def load(n): return json.loads((ART/f'{P}-{n}').read_text('utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 protocol,pack,recipes,evaluation=(load(n) for n in ('protocol.json','manifest.json','recipes.json','evaluation.json'))
 worker=ROOT/'scripts'/'execute_editor_core_factual_setup_r2_causal_diagnostic_v1.py'; fixture=ROOT/'tests'/'fixtures'/'editor_core_factual_setup_r2_causal_diagnostic_v1'/'fixture.json'
 core={'schema':'editor-factual-setup-r2-causal-diagnostic-execution-boundary','schema_version':1,'status':'FIXTURE_ONLY_REAL_RUNS_NOT_AUTHORIZED','published_source_commit':'e4858a37f98890618d4e59579bf074043a3c81b7','published_source_tree':'7a570d4457ddbb7288e42579911d36afdbd359ea','protocol_identity':protocol['protocol_identity'],'pack_identity':pack['pack_identity'],'recipes_identity':recipes['recipes_identity'],'evaluation_identity':evaluation['evaluation_identity'],'parent':'R2_STEP_9','parent_adapter_identity':protocol['parent_adapter_identity'],'parent_checkpoint_identity':protocol['parent_checkpoint_identity'],'arms':[x['arm_id'] for x in protocol['arms']],'seeds':protocol['seeds'],'slots':12,'worker_sha256':sha(worker),'fixture_sha256':sha(fixture),'measurements':['BYTE_SPAN_TO_TOKEN_MAPPING','FULL_TARGET_NLL','CRITICAL_SPAN_NLL','ADAPTER_DELTA','TRAIN_ACQUISITION','REPLAY_RETENTION','DEVELOPMENT_EVALUATION'],'output_isolation':'DISTINCT_EMPTY_ROOT_PER_ARM_SEED','zero_step_required':True,'stop_rules':protocol['stop_rules'],'model_load_authorized':False,'optimizer_creation_authorized':False,'optimizer_steps_authorized':0,'training_authorized':False,'inference_authorized':False,'parent_selection_authority':False,'promotion':False,'release':False}
 boundary={**core,'boundary_identity':hashlib.sha256(canonical(core)).hexdigest()}
 (ART/f'{P}-execution-boundary.json').write_bytes((json.dumps(boundary,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode())
if __name__=='__main__': main()
