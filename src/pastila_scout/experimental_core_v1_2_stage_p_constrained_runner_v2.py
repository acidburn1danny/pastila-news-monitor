"""Instrumented evaluation-only Stage P runner; lifecycle survives host timeout."""
from __future__ import annotations

import hashlib
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


def _types():
    dfa=_load("sav2_stage_p_dfa_lifecycle",ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_constraint_v1.py")
    trie=_load("sav2_stage_p_trie_lifecycle",ROOT/"src/pastila_scout/semantic_admission_v2/gate_f_trie_projector_v1.py")
    lifecycle=_load("sav2_append_lifecycle",ROOT/"src/pastila_scout/semantic_admission_v2/append_only_lifecycle_v1.py")
    return dfa.StagePConstraintStateV1,trie.GateFTokenTrieProjectorOptimizedV1,lifecycle.AppendOnlyLifecycleV1


def run(request_path,response_path,prompt_path,lifecycle_root):
    State,Trie,Lifecycle=_types();events=Lifecycle(lifecycle_root,actor="runner");events.emit("RUNNER_STARTED")
    try:
        request=json.loads(request_path.read_text("utf-8"));events.emit("REQUEST_VALIDATED",request_sha256=hashlib.sha256(request_path.read_bytes()).hexdigest())
        events.emit("TOKENIZER_LOAD_STARTED")
        from transformers import AutoTokenizer
        tokenizer=AutoTokenizer.from_pretrained(MODEL,local_files_only=True)
        if tokenizer.pad_token_id is None: tokenizer.pad_token=tokenizer.eos_token
        events.emit("TOKENIZER_LOAD_COMPLETED",vocabulary_size=len(tokenizer))
        events.emit("TRIE_BUILD_STARTED");pieces={item:tokenizer.decode([item],skip_special_tokens=True) for item in range(len(tokenizer))}
        projector=Trie(token_pieces=pieces,eos_token_id=tokenizer.eos_token_id,excluded_token_ids=set(tokenizer.all_special_ids)-{tokenizer.eos_token_id})
        events.emit("TRIE_BUILD_COMPLETED",trie_node_count=projector.trie_node_count)
        events.emit("PREWARM_STARTED");projector.prewarm((State(),));events.emit("PREWARM_COMPLETED",trie_cache_size=projector.cache_size)
        events.emit("MODEL_LOAD_STARTED")
        import torch
        from peft import PeftModel
        from transformers import AutoModelForImageTextToText,BitsAndBytesConfig
        quantization=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_compute_dtype=torch.bfloat16,bnb_4bit_use_double_quant=True)
        model=AutoModelForImageTextToText.from_pretrained(MODEL,local_files_only=True,quantization_config=quantization,
            device_map={"":0},dtype=torch.bfloat16,attn_implementation="sdpa",low_cpu_mem_usage=True)
        model.model.vision_tower=None;model.model.multi_modal_projector=None
        model=PeftModel.from_pretrained(model,ADAPTER,is_trainable=False);model.eval();events.emit("MODEL_LOAD_COMPLETED")
        batch=tokenizer.apply_chat_template([{"role":"system","content":prompt_path.read_text("utf-8")},{"role":"user","content":request["prompt"]}],
            tokenize=True,add_generation_prompt=True,return_tensors="pt",return_dict=True)
        prompt_tokens=int(batch["input_ids"].shape[1]);batch={name:value.to("cuda") for name,value in batch.items()}
        events.emit("PROMPT_TOKENIZED",prompt_tokens=prompt_tokens);generation_started=time.monotonic();heartbeat_at=generation_started;last_heartbeat_tokens=-1
        def allowed(_batch_id,input_ids):
            nonlocal heartbeat_at,last_heartbeat_tokens
            generated_ids=input_ids[prompt_tokens:].tolist();decoded=tokenizer.decode(generated_ids,skip_special_tokens=True)
            state=State().feed(decoded);allowed_ids=projector.allowed_token_ids(state);now=time.monotonic()
            if len(generated_ids)-last_heartbeat_tokens>=16 or now-heartbeat_at>=10:
                events.emit("GENERATION_HEARTBEAT",generated_tokens=len(generated_ids),decoded_utf8_bytes=len(decoded.encode()),
                    decoded_sha256=hashlib.sha256(decoded.encode()).hexdigest(),partial_output=decoded,dfa_mode=state.mode,
                    entry_count=state.entry_count,trie_cache_size=projector.cache_size,allowed_token_count=len(allowed_ids),
                    generation_elapsed_seconds=round(now-generation_started,6))
                last_heartbeat_tokens=len(generated_ids);heartbeat_at=now
            return list(allowed_ids)
        events.emit("GENERATION_STARTED",maximum_new_tokens=int(request["max_new_tokens"]));
        with torch.inference_mode():
            generated=model.generate(**batch,do_sample=False,num_beams=1,repetition_penalty=1.0,max_new_tokens=int(request["max_new_tokens"]),
                eos_token_id=tokenizer.eos_token_id,pad_token_id=tokenizer.pad_token_id,use_cache=True,prefix_allowed_tokens_fn=allowed)
        tokens=generated[0,prompt_tokens:].cpu();output=tokenizer.decode(tokens,skip_special_tokens=True)
        terminal=bool(len(tokens) and int(tokens[-1])==tokenizer.eos_token_id)
        if terminal: events.emit("TERMINAL_EOS",generated_tokens=len(tokens),output_sha256=hashlib.sha256(output.encode()).hexdigest())
        response_path.write_text(json.dumps({"output":output,"terminal_eos":terminal,"constraint_active":True},ensure_ascii=False),"utf-8")
        events.emit("RESPONSE_PERSISTED",response_sha256=hashlib.sha256(response_path.read_bytes()).hexdigest(),terminal_eos=terminal)
    except Exception as exc:
        events.emit("RUNNER_EXCEPTION",exception_type=type(exc).__name__,exception_message=str(exc)[:1000]);raise


if __name__=="__main__":
    if len(sys.argv)!=5: raise SystemExit("usage: runner REQUEST RESPONSE PROMPT DURABLE_LIFECYCLE_ROOT")
    run(*map(Path,sys.argv[1:5]))
