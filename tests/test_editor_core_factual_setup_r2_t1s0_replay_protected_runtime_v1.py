import importlib.util,json,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).parents[1]
def load():
 p=ROOT/'scripts/train_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1.py'; s=importlib.util.spec_from_file_location('runtime',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def test_runtime_audit_smoke_and_zero_step():
 for script in ('audit_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1.py','preflight_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1.py','smoke_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1.py'):
  r=subprocess.run([sys.executable,str(ROOT/'scripts'/script)],cwd=ROOT,check=True,capture_output=True,text=True); assert json.loads(r.stdout)['status'].startswith('PASS')
def test_six_slots_same_s0_and_no_unauthorized_real_run():
 m=load(); assert len(m.ARMS)==2 and len(m.SEEDS)==3 and set(m.ARMS.values())=={('T1','5e-7')}
 with pytest.raises(RuntimeError): m.run_slot(*([Path('x')]*7),'T1_S0_EXISTING_CONTROL',161803)
def test_learning_and_measurement_are_separate_in_worker():
 text=(ROOT/'scripts/train_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1.py').read_text('utf-8'); assert 'learning_mapping=real_chat_token_map' in text and 'mapping=real_chat_token_map' in text and 'tokens,start,_,critical_ids=prepared[index]' in text
def test_route_rejects_unsafe_or_ambiguous_mode():
 route=ROOT/'scripts/run_editor_core_factual_setup_r2_t1s0_replay_protected_runtime_v1.py'; assert subprocess.run([sys.executable,str(route)],cwd=ROOT,capture_output=True).returncode!=0; assert subprocess.run([sys.executable,str(route),'--preflight-only','--fixture-only'],cwd=ROOT,capture_output=True).returncode!=0
