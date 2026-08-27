"""WSL-side evaluation-only Core V1.2 Stage P constrained runner."""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

MODEL=Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
ADAPTER=Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.3/runs/pastila-editor-core-v1-2-deontology-20260820-003/checkpoint-final/adapter")
ROOT=Path("/mnt/c/Projects/pastila-news-monitor")


def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None: raise RuntimeError(f"cannot load {name}")
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module


def _constraint_types():
    dfa=_load("sav2_stage_p_dfa_probe",ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_constraint_v1.py")
    trie=_load("sav2_stage_p_trie_probe",ROOT/"src/pastila_scout/semantic_admission_v2/gate_f_trie_projector_v1.py")
    return dfa.StagePConstraintStateV1,trie.GateFTokenTrieProjectorOptimizedV1


def _build_projector(tokenizer):
    State,Trie=_constraint_types()
    pieces={item:tokenizer.decode([item],skip_special_tokens=True) for item in range(len(tokenizer))}
    projector=Trie(token_pieces=pieces,eos_token_id=tokenizer.eos_token_id,
        excluded_token_ids=set(tokenizer.all_special_ids)-{tokenizer.eos_token_id})
    prefix='{"stage_id":"PROPOSITION_LEDGER","coverage_decision":"COMPLETE","entries":[{"entry_id":"P1","entry_type":"REAL_WORLD_COMMITMENT","candidate_span":"'
    started=time.perf_counter();projector.prewarm((State(),State().feed(prefix)))
    return State,projector,time.perf_counter()-started


def run(request_path,response_path,prompt_path,lifecycle_path):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText,AutoTokenizer,BitsAndBytesConfig
    lifecycle={"inference_started":False,"inference_succeeded":False,"model_load_started":False,
        "model_load_succeeded":False,"constraint_active":True,"stage":"PROPOSITION_LEDGER"};_write(lifecycle_path,lifecycle)
    request=json.loads(request_path.read_text("utf-8"));tokenizer=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
    if tokenizer.pad_token_id is None: tokenizer.pad_token=tokenizer.eos_token
    State,projector,seconds=_build_projector(tokenizer);lifecycle.update(constraint_prewarm_succeeded=True,
        constraint_prewarm_seconds=seconds,trie_node_count=projector.trie_node_count);_write(lifecycle_path,lifecycle)
    quantization=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_compute_dtype=torch.bfloat16,bnb_4bit_use_double_quant=True)
    lifecycle["model_load_started"]=True;_write(lifecycle_path,lifecycle)
    model=AutoModelForImageTextToText.from_pretrained(MODEL,local_files_only=True,quantization_config=quantization,
        device_map={"":0},dtype=torch.bfloat16,attn_implementation="sdpa",low_cpu_mem_usage=True)
    model.model.vision_tower=None;model.model.multi_modal_projector=None
    model=PeftModel.from_pretrained(model,ADAPTER,is_trainable=False);model.eval();lifecycle["model_load_succeeded"]=True;_write(lifecycle_path,lifecycle)
    batch=tokenizer.apply_chat_template([{"role":"system","content":prompt_path.read_text("utf-8")},{"role":"user","content":request["prompt"]}],
        tokenize=True,add_generation_prompt=True,return_tensors="pt",return_dict=True)
    prompt_tokens=int(batch["input_ids"].shape[1]);batch={name:value.to("cuda") for name,value in batch.items()}
    def allowed(_batch_id,input_ids):
        decoded=tokenizer.decode(input_ids[prompt_tokens:].tolist(),skip_special_tokens=True)
        return list(projector.allowed_token_ids(State().feed(decoded)))
    lifecycle["inference_started"]=True;_write(lifecycle_path,lifecycle)
    with torch.inference_mode():
        generated=model.generate(**batch,do_sample=False,num_beams=1,repetition_penalty=1.0,max_new_tokens=int(request["max_new_tokens"]),
            eos_token_id=tokenizer.eos_token_id,pad_token_id=tokenizer.pad_token_id,use_cache=True,prefix_allowed_tokens_fn=allowed)
    tokens=generated[0,prompt_tokens:].cpu();lifecycle["inference_succeeded"]=True;_write(lifecycle_path,lifecycle)
    response_path.write_text(json.dumps({"output":tokenizer.decode(tokens,skip_special_tokens=True),"terminal_eos":bool(len(tokens) and int(tokens[-1])==tokenizer.eos_token_id),
        "constraint_active":True},ensure_ascii=False),"utf-8")


def _write(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+"\n","utf-8")


if __name__=="__main__":
    if len(sys.argv)!=5: raise SystemExit("invalid Stage P constrained runner arguments")
    run(*map(Path,sys.argv[1:5]))
