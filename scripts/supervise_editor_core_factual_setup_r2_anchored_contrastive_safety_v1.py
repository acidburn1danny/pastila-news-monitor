from __future__ import annotations
import argparse,json,os,subprocess,sys
from pathlib import Path
from verify_editor_core_factual_setup_r2_anchored_contrastive_safety_authority_v1 import verify
ARMS=("P0_POSITIVE_ONLY_K0_NO_KL","P1_CONTRASTIVE_K0_NO_KL","P0_POSITIVE_ONLY_K1_R2_KL","P1_CONTRASTIVE_K1_R2_KL"); SEEDS=(161803,271828,314159)
def plan(root):
 if root.is_symlink() or not root.is_dir() or any(root.iterdir()): raise ValueError("program output root must be distinct and empty")
 out=[]
 for arm in ARMS:
  for seed in SEEDS:
   p=root/f"{arm.lower()}__seed_{seed}"; p.mkdir(); out.append((arm,seed,p))
 return out
def main():
 p=argparse.ArgumentParser(); p.add_argument("--output-root",type=Path,required=True); p.add_argument("--fixture-only",action="store_true"); p.add_argument("--execute-authorized",action="store_true")
 for n in ("model","parent","corpus","annotations","pairs","retention","development","preflight","worker"): p.add_argument(f"--{n}",type=Path)
 a=p.parse_args(); slots=plan(a.output_root); auth=verify()
 if a.fixture_only: print(json.dumps({"status":"PASS_FIXTURE_ONLY","slots":len(slots),"distinct_outputs":len({str(x[2]) for x in slots}),"model_loaded":False,"optimizer_created":False,"optimizer_steps":0})); return
 if not a.execute_authorized or os.environ.get("ANCHORED_CONTRASTIVE_PROGRAM_OWNER_AUTHORIZED")!="1": raise SystemExit("separate owner authorization required")
 if not all(getattr(a,n) for n in ("model","parent","corpus","annotations","pairs","retention","development","preflight","worker")): raise SystemExit("missing bound input")
 zero_root=a.output_root/".zero-step"; zero_root.mkdir(); terminals=[]
 for arm,seed,out in slots:
  verify(arm,seed,True)
  z=zero_root/out.name; z.mkdir()
  cmd=[sys.executable,"-B",str(a.preflight),"--model",str(a.model),"--pairs",str(a.pairs),"--retention",str(a.retention),"--output",str(z)]
  receipt=json.loads(subprocess.run(cmd,check=True,text=True,capture_output=True).stdout)
  if receipt.get("status")!="PASS_ZERO_STEP" or receipt.get("model_loaded") or receipt.get("optimizer_steps")!=0: raise ValueError("fresh zero-step failed")
  env={**os.environ,"ANCHORED_CONTRASTIVE_REAL_RUN_AUTHORIZED":"1"}
  cmd=[sys.executable,"-B",str(a.worker),"--model",str(a.model),"--parent",str(a.parent),"--corpus",str(a.corpus),"--annotations",str(a.annotations),"--pairs",str(a.pairs),"--retention",str(a.retention),"--development",str(a.development),"--output",str(out),"--arm",arm,"--seed",str(seed),"--execute-authorized"]
  subprocess.run(cmd,check=True,env=env); terminal=json.loads((out/"terminal.json").read_text()); assert terminal["optimizer_steps"]==9 and terminal["slot_id"]==f"{arm}__seed_{seed}"; terminals.append(terminal)
 result={"status":"PASS_12_TERMINAL_SLOTS","authority_identity":auth["authority_identity"],"slots_completed":12,"optimizer_steps_total":108,"terminals":terminals}; (a.output_root/"program-terminal.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n"); print(json.dumps(result,sort_keys=True))
if __name__=="__main__": main()
