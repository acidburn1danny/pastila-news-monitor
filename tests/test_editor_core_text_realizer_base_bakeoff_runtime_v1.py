import importlib.util, sys
from pathlib import Path

ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
def load(name):
 s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_candidate_and_prompt_contract():
 m=load('editor_core_text_realizer_base_bakeoff_runtime_v1')
 assert m.CANDIDATES==('C0_R2_MINISTRAL','C1_QWEN3_8B','C2_QWEN25_7B')
 ledger={'case_id':'x','request':'r','atoms':[{'atom_id':'a','quote':'q'}],'realization_contract':{'allowed_atom_ids':['a']}}
 assert 'maximum 2–3' in m.prompt_for(ledger)[1]['content']
def test_preflight_constants():
 m=load('preflight_editor_core_text_realizer_base_bakeoff_runtime_v1')
 assert len(m.AUTH)==64 and len(m.PROGRAM)==64 and len(m.R2)==64
