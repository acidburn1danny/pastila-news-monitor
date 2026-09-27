import json,subprocess,sys
from pathlib import Path
R=Path(__file__).parents[1]
def test_frozen_closure_audit():
 p=subprocess.run([sys.executable,'-B',str(R/'scripts/audit_editor_core_text_realizer_base_bakeoff_frozen_v1.py')],cwd=R,text=True,capture_output=True,check=True)
 assert json.loads(p.stdout)['status']=='PASS_FROZEN_CLOSURE'
