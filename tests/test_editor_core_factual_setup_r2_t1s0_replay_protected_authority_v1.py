import importlib.util,json,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).parents[1]; ART=ROOT/'docs'/'artifacts'; P='editor-core-factual-setup-r2-t1s0-replay-protected-v1'
def load():
 p=ROOT/'scripts/supervise_editor_core_factual_setup_r2_t1s0_replay_protected_v1.py'; s=importlib.util.spec_from_file_location('sup',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
def test_authority_and_supervisor_audit_pass():
 for args in ([str(ROOT/'scripts/audit_editor_core_factual_setup_r2_t1s0_replay_protected_authority_v1.py')],[str(ROOT/'scripts/supervise_editor_core_factual_setup_r2_t1s0_replay_protected_v1.py'),'--audit-only']):
  r=subprocess.run([sys.executable,*args],cwd=ROOT,check=True,capture_output=True,text=True); assert json.loads(r.stdout)['status'].startswith('PASS')
def test_mutated_authority_fails_closed():
 m=load(); value=json.loads((ART/f'{P}-execution-authority.json').read_text('utf-8')); value['slots'][0]['optimizer_steps']=10
 with pytest.raises(ValueError): m.validate_authority(value)
def test_real_execution_is_unreachable():
 route=ROOT/'scripts/supervise_editor_core_factual_setup_r2_t1s0_replay_protected_v1.py'; assert subprocess.run([sys.executable,str(route)],cwd=ROOT,capture_output=True).returncode!=0
def test_six_unique_slots_no_retry_exact_steps():
 a=json.loads((ART/f'{P}-execution-authority.json').read_text('utf-8')); assert len({x['slot_id'] for x in a['slots']})==6 and all(x['optimizer_steps']==9 and x['run_limit']==1 and not x['retry_allowed'] for x in a['slots'])
