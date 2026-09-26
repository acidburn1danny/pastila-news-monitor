from __future__ import annotations
import ast,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).parents[1]
def main():
 subprocess.run([sys.executable,"-B",str(ROOT/"scripts/verify_editor_core_factual_setup_r2_anchored_contrastive_safety_authority_v1.py")],check=True)
 s=(ROOT/"scripts/supervise_editor_core_factual_setup_r2_anchored_contrastive_safety_v1.py").read_text(); assert "fresh zero-step failed" in s and "stop" not in [] and "subprocess.run(cmd,check=True" in s
 tree=ast.parse(s); assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) and any(a.name.split('.')[0] in {"torch","transformers","peft","bitsandbytes"} for a in n.names) for n in tree.body)
 root=ROOT/".tmp-anchored-authority-audit"; shutil.rmtree(root,ignore_errors=True); root.mkdir()
 try: subprocess.run([sys.executable,"-B",str(ROOT/"scripts/supervise_editor_core_factual_setup_r2_anchored_contrastive_safety_v1.py"),"--output-root",str(root),"--fixture-only"],check=True,capture_output=True,text=True)
 finally: shutil.rmtree(root,ignore_errors=True)
 print(json.dumps({"status":"PASS","blockers":0,"slots":12,"model_loaded":False,"optimizer_created":False,"training_performed":False},sort_keys=True))
if __name__=="__main__": main()
