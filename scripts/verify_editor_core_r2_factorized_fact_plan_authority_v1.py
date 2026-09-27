from __future__ import annotations
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).parents[1]; AUTH=ROOT/"docs/artifacts/editor-core-r2-factorized-fact-plan-execution-authority-v1.json"
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def verify(intervention=None,seed=None):
 d=json.loads(AUTH.read_text(encoding="utf-8")); ident=d.pop("authority_identity"); assert ident==hashlib.sha256(canonical(d)).hexdigest()
 assert len(d["slots"])==len({x["slot_id"] for x in d["slots"]})==len({x["output_slug"] for x in d["slots"]})==12
 assert d["published_commit"]=="08adffa0d3c5827ac715b73fc13f6b1cb915b3a0" and d["parent"]=="R2_STEP_9"
 assert d["schema_version"]==2 and d["runtime_python"]=="/root/pf9-ml-runtime-20260926/bin/python" and d["atomic_failure_evidence_required"]
 assert not d["retry_authorized"] and d["stop_on_first_failure"] and d["fresh_exact_tokenizer_zero_step_per_slot"]
 assert d["owner_run_authorization_required"] and not d["real_runs_authorized_in_build_task"] and not d["parent_selection_authority"]
 if intervention is None:return {"authority_identity":ident,"slots":d["slots"]}
 found=[x for x in d["slots"] if x["intervention"]==intervention and x["seed"]==seed]; assert len(found)==1; return {"authority_identity":ident,"slot":found[0]}
if __name__=="__main__": print(json.dumps({"status":"PASS","blockers":0,**verify()},sort_keys=True))
