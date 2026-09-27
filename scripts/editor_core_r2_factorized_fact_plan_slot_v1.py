"""Bound inference-only slot executor for the factorized fact-plan diagnostic."""
from __future__ import annotations
import argparse, json, os
from pathlib import Path

INTERVENTIONS=("I0_ONE_PASS_R2","I1_ORACLE_PLAN_SCORE","I2_ORACLE_PLAN_TO_R2_SETUP","I3_R2_PLAN_TO_R2_SETUP")
SEEDS=(161803,271828,314159)

def atomic_json(path:Path,value):
 tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8"); tmp.replace(path)

def fixture(intervention:str,seed:int,out:Path):
 if intervention not in INTERVENTIONS or seed not in SEEDS: raise ValueError("unauthorized slot")
 if out.exists() and (out.is_symlink() or any(out.iterdir())): raise ValueError("output root")
 out.mkdir(parents=True,exist_ok=True)
 atomic_json(out/"terminal.json",{"status":"PASS_FIXTURE_SLOT","slot_id":f"{intervention}__seed_{seed}","model_loaded":False,"optimizer_created":False,"training_performed":False})

def real(args):
 if os.environ.get("FACTORIZED_FACT_PLAN_SLOT_AUTHORIZED")!="1": raise SystemExit("separate owner authorization required")
 # Imports and model load intentionally occur only beyond the authorization gate.
 import torch
 from transformers import AutoModelForCausalLM,AutoTokenizer,BitsAndBytesConfig
 from peft import PeftModel
 from editor_core_r2_factorized_fact_plan_runtime_v1 import validate_plan
 torch.manual_seed(args.seed)
 tok=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True,use_fast=True)
 base=AutoModelForCausalLM.from_pretrained(args.model,local_files_only=True,device_map="auto",quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_compute_dtype=torch.bfloat16))
 model=PeftModel.from_pretrained(base,args.parent,is_trainable=False); model.eval()
 cases=[json.loads(x) for x in (args.artifacts/"editor-core-r2-factorized-fact-plan-diagnostic-v1-cases.jsonl").read_text(encoding="utf-8").splitlines()]
 plans={x["case_id"]:x for x in map(json.loads,(args.artifacts/"editor-core-r2-factorized-fact-plan-diagnostic-v1-oracle-plans.jsonl").read_text(encoding="utf-8").splitlines())}
 rows=[]
 def generate(messages,max_new=768):
  text=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True); enc=tok(text,return_tensors="pt").to(model.device)
  with torch.inference_mode(): ids=model.generate(**enc,do_sample=False,num_beams=1,max_new_tokens=max_new,eos_token_id=tok.eos_token_id,pad_token_id=tok.pad_token_id,use_cache=True)
  return tok.decode(ids[0,enc.input_ids.shape[1]:],skip_special_tokens=True).strip()
 for case in cases:
  cid=case["case_id"]; oracle=plans[cid]; result={"case_id":cid,"intervention":args.intervention}
  if args.intervention=="I0_ONE_PASS_R2": result["setup"]=generate(case["messages"])
  elif args.intervention=="I1_ORACLE_PLAN_SCORE":
   validate_plan(oracle,case); prompt=tok.apply_chat_template(case["messages"],tokenize=False,add_generation_prompt=True); target=json.dumps(oracle,ensure_ascii=False,sort_keys=True,separators=(",",":"))+tok.eos_token
   p=tok(prompt,return_tensors="pt").to(model.device); full=tok(prompt+target,return_tensors="pt").to(model.device); labels=full.input_ids.clone(); labels[:,:p.input_ids.shape[1]]=-100
   with torch.inference_mode(): loss=model(**full,labels=labels).loss.item()
   result.update(plan_identity=oracle["plan_identity"],teacher_forced_nll=loss)
  elif args.intervention=="I2_ORACLE_PLAN_TO_R2_SETUP":
   validate_plan(oracle,case); msgs=case["messages"]+[{"role":"assistant","content":"FACT_PLAN="+json.dumps(oracle,ensure_ascii=False,sort_keys=True,separators=(",",":"))},{"role":"user","content":"Realizează setup-ul factual de 2–3 propoziții exclusiv din FACT_PLAN. Returnează obiectul JSON cerut de contract."}]; result.update(plan_identity=oracle["plan_identity"],setup=generate(msgs))
  else:
   plan_text=generate(case["messages"]+[{"role":"user","content":"Construiește mai întâi un fact-plan JSON conform schemei publicate; fără setup."}]); plan=json.loads(plan_text); check=validate_plan(plan,case); msgs=case["messages"]+[{"role":"assistant","content":"FACT_PLAN="+json.dumps(plan,ensure_ascii=False,sort_keys=True,separators=(",",":"))},{"role":"user","content":"Realizează setup-ul factual de 2–3 propoziții exclusiv din FACT_PLAN. Returnează obiectul JSON cerut de contract."}]; result.update(plan=plan,plan_validation=check,setup=generate(msgs))
  rows.append(result)
 atomic_json(args.output/"observations.json",rows); atomic_json(args.output/"terminal.json",{"status":"PASS_TERMINAL","slot_id":f"{args.intervention}__seed_{args.seed}","rows":len(rows),"optimizer_created":False,"training_performed":False})

def main():
 p=argparse.ArgumentParser(); p.add_argument("--intervention",required=True); p.add_argument("--seed",type=int,required=True); p.add_argument("--output",type=Path,required=True); p.add_argument("--fixture-only",action="store_true"); p.add_argument("--execute-authorized",action="store_true"); p.add_argument("--model",type=Path); p.add_argument("--tokenizer",type=Path); p.add_argument("--parent",type=Path); p.add_argument("--artifacts",type=Path)
 a=p.parse_args()
 if a.fixture_only: fixture(a.intervention,a.seed,a.output); return
 if not a.execute_authorized or not all((a.model,a.tokenizer,a.parent,a.artifacts)): raise SystemExit("separate owner authorization required")
 if a.output.exists() and (a.output.is_symlink() or any(a.output.iterdir())): raise ValueError("output root")
 a.output.mkdir(parents=True,exist_ok=True); real(a)
if __name__=="__main__": main()
