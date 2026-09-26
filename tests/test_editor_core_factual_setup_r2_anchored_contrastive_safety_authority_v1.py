import json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).parents[1]
def test_authority_and_adversarial_fixture():
 r=subprocess.run([sys.executable,"-B",str(ROOT/"scripts/audit_editor_core_factual_setup_r2_anchored_contrastive_safety_authority_v1.py")],text=True,capture_output=True,check=True); assert json.loads(r.stdout.splitlines()[-1])["status"]=="PASS"
def test_real_execution_requires_separate_authorization():
 root=ROOT/".tmp-anchored-authority-negative"; shutil.rmtree(root,ignore_errors=True); root.mkdir()
 try:
  r=subprocess.run([sys.executable,"-B",str(ROOT/"scripts/supervise_editor_core_factual_setup_r2_anchored_contrastive_safety_v1.py"),"--output-root",str(root)],text=True,capture_output=True); assert r.returncode!=0 and "separate owner authorization required" in r.stderr
 finally: shutil.rmtree(root,ignore_errors=True)
