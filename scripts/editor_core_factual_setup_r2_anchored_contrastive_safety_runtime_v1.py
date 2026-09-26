"""Runtime primitives for the anchored contrastive safety diagnostic.

No ML package is imported at module import time.  Real execution remains
unreachable until a separately published authority enables ``run_slot``.
"""
from __future__ import annotations

import hashlib, json, os, random
from pathlib import Path

ARMS = {
    "P0_POSITIVE_ONLY_K0_NO_KL": (False, False),
    "P1_CONTRASTIVE_K0_NO_KL": (True, False),
    "P0_POSITIVE_ONLY_K1_R2_KL": (False, True),
    "P1_CONTRASTIVE_K1_R2_KL": (True, True),
}
SEEDS = (161803, 271828, 314159)
EXPECTED_SOURCE_COMMIT = "eadbddf23da3408f8cfb8233823f4f8fd974519f"
EXPECTED_SOURCE_TREE = "e07eb052f78d2d634dcd4f5482fb84508f585a2d"
EXPECTED_PROTOCOL = "7c9595d94b7cd1af535e74380e11ee4424af1b31edfe0195b1198acb9fba86b4"
EXPECTED_PACK = "4aba4d0ae34630528621a34b3f33bf0dc8152ece8bc40e95d8aeffe43c696449"
EXPECTED_RECIPE = "61de5f5276af6899a708522c4e6ae91e31e40fe977aafacad4fc0bfebc29bced"
EXPECTED_EVALUATOR = "0f31cb67ea2a5b6094307bb54c76d6c3856d48088bff867a9aacdd57de8e791a"
EXPECTED_PARENT = "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
EXPECTED_CHECKPOINT = "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be"
EXPECTED_TOKENIZER = "d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135"
EXPECTED_PAIRS = "a986105db31a02a6cc16dfab0821666a58f58685a83f50cead7c25bd5a536cc1"
EXPECTED_RETENTION = "6f3599e17010e0a7154f8f85019a9b4f55a4db897da87f4d1c35c435c15d5b7f"

def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()

def identity(value): return hashlib.sha256(canonical(value)).hexdigest()
def sha(path: Path): return hashlib.sha256(path.read_bytes()).hexdigest()

def slot_id(arm: str, seed: int) -> str:
    if arm not in ARMS or seed not in SEEDS: raise ValueError("unauthorized arm/seed")
    return f"{arm}__seed_{seed}"

def matched_order(seed: int, size: int = 72) -> list[int]:
    if seed not in SEEDS: raise ValueError("unauthorized seed")
    order=list(range(size)); random.Random(seed).shuffle(order); return order

def map_text_tokens(tokenizer, text: str) -> dict:
    encoded=tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
    ids=list(encoded["input_ids"]); offsets=[tuple(x) for x in encoded["offset_mapping"]]
    if not ids or len(ids)!=len(offsets) or any(a>b for a,b in offsets): raise ValueError("tokenizer offset closure")
    return {"token_ids":ids,"offsets":offsets,"mapping_identity":identity({"ids":ids,"offsets":offsets})}

def validate_pair(tokenizer, pair: dict) -> dict:
    chosen_raw=pair["chosen_response"]; rejected_raw=pair["rejected_response"]
    chosen=json.loads(chosen_raw); rejected=json.loads(rejected_raw)
    if set(chosen)!=set(rejected) or {k:v for k,v in chosen.items() if k!="text"}!={k:v for k,v in rejected.items() if k!="text"}: raise ValueError("only text may differ")
    if chosen["case_id"]!=rejected["case_id"] or chosen["case_id"]!=pair["example_id"]: raise ValueError("case binding")
    if chosen["text"]==rejected["text"]: raise ValueError("empty contrast")
    if hashlib.sha256(chosen_raw.encode()).hexdigest()!=pair["chosen_sha256"]: raise ValueError("chosen identity")
    if hashlib.sha256(rejected_raw.encode()).hexdigest()!=pair["rejected_sha256"]: raise ValueError("rejected identity")
    c=map_text_tokens(tokenizer,chosen_raw); r=map_text_tokens(tokenizer,rejected_raw)
    return {"pair_id":pair["pair_id"],"failure_class":pair["failure_class"],"chosen_tokens":len(c["token_ids"]),"rejected_tokens":len(r["token_ids"]),"chosen_mapping":c["mapping_identity"],"rejected_mapping":r["mapping_identity"]}

def validate_inputs(tokenizer, pairs_path: Path, retention_path: Path) -> dict:
    if sha(pairs_path)!=EXPECTED_PAIRS or sha(retention_path)!=EXPECTED_RETENTION: raise ValueError("pack byte identity")
    pairs=[json.loads(x) for x in pairs_path.read_text(encoding="utf-8").splitlines() if x]
    anchors=[json.loads(x) for x in retention_path.read_text(encoding="utf-8").splitlines() if x]
    if len(pairs)!=48 or len(anchors)!=24: raise ValueError("pack inventory")
    mapped=[validate_pair(tokenizer,row) for row in pairs]
    if len({x["pair_id"] for x in mapped})!=48: raise ValueError("duplicate pairs")
    if len({x["example_id"] for x in anchors})!=24: raise ValueError("duplicate retention anchors")
    if any(x["anchor"]!="R2_STEP_9_FROZEN_LOGITS" or x["reference_logits_persisted"] for x in anchors): raise ValueError("retention authority")
    return {"pairs":48,"retention_anchors":24,"pair_mapping_identity":identity(mapped),"failure_classes":sorted({x["failure_class"] for x in mapped})}

def fixture_slot(tokenizer, pairs_path: Path, retention_path: Path, output: Path, arm: str, seed: int) -> dict:
    if output.is_symlink() or not output.is_dir() or any(output.iterdir()): raise ValueError("output root must be distinct and empty")
    validated=validate_inputs(tokenizer,pairs_path,retention_path); sid=slot_id(arm,seed)
    core={"schema":"editor-r2-anchored-contrastive-runtime-fixture-receipt","schema_version":1,"slot_id":sid,"arm":arm,"seed":seed,"contrastive":ARMS[arm][0],"r2_kl":ARMS[arm][1],"matched_order_identity":identity(matched_order(seed)),**validated,"model_loaded":False,"optimizer_created":False,"optimizer_steps":0,"training_performed":False,"inference_performed":False,"status":"PASS_FIXTURE_ONLY"}
    receipt={**core,"receipt_identity":identity(core)}
    staging=output/".staging"; staging.mkdir(); (staging/"terminal.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n",encoding="utf-8"); os.replace(staging/"terminal.json",output/"terminal.json"); staging.rmdir()
    return receipt

def run_slot(*_args, **_kwargs):
    """Fail closed until a separate execution-authority successor is published."""
    raise RuntimeError("real execution authority is not published")
