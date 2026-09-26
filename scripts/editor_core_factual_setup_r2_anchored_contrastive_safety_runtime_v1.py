"""Runtime primitives for the anchored contrastive safety diagnostic.

No ML package is imported at module import time.  Real execution remains
unreachable until a separately published authority enables ``run_slot``.
"""
from __future__ import annotations

import hashlib, json, math, os, random
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
    """Execute one authorized research slot; imports ML packages lazily."""
    if os.environ.get("ANCHORED_CONTRASTIVE_REAL_RUN_AUTHORIZED")!="1":
        raise RuntimeError("real execution authority is not published")
    return _run_authorized_slot(*_args, **_kwargs)

def _chat_tokens(tokenizer, messages: list[dict]) -> tuple[list[int], int]:
    full=tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=False)
    prefix=tokenizer.apply_chat_template(messages[:2],tokenize=True,add_generation_prompt=True)
    ids=list(full["input_ids"] if hasattr(full,"keys") else full); start=len(prefix["input_ids"] if hasattr(prefix,"keys") else prefix)
    if not ids or start>=len(ids): raise ValueError("assistant token boundary")
    return ids,start

def _chat_span_tokens(tokenizer, messages: list[dict], spans: list[dict]) -> set[int]:
    assistant=messages[2]["content"]; rendered=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=False); prefix=tokenizer.apply_chat_template(messages[:2],tokenize=False,add_generation_prompt=True)
    if not rendered.startswith(prefix) or rendered[len(prefix):len(prefix)+len(assistant)]!=assistant: raise ValueError("assistant character boundary")
    encoded=tokenizer(rendered,add_special_tokens=False,return_offsets_mapping=True); ids=list(encoded["input_ids"]); offsets=[tuple(x) for x in encoded["offset_mapping"]]
    template=tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=False); template_ids=list(template["input_ids"] if hasattr(template,"keys") else template)
    if ids!=template_ids or len(ids)!=len(offsets): raise ValueError("chat tokenizer identity")
    selected:set[int]=set(); base=len(prefix)
    for span in spans:
        a,b=int(span["start"]),int(span["end"])
        if span.get("field")!="text" or assistant[a:b]!=span.get("text"): raise ValueError("critical span")
        hits=[i for i,(x,y) in enumerate(offsets) if x<base+b and y>base+a and x<y]
        if not hits or hits!=list(range(hits[0],hits[-1]+1)): raise ValueError("critical token coverage")
        selected.update(hits)
    if not selected: raise ValueError("empty critical mapping")
    return selected

