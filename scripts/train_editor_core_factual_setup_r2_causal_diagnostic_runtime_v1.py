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

def real_chat_token_map(tokenizer, messages: list[dict], spans: list[dict]) -> dict:
    """Map assistant-relative character spans onto the exact chat-template tokens."""
    assistant=messages[2]["content"]
    rendered=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=False)
    prefix=tokenizer.apply_chat_template(messages[:2],tokenize=False,add_generation_prompt=True)
    if not rendered.startswith(prefix): raise ValueError("chat template prefix drift")
    assistant_char_start=len(prefix)
    if rendered[assistant_char_start:assistant_char_start+len(assistant)]!=assistant: raise ValueError("assistant chat boundary drift")
    encoded=tokenizer(rendered,add_special_tokens=False,return_offsets_mapping=True)
    ids=list(encoded["input_ids"]); offsets=[tuple(x) for x in encoded["offset_mapping"]]
    templated=tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=False)
    template_ids=list(templated["input_ids"] if hasattr(templated,"keys") else templated)
    if ids!=template_ids or len(ids)!=len(offsets):
        mismatch=next((i for i,(a,b) in enumerate(zip(ids,template_ids)) if a!=b),min(len(ids),len(template_ids)))
        raise ValueError(f"chat template token identity drift: encoded={len(ids)} template={len(template_ids)} mismatch={mismatch} encoded_head={ids[:4]} template_head={template_ids[:4]}")
    answer_end=assistant_char_start+len(assistant)
    answer_tokens=[i for i,(a,b) in enumerate(offsets) if a<answer_end and b>assistant_char_start and a<b]
    if not answer_tokens or answer_tokens!=list(range(answer_tokens[0],answer_tokens[-1]+1)): raise ValueError("assistant token boundary")
    mapped=[]
    for span in spans:
        a,b=int(span["start"]),int(span["end"])
        if span.get("field")!="text" or assistant[a:b]!=span.get("text"): raise ValueError("critical span content")
        absolute_a=assistant_char_start+a; absolute_b=assistant_char_start+b
        selected=[i for i,(x,y) in enumerate(offsets) if x<absolute_b and y>absolute_a and x<y]
        if not selected or offsets[selected[0]][0]>absolute_a or offsets[selected[-1]][1]<absolute_b: raise ValueError("critical span tokenizer coverage")
        if selected!=list(range(selected[0],selected[-1]+1)) or any(i not in answer_tokens for i in selected): raise ValueError("critical span escaped assistant")
        mapped.append({"char_start":a,"char_end":b,"token_start":selected[0],"token_end_exclusive":selected[-1]+1,"token_char_start":offsets[selected[0]][0]-assistant_char_start,"token_char_end":offsets[selected[-1]][1]-assistant_char_start})
    return {"input_ids":ids,"assistant_token_start":answer_tokens[0],"assistant_token_end_exclusive":answer_tokens[-1]+1,"mapped_spans":mapped}

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

def _write_receipts_atomic(output: Path, documents: list[tuple[str,dict]]) -> None:
    staging=output/".staging"
    if staging.exists(): raise ValueError("stale staging")
    staging.mkdir()
    try:
        for name,value in documents: (staging/name).write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        for name,_ in documents[:-1]: os.replace(staging/name,output/name)
        os.replace(staging/documents[-1][0],output/documents[-1][0]); staging.rmdir()
    except Exception:
        raise

