"""Fail-closed supervisor for the one authorized 216-slot execution."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from preflight_editor_vnext_voice_bakeoff_car_v1 import preflight

ORDER=("V0_R2_MINISTRAL_CONTROL","V1_QWEN3_8B_NON_THINKING","V2_QWEN25_7B_INSTRUCT")
def canonical(v): return json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
def atomic(path,v):
 path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
 with tmp.open("wb") as f: f.write(json.dumps(v,sort_keys=True,indent=2,ensure_ascii=False).encode()+b"\n"); f.flush(); os.fsync(f.fileno())
 tmp.replace(path)
def run(a):
 gate=preflight(a.repo,a.product_root,a.output_root)
 a.output_root.mkdir(parents=True)
 attempted=0
 for candidate in ORDER:
  target=a.output_root/candidate
  command=[str(a.python),str(a.repo/"scripts/run_editor_vnext_voice_bakeoff_car_v1.py"),"--candidate",candidate,"--dispatch",str(a.repo/"docs/artifacts/editor-vnext-voice-bakeoff-car-dispatch-v1.jsonl"),"--cases",str(a.repo/"docs/artifacts/editor-vnext-voice-bakeoff-boundary-v1-cases.jsonl"),"--product-root",str(a.product_root),"--output",str(target)]
  env={**os.environ,"VNEXT_VOICE_BAKEOFF_AUTHORIZED":"1"}; attempted+=72
  result=subprocess.run(command,env=env)
  if result.returncode: atomic(a.output_root/"program-failure.json",{"candidate_id":candidate,"attempted_ceiling":attempted,"partial_eligible_evidence":False,"terminal_state":"FAIL"}); raise SystemExit(result.returncode)
 terminals=[json.loads((a.output_root/c/f"terminal-{c}.json").read_text()) for c in ORDER]
 outputs=list(a.output_root.glob("*/outputs/**/*.json"))
 if len(outputs)!=216: raise RuntimeError("output closure mismatch")
 core={"status":"PASS_INFERENCE_CLOSURE","outputs":216,"per_candidate":{c:72 for c in ORDER},"candidate_terminals":terminals,"zero_step_authority_identity":gate["authority_identity"],"zero_step_dispatch_identity":gate["dispatch_identity"],"retry_count":0,"partial_eligible_evidence":False,"scoring":False,"unseal":False,"training":False,"optimizer":False}
 atomic(a.output_root/"program-terminal.json",{**core,"closure_identity":hashlib.sha256(canonical(core)).hexdigest()})
def main():
 p=argparse.ArgumentParser(); p.add_argument("--repo",type=Path,required=True); p.add_argument("--product-root",type=Path,required=True); p.add_argument("--output-root",type=Path,required=True); p.add_argument("--python",type=Path,required=True); run(p.parse_args())
if __name__=="__main__": main()
