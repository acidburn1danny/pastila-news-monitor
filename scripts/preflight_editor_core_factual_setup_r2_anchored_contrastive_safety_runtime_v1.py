"""Exact-tokenizer zero-step. It never imports model or optimizer classes."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from editor_core_factual_setup_r2_anchored_contrastive_safety_runtime_v1 import ARMS, SEEDS, EXPECTED_TOKENIZER, identity, matched_order, sha, validate_inputs

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--model",type=Path,required=True); p.add_argument("--pairs",type=Path,required=True); p.add_argument("--retention",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    if sha(a.model/"tokenizer.json")!=EXPECTED_TOKENIZER: raise ValueError("exact tokenizer mismatch")
    if a.output.is_symlink() or not a.output.is_dir() or any(a.output.iterdir()): raise ValueError("output root must be distinct and empty")
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(a.model,local_files_only=True,fix_mistral_regex=True)
    closure=validate_inputs(tokenizer,a.pairs,a.retention)
    core={"schema":"editor-r2-anchored-contrastive-runtime-zero-step","schema_version":1,"status":"PASS_ZERO_STEP","tokenizer_sha256":EXPECTED_TOKENIZER,**closure,"arms":sorted(ARMS),"seeds":list(SEEDS),"slots":len(ARMS)*len(SEEDS),"orders":{str(s):identity(matched_order(s)) for s in SEEDS},"model_loaded":False,"optimizer_created":False,"optimizer_steps":0,"training_performed":False,"inference_performed":False,"parent_selection_authority":False}
    print(json.dumps({**core,"preflight_identity":identity(core)},sort_keys=True,separators=(",",":"))); return 0
if __name__=="__main__": raise SystemExit(main())
