import copy,importlib.util,json,subprocess,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).parents[1]
def load():
 p=ROOT/'scripts/editor_core_factual_setup_r2_t1s0_replay_protected_fixture_worker_v1.py'; s=importlib.util.spec_from_file_location('rpw',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
class Tok:
 def __call__(self,text,**kwargs): return {'input_ids':list(range(len(text))),'offset_mapping':[(i,i+1) for i in range(len(text))]}
def test_audit_zero_step_and_smoke():
 for name in ('audit_editor_core_factual_setup_r2_t1s0_replay_protected_boundary_v1.py','zero_step_editor_core_factual_setup_r2_t1s0_replay_protected_v1.py','smoke_editor_core_factual_setup_r2_t1s0_replay_protected_v1.py'):
  r=subprocess.run([sys.executable,str(ROOT/'scripts'/name)],cwd=ROOT,check=True,capture_output=True,text=True); assert json.loads(r.stdout)['status'].startswith('PASS')
def test_slots_orders_mapping_and_isolation():
 m=load(); assert len(m.ARMS)*len(m.SEEDS)==6 and m.row_order(161803)==m.row_order(161803)!=m.row_order(271828)
 a='{"text":"Actor 12 propus."}'; start=a.index('Actor'); span={'field':'text','start':start,'end':start+15,'text':'Actor 12 propus'}; assert m.map_spans(Tok(),a,[span])['mapped_spans'][0]['token_start']==start
 sid=m.slot_id(m.ARMS[0],m.SEEDS[0]); result=m.run_fixture(Tok(),a,[span],sid,m.ARMS[0],m.SEEDS[0]); assert result['publication_order'][-1]=='terminal.json'
 with pytest.raises(ValueError): m.run_fixture(Tok(),a,[span],'shared-output',m.ARMS[0],m.SEEDS[0])
def test_fail_closed_mapping_and_decisions():
 m=load(); a='{"text":"Actor."}'; start=a.index('Actor')
 with pytest.raises(ValueError): m.map_spans(Tok(),a,[{'field':'case_id','start':start,'end':start+5,'text':'Actor'}])
 complete={k:{s:{'targeted_gain':True,'retained':True,'material_regressions':0} for s in m.SEEDS} for k in ('control','protected')}; assert m.decide(complete,complete)=='CONTINUE_RESEARCH'
 bad=copy.deepcopy(complete); bad['protected'][m.SEEDS[0]]['material_regressions']=1
 assert m.decide(complete,bad)=='STOP'
 with pytest.raises(ValueError): m.decide({'control':{}},complete)
def test_no_ml_or_real_authority():
 text=(ROOT/'scripts/editor_core_factual_setup_r2_t1s0_replay_protected_fixture_worker_v1.py').read_text('utf-8'); assert '\nimport torch' not in text and '\nfrom transformers' not in text and 'def run_training' not in text