def _run_authorized_slot(model_path: Path, parent_path: Path, corpus_path: Path, annotations_path: Path,
                         pairs_path: Path, retention_path: Path, development_path: Path,
                         output: Path, arm: str, seed: int) -> dict:
    sid=slot_id(arm,seed)
    if output.is_symlink() or not output.is_dir() or any(output.iterdir()): raise ValueError("slot output must be distinct and empty")
    if sha(pairs_path)!=EXPECTED_PAIRS or sha(retention_path)!=EXPECTED_RETENTION: raise ValueError("pack identity")
    corpus=[json.loads(x) for x in corpus_path.read_text(encoding="utf-8").splitlines() if x]
    annotations={x["example_id"]:x for x in (json.loads(y) for y in annotations_path.read_text(encoding="utf-8").splitlines() if y)}
    pairs={x["example_id"]:x for x in (json.loads(y) for y in pairs_path.read_text(encoding="utf-8").splitlines() if y)}
    anchors={x["example_id"]:x for x in (json.loads(y) for y in retention_path.read_text(encoding="utf-8").splitlines() if y)}
    rows={x["example_id"]:x for x in corpus}
    if len(corpus)!=72 or len(annotations)!=72 or len(pairs)!=48 or len(anchors)!=24 or set(rows)!=(set(pairs)|set(anchors)): raise ValueError("partition inventory")
    if any(hashlib.sha256(rows[k]["messages"][2]["content"].encode()).hexdigest()!=v["chosen_sha256"] for k,v in pairs.items()): raise ValueError("chosen/corpus drift")

    import bitsandbytes as bnb
    import torch
    import torch.nn.functional as F
    from peft import PeftModel, prepare_model_for_kbit_training
    from torch._native.registry import deregister_op_overrides
    from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig

    random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed); torch.use_deterministic_algorithms(True); deregister_op_overrides(disable_op_symbols="bmm")
    if sha(model_path/"tokenizer.json")!=EXPECTED_TOKENIZER: raise ValueError("tokenizer identity")
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True,fix_mistral_regex=True)
    if tokenizer.pad_token_id is None: tokenizer.pad_token=tokenizer.eos_token
    quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_compute_dtype=torch.bfloat16,bnb_4bit_use_double_quant=True)
    model=AutoModelForImageTextToText.from_pretrained(model_path,local_files_only=True,quantization_config=quant,device_map={"":0},dtype=torch.bfloat16,attn_implementation="sdpa",low_cpu_mem_usage=True)
    model.model.vision_tower=None; model.model.multi_modal_projector=None
    model=prepare_model_for_kbit_training(model,use_gradient_checkpointing=True,gradient_checkpointing_kwargs={"use_reentrant":True}); model=PeftModel.from_pretrained(model,parent_path,is_trainable=True)
    trainable={n:p for n,p in model.named_parameters() if p.requires_grad}; parent_state={n:p.detach().float().cpu().clone() for n,p in trainable.items()}

    prepared=[]
    for row in corpus:
        eid=row["example_id"]; ids,start=_chat_tokens(tokenizer,row["messages"])
        if ids[-1]!=tokenizer.eos_token_id or len(ids)>3072: raise ValueError("sequence closure")
        rejected=None
        if eid in pairs:
            rejected_messages=[*row["messages"][:2],{"role":"assistant","content":pairs[eid]["rejected_response"]}]; rejected=_chat_tokens(tokenizer,rejected_messages)
        critical=_chat_span_tokens(tokenizer,row["messages"],annotations[eid]["critical_spans"])
        prepared.append((eid,ids,start,rejected,critical))

    def sequence_nll(ids:list[int],start:int,critical:set[int]|None=None):
        tensor=torch.tensor([ids],device="cuda"); logits=model(input_ids=tensor,use_cache=False).logits[:,:-1].float(); targets=tensor[:,1:]; losses=F.cross_entropy(logits.reshape(-1,logits.shape[-1]),targets.reshape(-1),reduction="none"); answer=losses[start-1:]; return answer.mean(),logits,targets
    def probe():
        model.eval(); values=[]
        with torch.no_grad():
            for _,ids,start,_,_ in prepared: values.append(float(sequence_nll(ids,start)[0].cpu()))
        return format(sum(values)/len(values),".17g")
    before_probe=probe(); model.train(); optimizer=bnb.optim.PagedAdamW8bit(trainable.values(),lr=5e-7,weight_decay=0.0); optimizer.zero_grad(set_to_none=True); steps=0; losses=[]
    contrastive,anchored=ARMS[arm]
    for position,index in enumerate(matched_order(seed),1):
        eid,ids,start,rejected,critical=prepared[index]; positive,positive_logits,positive_targets=sequence_nll(ids,start)
        tensor=torch.tensor([ids],device="cuda"); flat=F.cross_entropy(positive_logits.reshape(-1,positive_logits.shape[-1]),positive_targets.reshape(-1),reduction="none"); valid=torch.arange(flat.numel(),device="cuda")>=start-1; weights=torch.ones_like(flat)
        for token_index in critical:
            if token_index>0: weights[token_index-1]=3.0
        loss=(flat[valid]*weights[valid]).sum()/weights[valid].sum()
        if contrastive and rejected is not None:
            rejected_nll,_,_=sequence_nll(*rejected); loss=loss+torch.relu(torch.tensor(0.25,device="cuda")-(rejected_nll-positive))
        if anchored and eid in anchors:
            current={n:p.detach().float().cpu().clone() for n,p in trainable.items()}
            with torch.no_grad():
                for n,p in trainable.items(): p.copy_(parent_state[n].to(p.device,dtype=p.dtype))
                ref=model(input_ids=torch.tensor([ids],device="cuda"),use_cache=False).logits[:,:-1].float().detach()
                for n,p in trainable.items(): p.copy_(current[n].to(p.device,dtype=p.dtype))
            cand=model(input_ids=torch.tensor([ids],device="cuda"),use_cache=False).logits[:,:-1].float(); ref_prob=F.softmax(ref[:,start-1:],dim=-1); kl=F.kl_div(F.log_softmax(cand[:,start-1:],dim=-1),ref_prob,reduction="none").sum(dim=-1).mean(); loss=loss+0.10*kl
        (loss/8).backward(); losses.append(float(loss.detach().cpu()))
        if position%8==0: optimizer.step(); torch.cuda.synchronize(); optimizer.zero_grad(set_to_none=True); steps+=1
    if steps!=9: raise ValueError("optimizer schedule")
    after_probe=probe(); squares=0.0; changed=0
    for n,p in trainable.items():
        delta=p.detach().float().cpu()-parent_state[n]; value=float(torch.sum(delta*delta)); squares+=value; changed+=value>0
    adapter_tmp=output/"adapter.tmp"; model.save_pretrained(adapter_tmp,safe_serialization=True); os.replace(adapter_tmp,output/"adapter")
    receipts={
      "teacher-forced.json":{"before_full_mean_nll":before_probe,"after_full_mean_nll":after_probe},
      "adapter-delta.json":{"tensor_count":len(trainable),"changed_tensor_count":changed,"global_l2":format(math.sqrt(squares),".17g")},
      "semantic.json":{"development_requests_sha256":sha(development_path),"status":"PENDING_SEPARATE_DETERMINISTIC_EVALUATION","answer_key_loaded":False},
      "terminal.json":{"status":"PASS_TRAINING_TERMINAL","slot_id":sid,"optimizer_steps":steps,"final_loss":format(losses[-1],".17g"),"model_loaded":True,"training_performed":True,"inference_performed":False}}
    staging=output/".staging"; staging.mkdir()
    for name,value in receipts.items(): (staging/name).write_text(json.dumps(value,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    for name in list(receipts)[:-1]: os.replace(staging/name,output/name)
    os.replace(staging/"terminal.json",output/"terminal.json"); staging.rmdir(); return receipts["terminal.json"]

def main() -> int:
    import argparse
    p=argparse.ArgumentParser()
    for name in ("model","parent","corpus","annotations","pairs","retention","development","output"):
        p.add_argument(f"--{name}",type=Path,required=True)
    p.add_argument("--arm",choices=sorted(ARMS),required=True); p.add_argument("--seed",type=int,choices=SEEDS,required=True)
    p.add_argument("--execute-authorized",action="store_true")
    a=p.parse_args()
    if not a.execute_authorized or os.environ.get("ANCHORED_CONTRASTIVE_REAL_RUN_AUTHORIZED")!="1":
        raise SystemExit("separate real-run authorization required")
    result=_run_authorized_slot(a.model,a.parent,a.corpus,a.annotations,a.pairs,a.retention,a.development,a.output,a.arm,a.seed)
    print(json.dumps(result,sort_keys=True)); return 0

if __name__=="__main__": raise SystemExit(main())
