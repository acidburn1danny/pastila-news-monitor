"""Deterministic development inference for the R2 causal diagnostic adapters."""
from __future__ import annotations

import argparse, hashlib, json, os, sys, unicodedata
from pathlib import Path

ROWS=24
MAX_INPUT_TOKENS=3072
MAX_NEW_TOKENS=2048

def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def flat(root:Path):
    rows=[]
    for p in sorted(root.iterdir(),key=lambda x:x.name.encode()):
        if p.is_symlink() or not p.is_file(): raise ValueError("adapter/model closure")
        rows.append(p.name.encode()+b"\0"+p.stat().st_size.to_bytes(8,"big")+bytes.fromhex(sha(p.read_bytes())))
    return sha(b"".join(rows))

def load_requests(path:Path):
    rows=[json.loads(x) for x in path.read_bytes().splitlines()]
    if len(rows)!=ROWS or len({x["example_id"] for x in rows})!=ROWS: raise ValueError("request inventory")
    for row in rows:
        if row.get("split") not in {"INDEPENDENT_SELECTION_BENCHMARK","REPLAY_RETENTION"} or len(row.get("messages",[]))!=2: raise ValueError("evaluation split")
        if any(x.get("role")=="assistant" for x in row["messages"]): raise ValueError("answer leakage")
    return rows

def main():
    p=argparse.ArgumentParser(); p.add_argument("--model",type=Path,required=True); p.add_argument("--requests",type=Path,required=True); p.add_argument("--candidates",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    if os.environ.get("EDITOR_CAUSAL_DEVELOPMENT_AUTHORIZED")!="1" or a.output.is_symlink() or not a.output.is_dir() or any(a.output.iterdir()): raise ValueError("execution/output authority")
    manifest=json.loads(a.candidates.read_text(encoding="utf-8")); rows=load_requests(a.requests)
    if sha(a.requests.read_bytes())!=manifest["requests_sha256"]: raise ValueError("requests identity")
    candidates=manifest["candidates"]
    if len(candidates)!=13 or len({x["candidate_id"] for x in candidates})!=13: raise ValueError("candidate inventory")
    for item in candidates:
        path=Path(item["adapter_path"])
        if flat(path)!=item["adapter_identity"]: raise ValueError("adapter identity")

    # Isolated mode deliberately omits the script directory; only the bound,
    # read-only authority directory is added for the two frozen helpers.
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    import torch
    from peft import PeftModel
    from torch._native.registry import deregister_op_overrides
    from transformers import AutoModelForImageTextToText,AutoTokenizer,BitsAndBytesConfig
    from editor_core_bridge_json_constraint_v3 import BridgeJSONStateV3,BridgeTokenTrieV3
    from evaluate_editor_core_factual_setup_benchmark_v1 import validate_generated_response
    torch.manual_seed(0); torch.cuda.manual_seed_all(0); torch.use_deterministic_algorithms(True); deregister_op_overrides(disable_op_symbols="bmm")
    tok=AutoTokenizer.from_pretrained(a.model,local_files_only=True,fix_mistral_regex=True)
    if tok.pad_token_id is None: tok.pad_token=tok.eos_token
    base=AutoModelForImageTextToText.from_pretrained(a.model,local_files_only=True,quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_compute_dtype=torch.bfloat16,bnb_4bit_use_double_quant=True),device_map={"":0},dtype=torch.bfloat16,attn_implementation="sdpa",low_cpu_mem_usage=True)
    base.model.vision_tower=None; base.model.multi_modal_projector=None
    first=candidates[0]; model=PeftModel.from_pretrained(base,first["adapter_path"],adapter_name=first["candidate_id"],is_trainable=False)
    for item in candidates[1:]: model.load_adapter(item["adapter_path"],adapter_name=item["candidate_id"],is_trainable=False)
    pieces={i:tok.decode([i],skip_special_tokens=True,clean_up_tokenization_spaces=False) for i in range(len(tok))}
    trie=BridgeTokenTrieV3(token_pieces=pieces,eos_token_id=tok.eos_token_id,excluded_token_ids=set(tok.all_special_ids)-{tok.eos_token_id})
    receipts=[]
    for item in candidates:
        cid=item["candidate_id"]; model.set_adapter(cid); model.eval(); out=a.output/cid; out.mkdir(); responses=[]; observations=[]
        for index,row in enumerate(rows,1):
            payload=json.loads(row["messages"][1]["content"].split("\nINPUT=",1)[1]); enc=tok.apply_chat_template(row["messages"],tokenize=True,add_generation_prompt=True,return_tensors="pt",return_dict=True); n=int(enc["input_ids"].shape[1])
            if n>MAX_INPUT_TOKENS: raise ValueError("input ceiling")
            enc={k:v.to("cuda") for k,v in enc.items()}
            def allowed(_batch,input_ids):
                decoded=tok.decode(input_ids[n:].tolist(),skip_special_tokens=True,clean_up_tokenization_spaces=False)
                return list(trie.allowed_token_ids(BridgeJSONStateV3.start(payload).feed(decoded)))
            with torch.inference_mode(): generated=model.generate(**enc,do_sample=False,num_beams=1,max_new_tokens=MAX_NEW_TOKENS,repetition_penalty=1.0,prefix_allowed_tokens_fn=allowed,eos_token_id=tok.eos_token_id,pad_token_id=tok.pad_token_id,use_cache=True)
            tokens=generated[0,n:].cpu(); text=tok.decode(tokens,skip_special_tokens=True,clean_up_tokenization_spaces=False); eos=bool(len(tokens) and int(tokens[-1])==tok.eos_token_id)
            if not text or unicodedata.normalize("NFC",text)!=text: raise ValueError(f"invalid text {cid} {row['example_id']}")
            validate_generated_response(text,payload,eos)
            responses.append({"case_id":row["example_id"],"request_identity":payload["request_identity"],"response":text}); observations.append({"index":index,"case_id":row["example_id"],"output_tokens":len(tokens),"terminal_eos":eos,"response_sha256":sha(text.encode())})
        rb=b"".join(canonical(x)+b"\n" for x in responses); ob=b"".join(canonical(x)+b"\n" for x in observations); (out/"responses.jsonl").write_bytes(rb); (out/"observations.jsonl").write_bytes(ob)
        core={"schema":"editor-factual-setup-causal-development-inference","schema_version":1,"candidate_id":cid,"adapter_identity":item["adapter_identity"],"rows":24,"terminal_eos":sum(x["terminal_eos"] for x in observations),"responses_sha256":sha(rb),"observations_sha256":sha(ob),"requests_sha256":sha(a.requests.read_bytes()),"answer_key_accessed":False,"historical_holdout_accessed":False,"training_performed":False,"optimizer_steps":0}
        receipt={**core,"receipt_identity":sha(canonical(core))}; (out/"receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n"); receipts.append(receipt)
    program={"status":"PASS_13_DEVELOPMENT_BUNDLES","candidates":13,"rows":312,"terminal_eos":sum(x["terminal_eos"] for x in receipts),"receipts":[x["receipt_identity"] for x in receipts],"answer_key_accessed":False,"historical_holdout_accessed":False}
    (a.output/"program-terminal.json").write_text(json.dumps(program,sort_keys=True,indent=2)+"\n"); print(json.dumps(program,sort_keys=True))
if __name__=="__main__": main()
