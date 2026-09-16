"""Fail-closed V10 development gate using the published execution contract."""

from __future__ import annotations

import hashlib, importlib.util, json, os, sys, unicodedata
from collections import Counter
from pathlib import Path

EXPECTED_ENV={"ADAPTER_SHA256","CUBLAS_WORKSPACE_CONFIG","CONTRACT_SHA256","CUDA_VISIBLE_DEVICES","DEVELOPMENT_SHA256","EDITORIAL_SHA256","HF_HUB_OFFLINE","LAUNCHER_SHA256","MODEL_SHA256","PATH","PYTHONHASHSEED","RUNNER_SHA256","TOKENIZERS_PARALLELISM","TRANSFORMERS_OFFLINE","TRITON_CACHE_DIR","TRITON_LIBCUDA_PATH"}
def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()
def canonical(value:object)->bytes:return json.dumps(value,ensure_ascii=False,allow_nan=False,separators=(",", ":"),sort_keys=True).encode()
def flat_manifest(root:Path)->str:
    rows=[]
    for path in sorted(root.iterdir(),key=lambda p:p.name.encode()):
        if path.is_symlink() or not path.is_file():raise SystemExit("development object closure mismatch")
        data=path.read_bytes();rows.append(path.name.encode()+b"\0"+len(data).to_bytes(8,"big")+hashlib.sha256(data).digest())
    return sha(b"".join(rows))
def repeated_ngram_ceiling(text:str,width:int=8)->int:
    words=text.split()
    return 1 if len(words)<width else max(Counter(tuple(words[i:i+width]) for i in range(len(words)-width+1)).values())
def load_contract(path:Path):
    spec=importlib.util.spec_from_file_location("bound_v10_contract",path); module=importlib.util.module_from_spec(spec)
    if spec.loader is None:raise SystemExit("contract load mismatch")
    spec.loader.exec_module(module);return module

