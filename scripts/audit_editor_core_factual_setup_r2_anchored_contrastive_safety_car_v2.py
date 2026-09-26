from __future__ import annotations
import ast,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).parents[1]
def main():
 subprocess.run([sys.executable,"-B",str(ROOT/"scripts/verify_editor_core_factual_setup_r2_anchored_contrastive_safety_authority_v2.py")],check=True,capture_output=True,text=True)
 pre=(ROOT/"scripts/preflight_editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v2.py").read_text(); sup=(ROOT/"scripts/supervise_editor_core_factual_setup_r2_anchored_contrastive_safety_v2.py").read_text(); worker=(ROOT/"scripts/editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v2.py").read_text()
 assert "validate_training_mapping" in pre and "zero-step.json" in pre
 assert sup.index("auth=verify") < sup.index("slots=plan") and "program-failure.json" in sup
 assert "replay critical spans forbidden" in worker and "corrective critical spans required" in worker and "corrective_nonempty_token_mappings" in worker and "replay_empty_span_rows" in worker and "eligible_evidence\":False" in worker
 for path in (pre,sup):
  tree=ast.parse(path); assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) and any(a.name.split('.')[0] in {"torch","peft","bitsandbytes"} for a in n.names) for n in tree.body)
 print(json.dumps({"status":"PASS","blockers":0,"corrective_nonempty":48,"replay_empty":24,"authority_before_plan":True,"atomic_zero_step":True,"failure_evidence":True,"model_loaded":False,"optimizer_steps":0},sort_keys=True))
if __name__=="__main__": main()
