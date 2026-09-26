from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).parents[1]; AUTH=ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v2-execution-authority.json"; BOUND=ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v2-runtime-boundary.json"
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def verify(arm=None,seed=None,published=False):
 d=json.loads(AUTH.read_text()); ident=d.pop("authority_identity"); assert ident==hashlib.sha256(canonical(d)).hexdigest(); b=json.loads(BOUND.read_text()); bi=b.pop("runtime_boundary_identity"); assert bi==hashlib.sha256(canonical(b)).hexdigest()==d["runtime_boundary_identity"]
 assert len(d["slots"])==12 and len({x["slot_id"] for x in d["slots"]})==12 and d["program_run_limit"]==1 and not d["retry_authorized"] and d["stop_on_first_failure"]
 assert d["parent"]=="R2_STEP_9" and d["weighted_sft_t1s0_line"]=="CLOSED_REFERENCE_ONLY" and not d["historical_holdouts_allowed"] and not d["parent_selection_authority"]
 for key,path in {"worker":"scripts/editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v2.py","preflight":"scripts/preflight_editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v2.py","supervisor":"scripts/supervise_editor_core_factual_setup_r2_anchored_contrastive_safety_v2.py","verifier":"scripts/verify_editor_core_factual_setup_r2_anchored_contrastive_safety_authority_v2.py"}.items():
  raw=(ROOT/path).read_bytes(); assert hashlib.sha256(raw).hexdigest()==d["source_sha256"][key]; assert subprocess.check_output(["git","show",f'{d["runtime_source_commit"]}:{path}'],cwd=ROOT)==raw
 assert subprocess.check_output(["git","rev-parse",f'{d["runtime_source_commit"]}^{{tree}}'],cwd=ROOT,text=True).strip()==d["runtime_source_tree"]
 if published:
  upstream=subprocess.check_output(["git","rev-parse","@{upstream}"],cwd=ROOT,text=True).strip(); assert subprocess.call(["git","merge-base","--is-ancestor",d["runtime_source_commit"],upstream],cwd=ROOT)==0
 if arm is None: return {"authority_identity":ident,"slots":d["slots"]}
 found=[x for x in d["slots"] if x["arm"]==arm and x["seed"]==seed]; assert len(found)==1; return {"authority_identity":ident,"slot":found[0]}
if __name__=="__main__": print(json.dumps({"status":"PASS","blockers":0,**verify()},sort_keys=True))
