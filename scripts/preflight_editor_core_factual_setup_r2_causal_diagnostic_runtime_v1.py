"""Tokenizer-only executable preflight; this module never imports torch/model classes."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
try:
    from worker import ARMS, SEEDS, EXPECTED_TOKENIZER, identity, real_token_map, row_order
except ImportError:  # repository execution
    from train_editor_core_factual_setup_r2_causal_diagnostic_runtime_v1 import ARMS, SEEDS, EXPECTED_TOKENIZER, identity, real_token_map, row_order

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--model",type=Path,required=True); p.add_argument("--corpus",type=Path,required=True); p.add_argument("--challenger",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    if sha(a.model/"tokenizer.json") != EXPECTED_TOKENIZER: raise ValueError("exact tokenizer mismatch")
    if a.output.is_symlink() or not a.output.is_dir() or any(a.output.iterdir()): raise ValueError("output root must be empty")
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(a.model,local_files_only=True,fix_mistral_regex=True)
    rows=[json.loads(x) for x in a.challenger.read_text(encoding="utf-8").splitlines() if x]
    corpus={r["example_id"]:r for r in (json.loads(x) for x in a.corpus.read_text(encoding="utf-8").splitlines() if x)}
    mapped=[]
    for row in rows:
        source=corpus[row["example_id"]]; assistant=source["messages"][2]["content"]
        if hashlib.sha256(assistant.encode()).hexdigest()!=row["assistant_target_sha256"]: raise ValueError("assistant target binding")
        m=real_token_map(tok,assistant,row["critical_spans"]); mapped.append({"example_id":row["example_id"],"spans":m["mapped_spans"]})
    core={"schema":"editor-factual-setup-r2-causal-runtime-tokenizer-preflight","schema_version":1,"status":"PASS_ZERO_STEP","tokenizer_sha256":EXPECTED_TOKENIZER,"rows":len(rows),"spans":sum(len(x["spans"]) for x in mapped),"mapping_identity":identity(mapped),"orders":{str(s):identity(row_order(s)) for s in SEEDS},"arms":sorted(ARMS),"slots":12,"model_loaded":False,"optimizer_created":False,"optimizer_steps":0,"training_performed":False,"inference_performed":False}
    print(json.dumps({**core,"preflight_identity":identity(core)},sort_keys=True,separators=(",",":")))
    return 0
if __name__=="__main__": raise SystemExit(main())
