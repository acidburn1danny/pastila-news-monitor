"""Clean-room V0/V1/V2 runtime diagnostic using the frozen R2 realizer."""
from __future__ import annotations

import argparse, hashlib, json, re, time, unicodedata
from pathlib import Path

ARMS = ("V0_FULL_SOURCE", "V1_DETERMINISTIC_EVIDENCE", "V2_DETERMINISTIC_PLUS_BOUNDED_SELECTOR")
BUNDLE_ID = "9fb26a21251073c0cbbeee5a9036082ca0e5f07869b7e9998f9dd935647d961e"
LOCK_ID = "53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f"

def canonical(v): return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",",":")).encode()
def sha(b): return hashlib.sha256(b).hexdigest()
def norm(s): return " ".join("".join(c for c in unicodedata.normalize("NFKD",s.casefold()) if not unicodedata.combining(c)).split())
def nums(s): return set(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?(?:\s*%)?(?!\w)",s))
def atomic(path,value):
    tmp=path.with_suffix(path.suffix+".tmp"); tmp.write_bytes(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2).encode()+b"\n"); tmp.replace(path)

def verify_output(text, selected, required):
    source="\n".join(x["text"] for x in selected); ntext=norm(text)
    unbound=sorted(nums(text)-nums(source))
    voice=any(x in ntext for x in ("sarcasm","ironic","ridicol","halal","bravo lor"))
    req=[]
    for span in required:
        critical=sum(span["critical_literals"].values(),[])
        if critical:
            hit=all(norm(x) in ntext for x in critical)
        else:
            words=[w for w in re.findall(r"\w+",norm(span["text"])) if len(w)>4]
            hit=sum(w in ntext for w in words)>=min(2,len(words))
        req.append(hit)
    return {"factual_safe":not unbound and not voice,"unbound_numbers":unbound,"voice_content":voice,
            "required_span_hits":sum(req),"required_span_total":len(req),"sufficient":all(req)}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--closure",type=Path,required=True); p.add_argument("--bundle",type=Path,required=True); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    if a.output.exists(): raise ValueError("output root must be new")
    a.output.mkdir(parents=True)
    bundle=json.loads(a.bundle.read_text(encoding="utf-8")); lock=json.loads((a.closure/"dependency-lock.json").read_text())
    if bundle["bundle_identity"]!=BUNDLE_ID or lock["lock_identity"]!=LOCK_ID or len(bundle["fixtures"])!=48: raise ValueError("identity/inventory mismatch")
    import torch
    from peft import PeftModel
    from transformers import AutoModelForImageTextToText,AutoTokenizer,BitsAndBytesConfig
    tok=AutoTokenizer.from_pretrained(a.closure/lock["layout"]["tokenizer"],local_files_only=True,use_fast=True,fix_mistral_regex=True)
    if tok.pad_token_id is None: tok.pad_token=tok.eos_token
    quant=BitsAndBytesConfig(load_in_4bit=True,bnb_4bit_quant_type="nf4",bnb_4bit_compute_dtype=torch.bfloat16,bnb_4bit_use_double_quant=True)
    base=AutoModelForImageTextToText.from_pretrained(a.closure/lock["layout"]["base_model"],local_files_only=True,device_map={"":0},dtype=torch.bfloat16,attn_implementation="sdpa",low_cpu_mem_usage=True,quantization_config=quant)
    if hasattr(base.model,"vision_tower"): base.model.vision_tower=None
    if hasattr(base.model,"multi_modal_projector"): base.model.multi_modal_projector=None
    model=PeftModel.from_pretrained(base,a.closure/lock["layout"]["adapter"],is_trainable=False); model.eval()
    rows=[]; started=time.time()
    for fixture in bundle["fixtures"]:
      by_id={x["span_id"]:x for x in fixture["source_packet"]["spans"]}
      required=[by_id[x] for x in fixture["arms"]["ORACLE_UPPER_BOUND"]]
      for arm in ARMS:
        selected=[by_id[x] for x in fixture["arms"][arm]]
        source="\n".join(f"[{x['span_id']}] {x['text']}" for x in selected)
        instruction=("Transformă exclusiv sursele de mai jos într-un setup factual concis, uzual 2–3 propoziții. "
          "Păstrează actorii, cifrele, atribuirea, modalitatea și statutul procedural. Nu adăuga informații. "
          f"Returnează numai JSON conform schemei {{\"case_id\":\"{fixture['case_id']}\",\"text\":\"...\"}}.\nSURSE:\n{source}")
        messages=[{"role":"system","content":"Ești EDITOR factual. Sursele furnizate sunt singura autoritate factuală."},{"role":"user","content":instruction}]
        prompt=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True); enc=tok(prompt,return_tensors="pt").to(model.device)
        with torch.inference_mode(): out=model.generate(**enc,do_sample=False,num_beams=1,max_new_tokens=256,eos_token_id=tok.eos_token_id,pad_token_id=tok.pad_token_id,use_cache=True)
        raw=tok.decode(out[0,enc.input_ids.shape[1]:],skip_special_tokens=True).strip()
        try: obj=json.loads(raw); structural=isinstance(obj,dict) and obj.get("case_id")==fixture["case_id"] and isinstance(obj.get("text"),str); text=obj["text"] if structural else raw
        except Exception: structural=False; text=raw
        checks=verify_output(text,selected,required); accepted=structural and checks["factual_safe"] and checks["sufficient"]
        route="ACCEPTED_R2" if accepted else ("EXTRACTIVE_FALLBACK" if selected else "ABSTAIN")
        rows.append({"case_id":fixture["case_id"],"partition":fixture["partition"],"failure_class":fixture["failure_class"],"arm":arm,
          "selected_span_count":len(selected),"source_bytes":len(source.encode()),"context_tokens":int(enc.input_ids.shape[1]),"structural_valid":structural,
          **checks,"route":route,"raw_sha256":sha(raw.encode()),"text_sha256":sha(text.encode())})
    atomic(a.output/"observations.json",rows)
    summary={}
    for arm in ARMS:
      x=[r for r in rows if r["arm"]==arm]; summary[arm]={"rows":len(x),"factual_safety_rate":sum(r["factual_safe"] for r in x)/len(x),
       "primary_sufficiency_rate":sum(r["sufficient"] for r in x)/len(x),"structural_rate":sum(r["structural_valid"] for r in x)/len(x),
       "fallback_rate":sum(r["route"]=="EXTRACTIVE_FALLBACK" for r in x)/len(x),"abstention_rate":sum(r["route"]=="ABSTAIN" for r in x)/len(x),
       "mean_context_tokens":sum(r["context_tokens"] for r in x)/len(x),"max_context_tokens":max(r["context_tokens"] for r in x),
       "mean_source_bytes":sum(r["source_bytes"] for r in x)/len(x)}
    v0,v2=summary[ARMS[0]],summary[ARMS[2]]
    material=(v2["factual_safety_rate"]>v0["factual_safety_rate"] or v2["primary_sufficiency_rate"]>v0["primary_sufficiency_rate"])
    reasons=[]
    if any(not r["factual_safe"] and r["route"]=="ACCEPTED_R2" for r in rows): reasons.append("ANY_UNBOUND_ACCEPTED_FACT")
    if not material: reasons.append("NO_SAFETY_OR_SUFFICIENCY_ADVANTAGE_OVER_V0")
    decision="STOP" if reasons else ("REVISE" if .7536231884057971<.9 or v2["fallback_rate"]>.25 else "CONTINUE")
    core={"schema":"editor-vnext-minimal-source-authority-runtime-result","schema_version":1,"status":"PASS_TERMINAL","decision":decision,"reasons":reasons,
      "bundle_identity":BUNDLE_ID,"lock_identity":LOCK_ID,"rows":len(rows),"summary":summary,"v1_required_span_recall":.7536231884057971,"selector_case_rate":.5,
      "elapsed_seconds":time.time()-started,"training_performed":False,"optimizer_created":False,"legacy_dependency_count":0,
      "claim_limits":["DEVELOPMENT_FIXTURES_ONLY","DETERMINISTIC_LITERAL_AND_REQUIRED_SPAN_SCORING","NO_NATURALISTIC_TRANSFER","NO_ACTIVE_ARCHITECTURE_INTEGRATION"]}
    core["result_identity"]=sha(canonical(core)); atomic(a.output/"terminal-result.json",core); print(json.dumps(core,ensure_ascii=False,sort_keys=True))

if __name__=="__main__": main()
