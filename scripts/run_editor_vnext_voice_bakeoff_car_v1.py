"""Bound inference-only worker for one frozen VOICE candidate slice."""
from __future__ import annotations
import argparse, gc, hashlib, json, os, time
from pathlib import Path

def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def atomic(path,value):
    path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("wb") as stream:
        stream.write(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n")
        stream.flush(); os.fsync(stream.fileno())
    tmp.replace(path)
def rows(path): return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
def prompt(case):
    return [{"role":"system","content":"Ești VOICE pentru Pastila Acidă. Primești un setup factual imuabil. Scrie numai commentary separat. Nu adăuga actori, evenimente, cifre, date, statut sau alte afirmații factuale. Poți abstine. Returnează JSON: {\"commentary\": string, \"abstained\": boolean}."},{"role":"user","content":"EDITOR_SETUP_IMMUTABLE:\n"+case["factual_setup"]+"\nINSTRUCȚIUNE:\n"+case["bounded_voice_instruction"]}]
def load(candidate,product):
 import torch
 from transformers import AutoModelForCausalLM,AutoModelForImageTextToText,AutoTokenizer,BitsAndBytesConfig
 q=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_compute_dtype=torch.bfloat16,bnb_4bit_use_double_quant=True); common=dict(local_files_only=True,device_map={"":0},dtype=torch.bfloat16,attn_implementation="sdpa",low_cpu_mem_usage=True,quantization_config=q)
 if candidate=="V0_R2_MINISTRAL_CONTROL":
  from peft import PeftModel
  root=product/"components/r2-reference-v1"; tok=root/"objects/tokenizer"; base=root/"objects/base-model"; adapter=root/"objects/adapter"; tokenizer=AutoTokenizer.from_pretrained(tok,local_files_only=True,use_fast=True,fix_mistral_regex=True); model=AutoModelForImageTextToText.from_pretrained(base,**common); model=PeftModel.from_pretrained(model,adapter,is_trainable=False)
 else:
  layout="qwen3-8b" if candidate=="V1_QWEN3_8B_NON_THINKING" else "qwen2.5-7b-instruct"; root=product/"components/voice-candidates-v1"/layout; tokenizer=AutoTokenizer.from_pretrained(root,local_files_only=True,use_fast=True); model=AutoModelForCausalLM.from_pretrained(root,**common)
 if tokenizer.pad_token_id is None: tokenizer.pad_token=tokenizer.eos_token
 model.eval(); return model,tokenizer
def run(a):
 if os.environ.get("VNEXT_VOICE_BAKEOFF_AUTHORIZED")!="1": raise SystemExit("authorization env missing")
 if a.output.exists(): raise ValueError("output root must be absent")
 dispatch=[x for x in rows(a.dispatch) if x["candidate_id"]==a.candidate]; cases={x["case_id"]:x for x in rows(a.cases)}
 if len(dispatch)!=72: raise ValueError("candidate dispatch must be 72")
 model,tokenizer=load(a.candidate,a.product_root); started=time.time()
 import torch; torch.cuda.reset_peak_memory_stats()
 try:
  for d in dispatch:
   torch_seed=d["seed"]; torch.manual_seed(torch_seed); torch.cuda.manual_seed_all(torch_seed); case_started=time.time()
   messages=prompt(cases[d["case_id"]]); kw={"tokenize":False,"add_generation_prompt":True};
   if a.candidate=="V1_QWEN3_8B_NON_THINKING": kw["enable_thinking"]=False
   text=tokenizer.apply_chat_template(messages,**kw); enc=tokenizer(text,return_tensors="pt").to(model.device)
   with torch.inference_mode(): out=model.generate(**enc,do_sample=False,num_beams=1,max_new_tokens=256,eos_token_id=tokenizer.eos_token_id,pad_token_id=tokenizer.pad_token_id,use_cache=True)
   raw=tokenizer.decode(out[0,enc.input_ids.shape[1]:],skip_special_tokens=True).strip()
   try: parsed=json.loads(raw); commentary=parsed["commentary"]; abstained=bool(parsed["abstained"]); assert isinstance(commentary,str)
   except Exception as e: raise RuntimeError(f"STRUCTURAL_OUTPUT:{d['slot_identity']}:{type(e).__name__}")
   elapsed=time.time()-case_started
   if elapsed>30: raise RuntimeError(f"LATENCY_LIMIT:{d['slot_identity']}:{elapsed}")
   core={"slot_identity":d["slot_identity"],"grant_identity":d["grant_identity"],"dispatch_identity":d["dispatch_identity"],"input_sha256":sha(canonical(cases[d["case_id"]])),"decoding_identity":d["decoding_identity"],"blind_label":d["blind_label"],"commentary":commentary,"abstained":abstained,"candidate_receipt":{"candidate_id":a.candidate,"revision":d["revision"],"tokenizer_sha256":d["tokenizer_sha256"]},"raw_sha256":sha(raw.encode()),"elapsed_seconds":elapsed,"terminal_state":"PASS"}
   output_sha=sha(canonical(core)); atomic(a.output/d["output_relative_path"],{**core,"output_sha256":output_sha,"receipt_identity":sha(canonical({**core,"output_sha256":output_sha}))})
  peak=torch.cuda.max_memory_allocated()/1024**3
  if peak>14.5: raise RuntimeError(f"VRAM_LIMIT:{peak}")
  summary={"candidate_id":a.candidate,"outputs":72,"elapsed_seconds":time.time()-started,"peak_vram_gib":peak,"terminal_state":"PASS","inference_only":True,"training":False,"optimizer":False}; atomic(a.output/f"terminal-{a.candidate}.json",{**summary,"receipt_identity":sha(canonical(summary))})
 except Exception as e:
  atomic(a.output/f"failure-{a.candidate}.json",{"candidate_id":a.candidate,"error_type":type(e).__name__,"message":str(e),"terminal_state":"FAIL","partial_eligible_evidence":False}); raise
 finally: del model; gc.collect()
def main():
 p=argparse.ArgumentParser(); p.add_argument("--candidate",required=True); p.add_argument("--dispatch",type=Path,required=True); p.add_argument("--cases",type=Path,required=True); p.add_argument("--product-root",type=Path,required=True); p.add_argument("--output",type=Path,required=True); run(p.parse_args())
if __name__=="__main__": main()