def main()->int:
    if len(sys.argv)!=9 or set(os.environ)!=EXPECTED_ENV:raise SystemExit("development gate invocation mismatch")
    model,adapter,probes,output,contract_path,editorial_path=map(Path,sys.argv[1:7]);candidate=sys.argv[7];materialization=sys.argv[8]
    if materialization not in {"A","B"} or any(output.iterdir()):raise SystemExit("development gate output mismatch")
    bindings=((flat_manifest(model),"MODEL_SHA256"),(flat_manifest(adapter),"ADAPTER_SHA256"),(sha(probes.read_bytes()),"DEVELOPMENT_SHA256"),(sha(contract_path.read_bytes()),"CONTRACT_SHA256"),(sha(editorial_path.read_bytes()),"EDITORIAL_SHA256"),(sha(Path(__file__).read_bytes()),"RUNNER_SHA256"))
    if any(value!=os.environ[key] for value,key in bindings):raise SystemExit("development authority binding mismatch")
    contract=load_contract(contract_path); editorial=editorial_path.read_bytes(); rows=[json.loads(line) for line in probes.read_text("utf-8").splitlines()]
    if len(rows)!=72 or any(row.get("split")!="DEVELOPMENT" or row.get("candidate")!=candidate for row in rows):raise SystemExit("development probe closure mismatch")
    rendered=[]
    for row in rows:
        messages=list(contract.render_development_messages(candidate=candidate,editorial_prompt=editorial,user_prompt=row["user_prompt"]))
        if messages!=row["messages"] or contract.assert_phase_equivalence(candidate=candidate,editorial_prompt=editorial,user_prompt=row["user_prompt"])!=contract.projection_identity(messages):raise SystemExit("V10 projection mismatch")
        rendered.append(messages)
    policy=contract.GENERATION_POLICY
    if policy["maximum_utf8_bytes"]!=6268 or policy["max_new_tokens"]!=6268 or policy["do_sample"] is not False or policy["num_beams"]!=1:raise SystemExit("generation policy mismatch")
    import torch
    from peft import PeftModel
    from torch._native.registry import deregister_op_overrides
    from transformers import AutoModelForImageTextToText,AutoTokenizer,BitsAndBytesConfig
    torch.manual_seed(0);torch.use_deterministic_algorithms(True);deregister_op_overrides(disable_op_symbols="bmm")
    tokenizer=AutoTokenizer.from_pretrained(model,local_files_only=True,fix_mistral_regex=True)
    if tokenizer.pad_token_id is None:tokenizer.pad_token=tokenizer.eos_token
    loaded=AutoModelForImageTextToText.from_pretrained(model,local_files_only=True,quantization_config=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_compute_dtype=torch.bfloat16,bnb_4bit_use_double_quant=True),device_map={"":0},dtype=torch.bfloat16,attn_implementation="sdpa",low_cpu_mem_usage=True)
    loaded.model.vision_tower=None;loaded.model.multi_modal_projector=None;loaded=PeftModel.from_pretrained(loaded,adapter,is_trainable=False);loaded.eval();observations=[]
    for index,(row,messages) in enumerate(zip(rows,rendered,strict=True),1):
        encoded=tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,return_tensors="pt",return_dict=True);input_tokens=int(encoded["input_ids"].shape[1])
        if input_tokens>policy["maximum_input_tokens"]:raise SystemExit("development input token ceiling exceeded")
        encoded={k:v.to("cuda") for k,v in encoded.items()}
        with torch.inference_mode():generated=loaded.generate(**encoded,do_sample=False,num_beams=1,repetition_penalty=float(policy["repetition_penalty"]),max_new_tokens=policy["max_new_tokens"],eos_token_id=tokenizer.eos_token_id,pad_token_id=tokenizer.pad_token_id,use_cache=policy["use_cache"])
        tokens=generated[0,input_tokens:].cpu();terminal_eos=bool(len(tokens) and int(tokens[-1])==tokenizer.eos_token_id);text=tokenizer.decode(tokens,skip_special_tokens=True);raw=text.encode()
        try:parsed=json.loads(text);canonical_json=contract.canonical(parsed)==raw
        except (ValueError,TypeError):canonical_json=False
        observation={"index":index,"example_id":row["example_id"],"projection_identity":contract.projection_identity(messages),"terminal_eos":terminal_eos,"canonical_json":canonical_json,"nfc":unicodedata.normalize("NFC",text)==text,"within_byte_ceiling":len(raw)<=policy["maximum_utf8_bytes"],"exact_target":text==row["expected"],"input_tokens":input_tokens,"output_tokens":len(tokens),"output_bytes":len(raw),"repeated_8gram_ceiling":repeated_ngram_ceiling(text),"output_sha256":sha(raw)}
        observations.append(observation);(output/f"{index:03d}.json").write_bytes(canonical(observation))
    passed=all(row["terminal_eos"] and row["canonical_json"] and row["nfc"] and row["within_byte_ceiling"] and row["repeated_8gram_ceiling"]<=3 for row in observations)
    core={"schema":"pastila-production-core-successor-development-gate","schema_version":10,"materialization":materialization,"candidate":candidate,"adapter_sha256":os.environ["ADAPTER_SHA256"],"development_sha256":os.environ["DEVELOPMENT_SHA256"],"contract_sha256":os.environ["CONTRACT_SHA256"],"editorial_sha256":os.environ["EDITORIAL_SHA256"],"launcher_sha256":os.environ["LAUNCHER_SHA256"],"runner_sha256":os.environ["RUNNER_SHA256"],"rows":72,"terminal_eos_passed":sum(r["terminal_eos"] for r in observations),"canonical_json_passed":sum(r["canonical_json"] for r in observations),"nfc_passed":sum(r["nfc"] for r in observations),"byte_ceiling_passed":sum(r["within_byte_ceiling"] for r in observations),"exact_target_passed":sum(r["exact_target"] for r in observations),"anti_repetition_passed":sum(r["repeated_8gram_ceiling"]<=3 for r in observations),"status":"PASS" if passed else "FAIL_CLOSED","qualification_attempt_consumed":False,"adjudication_performed":False,"promotion_effect":False}
    receipt={**core,"gate_identity":sha(canonical(core))};(output/"gate-receipt.json").write_bytes(canonical(receipt))
    if not passed:raise SystemExit("development gate failed closed")
    return 0
if __name__=="__main__":raise SystemExit(main())
