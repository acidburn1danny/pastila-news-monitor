from __future__ import annotations
import ast,hashlib,importlib.util,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-factual-setup-r2-causal-diagnostic-v1'
WORKER=ROOT/'scripts'/'execute_editor_core_factual_setup_r2_causal_diagnostic_v1.py'; FIXTURE=ROOT/'tests'/'fixtures'/'editor_core_factual_setup_r2_causal_diagnostic_v1'/'fixture.json'
def req(v,m):
 if not v: raise ValueError(m)
def canonical(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def load(n): return json.loads((ART/f'{P}-{n}').read_text('utf-8'))
def rows(path): return [json.loads(x) for x in path.read_text('utf-8').splitlines() if x]
def module():
 spec=importlib.util.spec_from_file_location('diag_worker_audit',WORKER); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod); return mod
def main():
 boundary=load('execution-boundary.json'); ident=boundary.pop('boundary_identity'); req(hashlib.sha256(canonical(boundary)).hexdigest()==ident,'boundary identity')
 protocol,pack,recipes,evaluation=(load(n) for n in ('protocol.json','manifest.json','recipes.json','evaluation.json'))
 req(boundary['published_source_commit']=='e4858a37f98890618d4e59579bf074043a3c81b7','source commit')
 req(subprocess.check_output(['git','rev-parse',boundary['published_source_commit']+'^{tree}'],text=True).strip()==boundary['published_source_tree'],'source tree')
 for key,value in [('protocol_identity',protocol['protocol_identity']),('pack_identity',pack['pack_identity']),('recipes_identity',recipes['recipes_identity']),('evaluation_identity',evaluation['evaluation_identity'])]: req(boundary[key]==value,key)
 req(boundary['worker_sha256']==hashlib.sha256(WORKER.read_bytes()).hexdigest(),'worker hash'); req(boundary['fixture_sha256']==hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),'fixture hash')
 req(boundary['arms']==[x['arm_id'] for x in protocol['arms']] and boundary['seeds']==protocol['seeds'] and boundary['slots']==12,'slot binding')
 req(boundary['parent']=='R2_STEP_9' and boundary['parent_adapter_identity']==protocol['parent_adapter_identity'] and boundary['parent_checkpoint_identity']==protocol['parent_checkpoint_identity'],'parent binding')
 req(not any(boundary[k] for k in ('model_load_authorized','optimizer_creation_authorized','training_authorized','inference_authorized','parent_selection_authority','promotion','release')) and boundary['optimizer_steps_authorized']==0,'authority boundary')
 tree=ast.parse(WORKER.read_text('utf-8')); imports={a.name.split('.')[0] for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) for a in n.names}; req(not imports.intersection({'torch','transformers','peft','bitsandbytes'}),'top-level ML import')
 worker=module(); source=rows(ART/'editor-core-factual-setup-corrective-v1-training.jsonl'); annotations=rows(ART/f'{P}-challenger-signal.jsonl'); mapped=0
 for row,annotation in zip(source,annotations,strict=True):
  req(row['example_id']==annotation['example_id'],'annotation order')
  if annotation['critical_spans']:
   mapped+=len(worker.validate_and_map_annotation(row['messages'][-1]['content'],annotation))
 req(mapped>48,'critical mapping inventory')
 orders={seed:worker.deterministic_order(72,seed) for seed in worker.SEEDS}; req(len({hashlib.sha256(canonical(v)).hexdigest() for v in orders.values()})==3,'seed order uniqueness')
 req(all(worker.deterministic_order(72,seed)==orders[seed] for _arm in worker.ARMS for seed in worker.SEEDS),'matched row order')
 req(worker.stop_decision({'material_safety_regressions':1})=='STOP' and worker.stop_decision({'material_replay_regressions':1})=='STOP' and worker.stop_decision({'contamination':True})=='STOP','stop rules')
 print(json.dumps({'status':'PASS','blockers':0,'boundary_identity':ident,'arms':4,'slots':12,'mapped_critical_spans':mapped,'matched_seed_orders':3,'model_loaded':False,'optimizer_created':False,'optimizer_steps':0,'training_performed':False,'inference_performed':False,'real_runs_authorized':False},sort_keys=True))
if __name__=='__main__':
 try: main()
 except Exception as exc:
  print(json.dumps({'status':'BLOCKED','error':str(exc)},sort_keys=True),file=sys.stderr); raise
