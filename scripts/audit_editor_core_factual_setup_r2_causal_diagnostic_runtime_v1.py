from __future__ import annotations
import ast,hashlib,json,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).parents[1]
BOUNDARY=ROOT/"docs/artifacts/editor-core-factual-setup-r2-causal-diagnostic-v1-runtime-boundary.json"
def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    b=json.loads(BOUNDARY.read_text(encoding="utf-8")); ident=b.pop("runtime_boundary_identity"); assert ident==hashlib.sha256(canonical(b)).hexdigest()
    assert b["slots"]==12 and b["arms"]==4 and b["seeds"]==[161803,271828,314159]
    assert not any((b["training_authorized"],b["model_load_authorized"],b["optimizer_creation_authorized"],b["parent_selection_authority"])) and b["optimizer_steps_authorized"]==0
    paths={"worker":"scripts/train_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1.py","route":"scripts/run_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1.sh","preflight":"scripts/preflight_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1.py","smoke":"scripts/smoke_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1.py"}
    assert b["files"]=={k:sha(ROOT/v) for k,v in paths.items()}
    tree=ast.parse((ROOT/paths["worker"]).read_text(encoding="utf-8")); assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) and any(a.name.split('.')[0] in {"torch","transformers","peft","bitsandbytes"} for a in n.names) for n in tree.body)
    route=(ROOT/paths["route"]).read_text(encoding="utf-8"); assert "--preflight-only" in route and "--execute-authorized" not in route
    print(json.dumps({"status":"PASS","blockers":0,"runtime_boundary_identity":ident,"model_loaded":False,"optimizer_created":False,"optimizer_steps":0,"training_performed":False,"inference_performed":False},sort_keys=True))
if __name__=="__main__": main()