def run_slot(model_path: Path, parent_path: Path, corpus_path: Path, learning_signal_path: Path,
             measurement_annotations_path: Path, development_path: Path, output: Path, arm: str, seed: int) -> dict:
    if os.environ.get("CAUSAL_DIAGNOSTIC_REAL_RUN_AUTHORIZED")!="1": raise RuntimeError("real runs are not authorized")
    slot_id=slot(arm,seed)
    if output.is_symlink() or not output.is_dir() or any(output.iterdir()): raise ValueError("slot output must be distinct and empty")
    signal_name,lr_text=ARMS[arm]
    corpus=[json.loads(x) for x in corpus_path.read_text(encoding="utf-8").splitlines() if x]
    learning_signals=[json.loads(x) for x in learning_signal_path.read_text(encoding="utf-8").splitlines() if x]
    measurement_signals=[json.loads(x) for x in measurement_annotations_path.read_text(encoding="utf-8").splitlines() if x]
    learning={x["example_id"]:x for x in learning_signals}; annotations={x["example_id"]:x for x in measurement_signals}
    expected_ids={x["example_id"] for x in corpus}
    if len(corpus)!=72 or len(learning)!=72 or len(annotations)!=72 or set(learning)!=expected_ids or set(annotations)!=expected_ids: raise ValueError("corpus/signal inventory")
    targets={x["example_id"]:hashlib.sha256(x["messages"][2]["content"].encode()).hexdigest() for x in corpus}
    if any(x["assistant_target_sha256"]!=targets[x["example_id"]] for x in learning_signals): raise ValueError("learning target byte drift")
    if any(x["assistant_target_sha256"]!=targets[x["example_id"]] for x in measurement_signals): raise ValueError("measurement target byte drift")
    if any(not x["critical_spans"] for x in measurement_signals): raise ValueError("measurement critical-span coverage")

    import bitsandbytes as bnb
    import torch
    import torch.nn.functional as F
    from peft import PeftModel, prepare_model_for_kbit_training
    from torch._native.registry import deregister_op_overrides
    from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig

    random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed); torch.use_deterministic_algorithms(True); deregister_op_overrides(disable_op_symbols="bmm")
    tokenizer=AutoTokenizer.from_pretrained(model_path,local_files_only=True,fix_mistral_regex=True)
    if hashlib.sha256((model_path/"tokenizer.json").read_bytes()).hexdigest()!=EXPECTED_TOKENIZER: raise ValueError("tokenizer identity")
    if tokenizer.pad_token_id is None: tokenizer.pad_token=tokenizer.eos_token
    quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_compute_dtype=torch.bfloat16,bnb_4bit_use_double_quant=True)
    model=AutoModelForImageTextToText.from_pretrained(model_path,local_files_only=True,quantization_config=quant,device_map={"":0},dtype=torch.bfloat16,attn_implementation="sdpa",low_cpu_mem_usage=True)
    model.model.vision_tower=None; model.model.multi_modal_projector=None
    model=prepare_model_for_kbit_training(model,use_gradient_checkpointing=True,gradient_checkpointing_kwargs={"use_reentrant":True})
    model=PeftModel.from_pretrained(model,parent_path,is_trainable=True)
    trainable={n:p for n,p in model.named_parameters() if p.requires_grad}; before={n:p.detach().float().cpu().clone() for n,p in trainable.items()}

    prepared=[]
    for row in corpus:
        messages=row["messages"]; mapping=real_chat_token_map(tokenizer,messages,annotations[row["example_id"]]["critical_spans"]); tokens=mapping["input_ids"]; start=mapping["assistant_token_start"]
        if not tokens or tokens[-1]!=tokenizer.eos_token_id or len(tokens)>3072: raise ValueError("token sequence closure")
        critical=set()
        for span in mapping["mapped_spans"]: critical.update(range(span["token_start"],span["token_end_exclusive"]))
        prepared.append((tokens,start,critical))

    def probe() -> dict:
        model.eval(); full=[]; critical=[]
        with torch.no_grad():
            for tokens,start,critical_ids in prepared:
                ids=torch.tensor([tokens],device="cuda"); logits=model(input_ids=ids,use_cache=False).logits[:,:-1].float(); targets=ids[:,1:]; nll=F.cross_entropy(logits.reshape(-1,logits.shape[-1]),targets.reshape(-1),reduction="none").reshape(-1)
                answer=nll[start-1:]; full.extend(answer.detach().cpu().tolist()); critical.extend(nll[i-1].item() for i in sorted(critical_ids) if i>0)
        if not full or not critical: raise ValueError("teacher forced coverage")
        return {"full_mean_nll":format(sum(full)/len(full),".17g"),"critical_mean_nll":format(sum(critical)/len(critical),".17g"),"full_tokens":len(full),"critical_tokens":len(critical)}

    before_probe=probe(); model.train(); optimizer=bnb.optim.PagedAdamW8bit(trainable.values(),lr=float(lr_text),weight_decay=0.0); optimizer.zero_grad(set_to_none=True); steps=0; losses=[]
    for position,index in enumerate(row_order(seed),1):
        tokens,start,critical_ids=prepared[index]; ids=torch.tensor([tokens],device="cuda"); labels=ids.clone(); labels[:,:start]=-100; logits=model(input_ids=ids,use_cache=False).logits[:,:-1].float(); targets=labels[:,1:]; flat=F.cross_entropy(logits.reshape(-1,logits.shape[-1]),targets.reshape(-1),ignore_index=-100,reduction="none").reshape(-1); valid=targets.reshape(-1)!=-100; weights=torch.ones_like(flat)
        if signal_name=="T1":
            for token_index in critical_ids:
                if token_index>0: weights[token_index-1]=3.0
        loss=(flat[valid]*weights[valid]).sum()/weights[valid].sum(); (loss/8).backward(); losses.append(float(loss.detach().cpu()))
        if position%8==0: optimizer.step(); torch.cuda.synchronize(); optimizer.zero_grad(set_to_none=True); steps+=1
    if steps!=9: raise ValueError("optimizer schedule")
    after_probe=probe(); after={n:p.detach().float().cpu() for n,p in trainable.items()}; squares=0.0; changed=0
    for n in before:
        delta=after[n]-before[n]; value=float(torch.sum(delta*delta)); squares+=value; changed+=value>0
    delta_receipt=receipt("adapter-delta",slot_id,{"tensor_count":len(before),"changed_tensor_count":changed,"global_l2":format(math.sqrt(squares),".17g")})
    teacher=receipt("teacher-forced",slot_id,{"before":before_probe,"after":after_probe})
    adapter_dir=output/"adapter.tmp"; model.save_pretrained(adapter_dir,safe_serialization=True); os.replace(adapter_dir,output/"adapter")
    semantic=receipt("semantic-measurement",slot_id,{"development_requests_sha256":hashlib.sha256(development_path.read_bytes()).hexdigest(),"deterministic_decoding_bound":True,"answer_key_loaded":False,"status":"PENDING_SEPARATE_DETERMINISTIC_MEASUREMENT"})
    terminal=receipt("terminal",slot_id,{"status":"PASS_TRAINING_TERMINAL","optimizer_steps":steps,"final_loss":format(losses[-1],".17g"),"model_loaded":True,"training_performed":True,"inference_performed":False})
    _write_receipts_atomic(output,[("teacher-forced.json",teacher),("adapter-delta.json",delta_receipt),("semantic.json",semantic),("terminal.json",terminal)])
    return terminal

if __name__ == "__main__":
    if len(sys.argv)!=10: raise SystemExit("usage: worker MODEL PARENT CORPUS LEARNING_SIGNAL MEASUREMENT_ANNOTATIONS DEVELOPMENT OUTPUT ARM SEED")
    print(json.dumps(run_slot(*map(Path,sys.argv[1:8]),sys.argv[8],int(sys.argv[9])),sort_keys=True,separators=(",",":")))
