import json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).parents[1]
def test_authority_and_car_audit():
 r=subprocess.run([sys.executable,"-B",str(ROOT/"scripts/audit_editor_core_factual_setup_r2_anchored_contrastive_safety_car_v2.py")],check=True,text=True,capture_output=True); assert json.loads(r.stdout)["status"]=="PASS"
def test_fixture_and_authorization_gate():
 root=ROOT/".car-v2-supervisor-test"; root.mkdir(exist_ok=False)
 try:
  cmd=[sys.executable,"-B",str(ROOT/"scripts/supervise_editor_core_factual_setup_r2_anchored_contrastive_safety_v2.py"),"--output-root",str(root),"--fixture-only"]
  assert json.loads(subprocess.run(cmd,check=True,text=True,capture_output=True).stdout)["slots"]==12
 finally:
  import shutil; shutil.rmtree(root)
