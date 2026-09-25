"""Real-runtime worker for the R2 causal learnability diagnostic.

ML imports and model construction are reachable only from ``run_slot``.  The
fixture entry point exercises the same span mapping, receipts, and terminal
state rules without importing an ML package.
"""
from __future__ import annotations

import hashlib, json, math, os, random, sys
from pathlib import Path

ARMS = {
    "T0_CONTROL_S0_CONTROL": ("T0", "5e-7"),
    "T0_CONTROL_S1_HIGHER_PLASTICITY": ("T0", "1e-6"),
    "T1_CONTRACT_WEIGHTED_S0_CONTROL": ("T1", "5e-7"),
    "T1_CONTRACT_WEIGHTED_S1_HIGHER_PLASTICITY": ("T1", "1e-6"),
}
SEEDS = (161803, 271828, 314159)
EXPECTED_PROTOCOL = "41799641949b42a3bd0c4c50abd9cb1dc7da72d594db106bbb8704b5fdfbda7a"
EXPECTED_PACK = "c9480b68c8f2c10ce4e36b2371d6ae564b43a4ad5fdde23e57759dc4ec8a99bc"
EXPECTED_RECIPES = "61de5f5276af6899a708522c4e6ae91e31e40fe977aafacad4fc0bfebc29bced"
EXPECTED_EVALUATION = "0f31cb67ea2a5b6094307bb54c76d6c3856d48088bff867a9aacdd57de8e791a"
EXPECTED_PARENT = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
EXPECTED_CHECKPOINT = "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be"
EXPECTED_TOKENIZER = "d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135"

def canonical(v): return json.dumps(v, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()
def identity(v): return hashlib.sha256(canonical(v)).hexdigest()

def slot(arm: str, seed: int) -> str:
    if arm not in ARMS or seed not in SEEDS: raise ValueError("unauthorized arm/seed")
    return f"{arm}__seed_{seed}"

def row_order(seed: int) -> list[int]:
    order=list(range(72)); random.Random(seed).shuffle(order); return order

def real_token_map(tokenizer, assistant: str, spans: list[dict]) -> dict:
    encoded=tokenizer(assistant, add_special_tokens=False, return_offsets_mapping=True)
    ids=list(encoded["input_ids"]); offsets=[tuple(x) for x in encoded["offset_mapping"]]
    if not ids or len(ids)!=len(offsets): raise ValueError("tokenizer offset closure")
    mapped=[]
    for span in spans:
        a,b=int(span["start"]),int(span["end"])
        if span.get("field")!="text" or assistant[a:b]!=span.get("text"): raise ValueError("critical span content")
        selected=[i for i,(x,y) in enumerate(offsets) if x<b and y>a and x<y]
        if not selected or offsets[selected[0]][0]>a or offsets[selected[-1]][1]<b: raise ValueError("critical span tokenizer coverage")
        if selected != list(range(selected[0], selected[-1]+1)): raise ValueError("discontinuous mapping")
        mapped.append({"char_start":a,"char_end":b,"token_start":selected[0],"token_end_exclusive":selected[-1]+1,"token_char_start":offsets[selected[0]][0],"token_char_end":offsets[selected[-1]][1]})
    return {"assistant_token_ids":ids,"mapped_spans":mapped}

def receipt(kind: str, slot_id: str, payload: dict) -> dict:
    core={"schema":f"editor-factual-setup-r2-causal-runtime-{kind}","schema_version":1,"slot_id":slot_id,**payload}
    return {**core,"receipt_identity":identity(core)}

def fixture_run(tokenizer, assistant: str, annotation: dict, output: Path, arm: str, seed: int) -> dict:
    if output.is_symlink() or not output.is_dir() or any(output.iterdir()): raise ValueError("output must be distinct and empty")
    slot_id=slot(arm,seed); mapping=real_token_map(tokenizer,assistant,annotation["critical_spans"])
    diagnostics=receipt("teacher-forced",slot_id,{"before":{"full_mean_nll":"1.5","critical_mean_nll":"2"},"after":{"full_mean_nll":"1","critical_mean_nll":"1.25"}})
    delta=receipt("adapter-delta",slot_id,{"tensor_count":2,"changed_tensor_count":2,"global_l2":"0.125"})
    semantic=receipt("semantic-measurement",slot_id,{"partitions":{"TRAIN_ACQUISITION":48,"REPLAY_RETENTION":24,"DEVELOPMENT_EVALUATION":24},"decoded":False,"fixture_only":True})
    terminal=receipt("terminal",slot_id,{"status":"PASS_FIXTURE_ONLY","optimizer_steps":0,"model_loaded":False,"training_performed":False,"inference_performed":False})
    documents=(("mapping.json",mapping),("teacher-forced.json",diagnostics),("adapter-delta.json",delta),("semantic.json",semantic),("terminal.json",terminal))
    staging=output/".staging"; staging.mkdir()
    for name,value in documents:
        (staging/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    # Terminal is published last. A failure can leave only ineligible staging.
    for name,_ in documents[:-1]: os.replace(staging/name,output/name)
    os.replace(staging/"terminal.json",output/"terminal.json"); staging.rmdir()
    return terminal

def run_slot(*args, **kwargs):
    if os.environ.get("CAUSAL_DIAGNOSTIC_REAL_RUN_AUTHORIZED")!="1": raise RuntimeError("real runs are not authorized")
    # Imports remain beyond the authorization gate by construction.
    import torch  # noqa: F401
    from transformers import AutoTokenizer  # noqa: F401
    raise RuntimeError("published execution authority required before real run")

if __name__ == "__main__":
    raise SystemExit("direct execution disabled; use the bound route")
