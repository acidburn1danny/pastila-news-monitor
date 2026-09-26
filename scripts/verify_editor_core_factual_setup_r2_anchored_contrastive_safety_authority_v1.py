from __future__ import annotations
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).parents[1]; PATH=ROOT/"docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-execution-authority.json"
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def verify(arm=None,seed=None,published=False):
 d=json.loads(PATH.read_text()); ident=d.pop("authority_identity"); assert ident==hashlib.sha256(canonical(d)).hexdigest()
 assert len(d["slots"])==12 and len({x["slot_id"] for x in d["slots"]})==12 and len({x["output_slug"] for x in d["slots"]})==12
 assert not d["retry_authorized"] and d["stop_on_first_failure"] and d["owner_run_authorization_required"] and not d["real_runs_authorized_in_build_task"]
 assert d["parent"]=="R2_STEP_9" and d["weighted_sft_t1s0_line"]=="CLOSED_REFERENCE_ONLY" and not d["historical_holdouts_allowed"] and not d["parent_selection_authority"]
 if published:
  head=subprocess.check_output(["git","rev-parse","@{upstream}"],cwd=ROOT,text=True).strip(); assert subprocess.call(["git","merge-base","--is-ancestor",head,"HEAD"],cwd=ROOT)==0
 if arm is None: return {"authority_identity":ident,"slots":d["slots"]}
 found=[x for x in d["slots"] if x["arm"]==arm and x["seed"]==seed]; assert len(found)==1; return {"authority_identity":ident,"slot":found[0]}
if __name__=="__main__": print(json.dumps({"status":"PASS","blockers":0,**verify()},sort_keys=True))
