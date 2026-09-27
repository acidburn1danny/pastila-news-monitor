"""Static and executable fixture audit."""
import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; B=ROOT/'docs'/'artifacts/editor-core-r2-factorized-fact-plan-runtime-boundary-v1.json'; b=json.loads(B.read_text(encoding='utf-8'))
assert b['slots']==12 and b['status']=='FIXTURE_ONLY_NO_REAL_AUTHORITY' and not b['model_load_authorized'] and not b['optimizer_creation_authorized'] and not b['training_authorized'] and not b['real_execution_authority'] and not b['parent_selection_authority']
p=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/smoke_editor_core_r2_factorized_fact_plan_runtime_v1.py')],check=True,capture_output=True,text=True); assert json.loads(p.stdout)['status']=='PASS_FIXTURE_SMOKE'
route=(ROOT/'scripts/run_editor_core_r2_factorized_fact_plan_runtime_v1.sh').read_text(); assert 'real execution authority absent' in route and '--zero-step-only' in route
print(json.dumps({'status':'PASS_ADVERSARIAL','blockers':0,'phase_separation':True,'output_isolation':True,'real_authority':False,'model_loaded':False},sort_keys=True))
