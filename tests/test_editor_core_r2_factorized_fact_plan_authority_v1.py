import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).parents[1]
def test_authority_audit_fixture_only():
 r=subprocess.run([sys.executable,"-B",str(ROOT/"scripts/audit_editor_core_r2_factorized_fact_plan_authority_v1.py")],capture_output=True,text=True,check=True); d=json.loads(r.stdout); assert d["status"]=="PASS" and d["blockers"]==0 and not d["model_loaded"]
def test_authority_identity_and_slots():
 subprocess.run([sys.executable,"-B",str(ROOT/"scripts/build_editor_core_r2_factorized_fact_plan_authority_v1.py")],check=True,capture_output=True); d=json.loads((ROOT/"docs/artifacts/editor-core-r2-factorized-fact-plan-execution-authority-v1.json").read_text()); assert len(d["slots"])==12 and not d["retry_authorized"] and d["stop_on_first_failure"]
