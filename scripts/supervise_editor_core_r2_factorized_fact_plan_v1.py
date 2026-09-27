from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
from verify_editor_core_r2_factorized_fact_plan_authority_v1 import verify
INTERVENTIONS=("I0_ONE_PASS_R2","I1_ORACLE_PLAN_SCORE","I2_ORACLE_PLAN_TO_R2_SETUP","I3_R2_PLAN_TO_R2_SETUP"); SEEDS=(161803,271828,314159)
def main():
 p=argparse.ArgumentParser(); p.add_argument("--output-root",type=Path,required=True); p.add_argument("--fixture-only",action="store_true"); p.add_argument("--execute-authorized",action="store_true"); p.add_argument("--runtime-python",type=Path); p.add_argument("--model",type=Path); p.add_argument("--tokenizer",type=Path); p.add_argument("--parent",type=Path); p.add_argument("--artifacts",type=Path); p.add_argument("--preflight",type=Path); p.add_argument("--worker",type=Path)
 a=p.parse_args(); auth=verify()
 planned=[f"{intervention.lower()}__seed_{seed}" for intervention in INTERVENTIONS for seed in SEEDS]
 if a.fixture_only:
  assert len(planned)==len(set(planned))==12
  print(json.dumps({"status":"PASS_FIXTURE_12","authority_identity":auth["authority_identity"],"slots":12,"distinct_outputs":12,"model_loaded":False,"optimizer_created":False,"training_performed":False},sort_keys=True)); return
 if a.output_root.exists() and (a.output_root.is_symlink() or any(a.output_root.iterdir())): raise ValueError("program output root")
 if not a.execute_authorized or os.environ.get("FACTORIZED_FACT_PLAN_PROGRAM_AUTHORIZED")!="1": raise SystemExit("separate owner authorization required")
 if not a.runtime_python or hashlib.sha256(a.runtime_python.read_bytes()).hexdigest()!="e50d468e8b0adfb05733f5b87b3cff34829c4a8c1aea50c865aa8bdfe4bb150f": raise SystemExit("runtime python identity")
 a.output_root.mkdir(parents=True,exist_ok=True); slots=[]
 for intervention in INTERVENTIONS:
  for seed in SEEDS:
   verify(intervention,seed); slot=a.output_root/f"{intervention.lower()}__seed_{seed}"
   if not all((a.model,a.tokenizer,a.parent,a.artifacts,a.preflight,a.worker)): raise SystemExit("missing bound input")
   zero=a.output_root/f".zero-step-{slot.name}"
   try:
    subprocess.run([str(a.runtime_python),"-B",str(a.preflight),"--artifact-root",str(a.artifacts),"--tokenizer-dir",str(a.tokenizer),"--parent-adapter",str(a.parent),"--output",str(zero)],check=True)
    receipt=json.loads((zero/"zero-step.json").read_text()); assert receipt["status"]=="PASS_12_ZERO_STEP" and not receipt["model_loaded"]
    slot.mkdir(); env={**os.environ,"FACTORIZED_FACT_PLAN_SLOT_AUTHORIZED":"1"}; subprocess.run([str(a.runtime_python),"-B",str(a.worker),"--intervention",intervention,"--seed",str(seed),"--output",str(slot),"--model",str(a.model),"--tokenizer",str(a.tokenizer),"--parent",str(a.parent),"--artifacts",str(a.artifacts),"--execute-authorized"],check=True,env=env)
    terminal=json.loads((slot/"terminal.json").read_text()); assert terminal["status"]=="PASS_TERMINAL"; slots.append(slot.name)
   except Exception as exc:
    tmp=a.output_root/"failure.json.tmp"; tmp.write_text(json.dumps({"status":"TERMINAL_FAILURE","slot_id":f"{intervention}__seed_{seed}","phase":"ZERO_STEP" if not zero.joinpath("zero-step.json").exists() else "SLOT_EXECUTION","error_type":type(exc).__name__},sort_keys=True,indent=2)+"\n"); tmp.replace(a.output_root/"failure.json"); raise
 print(json.dumps({"status":"PASS_TERMINAL_12","authority_identity":auth["authority_identity"],"slots":len(slots),"model_loaded":True,"optimizer_created":False,"training_performed":False},sort_keys=True))
if __name__=="__main__": main()
