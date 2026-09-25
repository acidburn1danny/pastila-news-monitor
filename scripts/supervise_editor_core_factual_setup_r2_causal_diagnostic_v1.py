from __future__ import annotations
import argparse,json,os,subprocess
from pathlib import Path
from verify_editor_core_factual_setup_r2_causal_diagnostic_execution_authority_v1 import verify
ARMS=("T0_CONTROL_S0_CONTROL","T0_CONTROL_S1_HIGHER_PLASTICITY","T1_CONTRACT_WEIGHTED_S0_CONTROL","T1_CONTRACT_WEIGHTED_S1_HIGHER_PLASTICITY"); SEEDS=(161803,271828,314159)
def plan(root:Path):
    if root.is_symlink() or not root.is_dir() or any(root.iterdir()): raise ValueError("supervisor root must be distinct and empty")
    slots=[]
    for arm in ARMS:
      for seed in SEEDS:
        out=root/f"{arm.lower()}__seed_{seed}"; out.mkdir(); slots.append({"arm":arm,"seed":seed,"output":str(out),"state":"PENDING_ZERO_STEP"})
    return slots
def fixture(root:Path):
    slots=plan(root); return {"status":"PASS_FIXTURE_ONLY","slots":len(slots),"distinct_outputs":len({s['output'] for s in slots}),"model_loaded":False,"optimizer_steps":0,"real_runs":0}
def preflight_all(root:Path, route:Path, rootfs:Path, model:Path, corpus:Path, challenger:Path, preflight:Path, worker:Path, published:bool):
    slots=plan(root); receipts=[]
    for item in slots:
        authority=verify(item["arm"],item["seed"],published)
        command=["bash",str(route),str(rootfs),str(model),str(corpus),str(challenger),item["output"],str(preflight),str(worker),"--preflight-only"]
        result=subprocess.run(command,check=True,text=True,capture_output=True); receipt=json.loads(result.stdout)
        if receipt.get("status")!="PASS_ZERO_STEP" or receipt.get("model_loaded") or receipt.get("optimizer_steps")!=0: raise ValueError("slot zero-step failure")
        receipts.append({"slot_id":authority["slot"]["slot_id"],"preflight_identity":receipt["preflight_identity"],"mapping_identity":receipt["mapping_identity"]})
    return {"status":"PASS_12_SLOT_ZERO_STEP","slots":receipts,"model_loaded":False,"optimizer_steps":0,"real_runs":0}
def main():
    p=argparse.ArgumentParser(); p.add_argument("--output-root",type=Path,required=True); p.add_argument("--fixture-only",action="store_true"); p.add_argument("--preflight-all",action="store_true"); p.add_argument("--local-authority",action="store_true")
    for name in ("route","rootfs","model","corpus","challenger","preflight","worker"): p.add_argument(f"--{name}",type=Path)
    a=p.parse_args()
    if a.fixture_only: result=fixture(a.output_root)
    elif a.preflight_all and all(getattr(a,n) for n in ("route","rootfs","model","corpus","challenger","preflight","worker")): result=preflight_all(a.output_root,a.route,a.rootfs,a.model,a.corpus,a.challenger,a.preflight,a.worker,not a.local_authority)
    else: raise SystemExit("real runs require a separate owner authorization invocation")
    print(json.dumps(result,sort_keys=True))
if __name__=="__main__": main()
