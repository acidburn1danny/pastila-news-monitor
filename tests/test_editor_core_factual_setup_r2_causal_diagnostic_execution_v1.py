import ast,importlib.util,json,shutil,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
WORKER=ROOT/'scripts'/'execute_editor_core_factual_setup_r2_causal_diagnostic_v1.py'; SMOKE=ROOT/'scripts'/'smoke_editor_core_factual_setup_r2_causal_diagnostic_execution_v1.py'; AUDIT=ROOT/'scripts'/'audit_editor_core_factual_setup_r2_causal_diagnostic_execution_v1.py'; FIXTURE=ROOT/'tests'/'fixtures'/'editor_core_factual_setup_r2_causal_diagnostic_v1'/'fixture.json'
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod); return mod
def test_smoke_and_audit_are_zero_real_execution():
 smoke=load(SMOKE,'diag_smoke').run(); assert smoke['status']=='PASS_FIXTURE_ONLY' and smoke['slots']==12 and smoke['arms']==4
 assert not any(smoke[k] for k in ('model_loaded','optimizer_created','training_performed','inference_performed')); assert smoke['optimizer_steps']==0
 result=subprocess.run([sys.executable,str(AUDIT)],check=True,text=True,capture_output=True); receipt=json.loads(result.stdout); assert receipt['status']=='PASS' and receipt['blockers']==0 and receipt['mapped_critical_spans']>48
def test_worker_has_no_ml_runtime_or_real_execution_entrypoint():
 tree=ast.parse(WORKER.read_text('utf-8')); imports={a.name.split('.')[0] for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom)) for a in n.names}; assert not imports.intersection({'torch','transformers','peft','bitsandbytes'})
 assert 'optimizer.step(' not in WORKER.read_text('utf-8') and 'from_pretrained(' not in WORKER.read_text('utf-8')
def test_utf8_span_mapping_and_partial_token_fail_closed():
 worker=load(WORKER,'diag_map'); content='AăB'; span=worker.char_span_to_byte_span(content,1,2); assert span==(1,3); assert worker.map_byte_span_to_tokens(content,span,worker.fixture_tokenizer_offsets(content))==[1]
 with pytest.raises(ValueError): worker.map_byte_span_to_tokens(content,(2,3),worker.fixture_tokenizer_offsets(content))
def test_annotation_escape_and_output_collision_fail_closed():
 worker=load(WORKER,'diag_negative'); fixture=json.loads(FIXTURE.read_text('utf-8')); fixture['annotation']['critical_spans'][0]['start']=0
 with pytest.raises(ValueError): worker.validate_and_map_annotation(fixture['assistant_content'],fixture['annotation'])
 occupied=ROOT/'.diag-occupied-output'; shutil.rmtree(occupied,ignore_errors=True); occupied.mkdir(); (occupied/'x').write_text('x')
 try:
  with pytest.raises(ValueError): worker.fixture_run(json.loads(FIXTURE.read_text('utf-8')),occupied)
 finally: shutil.rmtree(occupied)
def test_arm_seed_crossover_and_stop_rules_fail_closed():
 worker=load(WORKER,'diag_cross'); fixture=json.loads(FIXTURE.read_text('utf-8')); fixture['slots'][1]['output_subdir']=fixture['slots'][0]['output_subdir']
 root=ROOT/'.diag-crossover-output'; shutil.rmtree(root,ignore_errors=True); root.mkdir()
 try:
  with pytest.raises(ValueError): worker.fixture_run(fixture,root)
 finally: shutil.rmtree(root)
 assert worker.stop_decision({'identity_drift':True})=='STOP'; assert worker.stop_decision({'all_arms_train_acquisition_failed':True})=='STOP_AND_REVIEW_LORA_OR_OPTIMIZATION'; assert worker.stop_decision({'replicated_development_gain':True})=='CONTINUE_CAUSAL_INTERPRETATION_ONLY'
