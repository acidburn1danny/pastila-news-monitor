"""Bound inference-only worker for the EDITOR text-realizer base bake-off."""
from __future__ import annotations

import argparse, gc, hashlib, json, os, time
from pathlib import Path

from fixture_editor_core_source_bound_hybrid_feasibility_v1 import execute_with_fallback, validate_ledger

CANDIDATES = ("C0_R2_MINISTRAL", "C1_QWEN3_8B", "C2_QWEN25_7B")

def canonical(v: object) -> bytes:
    return json.dumps(v, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()

def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()

def atomic(path: Path, value: object) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes((json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode())
    tmp.replace(path)

def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x]

def prompt_for(ledger: dict) -> list[dict]:
    allowed = [{"atom_id": a["atom_id"], "quote": a["quote"]} for a in ledger["atoms"]
               if a["atom_id"] in ledger["realization_contract"]["allowed_atom_ids"]]
    payload = {"case_id": ledger["case_id"], "request": ledger["request"], "atoms": allowed}
    instruction = ("Realizează maximum 2–3 propoziții factuale exclusiv din ledger. Returnează numai JSON "
                   "conform schemei {\"case_id\":...,\"sentences\":[{\"text\":...,\"atom_ids\":[...]}]}. "
                   "Nu adăuga fapte, actori, numere sau certitudine. LEDGER=" +
                   json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return [{"role": "system", "content": "Ești EDITOR factual. Ledgerul este singura autoritate factuală."},
            {"role": "user", "content": instruction}]

def load(candidate: str, model_path: Path, tokenizer_path: Path, adapter_path: Path | None):
    import torch
    from transformers import AutoModelForCausalLM, AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True, use_fast=True,
                                              fix_mistral_regex=True)
    if tokenizer.pad_token_id is None: tokenizer.pad_token = tokenizer.eos_token
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                               bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    common = dict(local_files_only=True, device_map={"": 0}, dtype=torch.bfloat16,
                  attn_implementation="sdpa", low_cpu_mem_usage=True, quantization_config=quant)
    if candidate == "C0_R2_MINISTRAL":
        from peft import PeftModel
        base = AutoModelForImageTextToText.from_pretrained(model_path, **common)
        if hasattr(base.model, "vision_tower"): base.model.vision_tower = None
        if hasattr(base.model, "multi_modal_projector"): base.model.multi_modal_projector = None
        model = PeftModel.from_pretrained(base, adapter_path, is_trainable=False)
    else:
        model = AutoModelForCausalLM.from_pretrained(model_path, **common)
    model.eval(); return model, tokenizer

def generate(model, tokenizer, messages: list[dict], qwen3: bool) -> str:
    import torch
    kw = {"tokenize": False, "add_generation_prompt": True}
    if qwen3: kw["enable_thinking"] = False
    prompt = tokenizer.apply_chat_template(messages, **kw)
    encoded = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.inference_mode():
        out = model.generate(**encoded, do_sample=False, num_beams=1, max_new_tokens=768,
                             eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id,
                             use_cache=True)
    return tokenizer.decode(out[0, encoded.input_ids.shape[1]:], skip_special_tokens=True).strip()

def run(a: argparse.Namespace) -> None:
    if os.environ.get("EDITOR_BASE_BAKEOFF_SLOT_AUTHORIZED") != "1": raise SystemExit("authorization required")
    if a.candidate not in CANDIDATES: raise ValueError("candidate")
    if a.output.exists() and (a.output.is_symlink() or any(a.output.iterdir())): raise ValueError("nonempty output")
    a.output.mkdir(parents=True, exist_ok=True)
    ledgers = read_jsonl(a.artifacts / "editor-core-source-bound-hybrid-feasibility-v1-ledgers.jsonl")
    if len(ledgers) != 48: raise ValueError("ledger inventory")
    for x in ledgers: validate_ledger(x)
    started = time.time(); model, tokenizer = load(a.candidate, a.model, a.tokenizer, a.adapter)
    rows=[]
    try:
        for ledger in ledgers:
            raw = generate(model, tokenizer, prompt_for(ledger), a.candidate == "C1_QWEN3_8B")
            try:
                proposal=json.loads(raw); structural=isinstance(proposal,dict)
            except (json.JSONDecodeError, TypeError): proposal={"case_id":ledger["case_id"],"sentences":[]}; structural=False
            result=execute_with_fallback(ledger,proposal)
            rows.append({"case_id":ledger["case_id"],"candidate":a.candidate,"route":result["route"],
                         "text":result["text"],"verified":True,"structural_valid":structural,
                         "raw_sha256":sha(raw.encode()),"rejection_reasons":result["primary"]["reasons"]})
    except Exception as e:
        atomic(a.output/"failure.json", {"status":"CASE_RUNTIME_FAILURE","candidate":a.candidate,
               "example_id":ledger["case_id"],"phase":"INFERENCE","error_type":type(e).__name__,
               "invalid_payload_persisted":False,"eligible_evidence":False})
        raise
    atomic(a.output/"observations.json",rows)
    runtime={"candidate":a.candidate,"rows":len(rows),"elapsed_seconds":time.time()-started}
    atomic(a.output/"runtime.json",runtime)
    core={"status":"PASS_TERMINAL","candidate":a.candidate,"rows":48,
          "observations_sha256":sha((a.output/"observations.json").read_bytes()),"inference_only":True,
          "optimizer_created":False,"training_performed":False}
    atomic(a.output/"terminal.json",{**core,"receipt_identity":sha(canonical(core))})
    del model; gc.collect()

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--candidate",required=True); p.add_argument("--output",type=Path,required=True)
    p.add_argument("--model",type=Path,required=True); p.add_argument("--tokenizer",type=Path,required=True)
    p.add_argument("--adapter",type=Path); p.add_argument("--artifacts",type=Path,required=True)
    run(p.parse_args())
if __name__ == "__main__": main()
