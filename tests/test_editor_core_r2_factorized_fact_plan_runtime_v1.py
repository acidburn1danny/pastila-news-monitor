import hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).parents[1]
def test_boundary_build_and_hashes():
 subprocess.run([sys.executable,'-B','scripts/build_editor_core_r2_factorized_fact_plan_runtime_boundary_v1.py'],check=True)
 b=json.loads(Path('docs/artifacts/editor-core-r2-factorized-fact-plan-runtime-boundary-v1.json').read_text())
 assert b['slots']==12 and b['source_commit']=='11c39a158e3edd98418ebbc15e472a1c2388f43a'
 assert b['files']=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in b['files']}
 assert not any(b[k] for k in ('model_load_authorized','optimizer_creation_authorized','training_authorized','real_execution_authority','parent_selection_authority'))
def test_four_phase_fixture_smoke():
 p=subprocess.run([sys.executable,'-B','scripts/smoke_editor_core_r2_factorized_fact_plan_runtime_v1.py'],check=True,capture_output=True,text=True); assert json.loads(p.stdout)['interventions']==4
def test_route_refuses_non_zero_step():
 s=Path('scripts/run_editor_core_r2_factorized_fact_plan_runtime_v1.sh').read_text(); assert 'exit 64' in s and '--zero-step-only' in s
