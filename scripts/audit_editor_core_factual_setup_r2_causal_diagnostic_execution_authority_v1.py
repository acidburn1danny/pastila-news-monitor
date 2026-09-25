from __future__ import annotations
import ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).parents[1]; AUTH=ROOT/"docs/artifacts/editor-core-factual-setup-r2-causal-diagnostic-v1-execution-authority.json"
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def main():
 d=json.loads(AUTH.read_text(encoding="utf-8")); ident=d.pop("authority_identity"); assert ident==hashlib.sha256(canonical(d)).hexdigest(); assert len(d["slots"])==12 and len({x["slot_id"] for x in d["slots"]})==12 and len({x["output_slug"] for x in d["slots"]})==12
 assert all(x["optimizer_steps"]==9 and x["run_limit"]==1 and x["fresh_zero_step_required"] for x in d["slots"])
 assert d["owner_run_authorization_required"] and not d["real_runs_authorized_in_build_task"] and not d["holdout_access_authorized"] and not d["parent_selection_authority"]
 worker=(ROOT/"scripts/train_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1.py").read_text(encoding="utf-8"); tree=ast.parse(worker); assert "CAUSAL_DIAGNOSTIC_REAL_RUN_AUTHORIZED" in worker and any(isinstance(n,ast.FunctionDef) and n.name=="run_slot" for n in tree.body)
 supervisor=(ROOT/"scripts/supervise_editor_core_factual_setup_r2_causal_diagnostic_v1.py").read_text(encoding="utf-8"); assert "real runs require a separate owner authorization invocation" in supervisor
 print(json.dumps({"status":"PASS","blockers":0,"authority_identity":ident,"slots":12,"real_runs":0,"model_loaded":False,"optimizer_steps":0},sort_keys=True))
if __name__=="__main__": main()
