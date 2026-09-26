from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path
from verify_editor_core_factual_setup_r2_anchored_contrastive_safety_continuation_v1 import verify

SLOTS=(("P0_POSITIVE_ONLY_K1_R2_KL",314159),("P1_CONTRASTIVE_K1_R2_KL",161803),("P1_CONTRASTIVE_K1_R2_KL",271828),("P1_CONTRASTIVE_K1_R2_KL",314159))
def sha(p:Path)->str: return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(); p.add_argument("--predecessor-root",type=Path,required=True); p.add_argument("--output-root",type=Path,required=True); p.add_argument("--execute-authorized",action="store_true")
 for n in ("model","parent","corpus","annotations","pairs","retention","development","preflight","worker"): p.add_argument(f"--{n}",type=Path,required=True)
 a=p.parse_args(); auth=verify(published=True)
 if not a.execute_authorized or os.environ.get("ANCHORED_CONTRASTIVE_CONTINUATION_OWNER_AUTHORIZED")!="1": raise SystemExit("continuation authorization required")
 if a.output_root.is_symlink() or not a.output_root.is_dir() or any(a.output_root.iterdir()): raise ValueError("continuation root must be distinct and empty")
 for rel,digest in auth["predecessor_receipts"].items():
  q=a.predecessor_root/rel
  if not q.is_file() or sha(q)!=digest: raise ValueError(f"predecessor receipt mismatch: {rel}")
 outputs=[]
 for arm,seed in SLOTS:
  verify(arm,seed,True); sid=f"{arm}__seed_{seed}"; out=a.output_root/f"{arm.lower()}__seed_{seed}"; zero=a.output_root/".zero-step"/out.name
  out.mkdir(parents=True); zero.mkdir(parents=True)
  zcmd=[sys.executable,"-B",str(a.preflight),"--model",str(a.model),"--corpus",str(a.corpus),"--annotations",str(a.annotations),"--pairs",str(a.pairs),"--retention",str(a.retention),"--output",str(zero)]
  receipt=json.loads(subprocess.run(zcmd,check=True,text=True,capture_output=True).stdout)
  if receipt.get("status")!="PASS_ZERO_STEP" or receipt.get("optimizer_steps")!=0 or receipt.get("model_loaded"): raise ValueError("fresh zero-step failed")
  env={**os.environ,"ANCHORED_CONTRASTIVE_REAL_RUN_AUTHORIZED":"1"}
  cmd=[sys.executable,"-B",str(a.worker),"--model",str(a.model),"--parent",str(a.parent),"--corpus",str(a.corpus),"--annotations",str(a.annotations),"--pairs",str(a.pairs),"--retention",str(a.retention),"--development",str(a.development),"--output",str(out),"--arm",arm,"--seed",str(seed),"--execute-authorized"]
  subprocess.run(cmd,check=True,env=env)
  terminal=json.loads((out/"terminal.json").read_text()); assert terminal["slot_id"]==sid and terminal["optimizer_steps"]==9; outputs.append(terminal)
 result={"status":"PASS_CONTINUATION_12_OF_12","authority_identity":auth["authority_identity"],"predecessor_slots":8,"continuation_slots":4,"optimizer_steps_total":108,"continuation_terminals":outputs}
 (a.output_root/"continuation-terminal.json").write_text(json.dumps(result,sort_keys=True,indent=2)+"\n"); print(json.dumps(result,sort_keys=True))
if __name__=="__main__": main()
