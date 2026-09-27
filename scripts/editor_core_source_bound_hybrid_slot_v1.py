"""Bound per-slot executor for the source-bound hybrid feasibility diagnostic."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from editor_core_source_bound_hybrid_runtime_v1 import ARMS, SEEDS
from fixture_editor_core_source_bound_hybrid_feasibility_v1 import (
    execute_with_fallback,
    extractive_proposal,
    validate_ledger,
    verify_proposal,
)


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def fixture(arm: str, seed: int) -> dict:
    if arm not in ARMS or seed not in SEEDS:
        raise ValueError("unauthorized slot")
    return {"status": "PASS_FIXTURE_SLOT", "slot_id": f"{arm}__seed_{seed}", "model_loaded": False,
            "inference_performed": False, "optimizer_created": False, "training_performed": False}


def model_proposal(model, tokenizer, ledger: dict, arm: str) -> dict:
    if arm == "B0_R2_ONE_PASS":
        material = "\n".join(span["text"] for span in ledger["source_spans"])
        instruction = (f"CERINȚĂ: {ledger['request']}\nSURSE:\n{material}\n"
                       "Returnează numai JSON: {\"case_id\":...,\"text\":...}. Textul are 2–3 propoziții.")
    else:
        allowed = [{"atom_id": atom["atom_id"], "quote": atom["quote"]}
                   for atom in ledger["atoms"] if atom["atom_id"] in ledger["realization_contract"]["allowed_atom_ids"]]
        instruction = ("Realizează 2–3 propoziții exclusiv din ledger. Returnează numai JSON conform schemei "
                       "{\"case_id\":...,\"sentences\":[{\"text\":...,\"atom_ids\":[...]}]}.\nLEDGER=" +
                       json.dumps({"case_id": ledger["case_id"], "request": ledger["request"], "atoms": allowed},
                                  ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    messages = [{"role": "system", "content": "Ești EDITOR factual. Nu adăuga fapte."},
                {"role": "user", "content": instruction}]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    encoded = tokenizer(prompt, return_tensors="pt").to(model.device)
    import torch
    with torch.inference_mode():
        generated = model.generate(**encoded, do_sample=False, num_beams=1, max_new_tokens=768,
                                   eos_token_id=tokenizer.eos_token_id,
                                   pad_token_id=tokenizer.pad_token_id, use_cache=True)
    raw = tokenizer.decode(generated[0, encoded.input_ids.shape[1]:], skip_special_tokens=True).strip()
    return json.loads(raw)


def real(args: argparse.Namespace) -> None:
    if os.environ.get("SOURCE_BOUND_HYBRID_SLOT_AUTHORIZED") != "1":
        raise SystemExit("separate owner authorization required")
    if args.output.exists() and (args.output.is_symlink() or any(args.output.iterdir())):
        raise ValueError("slot staging root must be new or empty")
    args.output.mkdir(parents=True, exist_ok=True)
    ledgers = read_jsonl(args.artifacts / "editor-core-source-bound-hybrid-feasibility-v1-ledgers.jsonl")
    for ledger in ledgers:
        validate_ledger(ledger)
    model = tokenizer = None
    if args.arm != "B1_EXTRACTIVE_BASELINE":
        import torch
        from peft import PeftModel
        from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig
        tokenizer = AutoTokenizer.from_pretrained(args.tokenizer, local_files_only=True, use_fast=True,
                                                  fix_mistral_regex=True)
        if tokenizer.pad_token_id is None:
            tokenizer.pad_token = tokenizer.eos_token
        base = AutoModelForImageTextToText.from_pretrained(
            args.model, local_files_only=True, device_map={"": 0}, dtype=torch.bfloat16,
            attn_implementation="sdpa", low_cpu_mem_usage=True,
            quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                   bnb_4bit_compute_dtype=torch.bfloat16,
                                                   bnb_4bit_use_double_quant=True))
        base.model.vision_tower = None
        base.model.multi_modal_projector = None
        model = PeftModel.from_pretrained(base, args.parent, is_trainable=False)
        model.eval()
    rows = []
    for ledger in ledgers:
        if args.arm == "B1_EXTRACTIVE_BASELINE":
            proposal = extractive_proposal(ledger)
            verified = verify_proposal(ledger, proposal)
            if not verified["accepted"]:
                raise ValueError("extractive baseline rejected")
            row = {"case_id": ledger["case_id"], "arm": args.arm, "route": "DETERMINISTIC_EXTRACTIVE",
                   "text": verified["text"], "verified": True}
        elif args.arm == "B2_HYBRID":
            proposal = model_proposal(model, tokenizer, ledger, args.arm)
            result = execute_with_fallback(ledger, proposal)
            row = {"case_id": ledger["case_id"], "arm": args.arm, "route": result["route"],
                   "text": result["text"], "verified": True}
        else:
            proposal = model_proposal(model, tokenizer, ledger, args.arm)
            if proposal.get("case_id") != ledger["case_id"] or not isinstance(proposal.get("text"), str):
                raise ValueError("malformed B0 output")
            row = {"case_id": ledger["case_id"], "arm": args.arm, "route": "R2_ONE_PASS",
                   "text": proposal["text"], "verified": False}
        rows.append(row)
    atomic_json(args.output / "observations.json", rows)
    atomic_json(args.output / "terminal.json", {"status": "PASS_TERMINAL", "slot_id": f"{args.arm}__seed_{args.seed}",
                                                "rows": len(rows), "optimizer_created": False,
                                                "training_performed": False})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fixture-only", action="store_true")
    parser.add_argument("--execute-authorized", action="store_true")
    parser.add_argument("--model", type=Path)
    parser.add_argument("--tokenizer", type=Path)
    parser.add_argument("--parent", type=Path)
    parser.add_argument("--artifacts", type=Path)
    args = parser.parse_args()
    if args.fixture_only:
        print(json.dumps(fixture(args.arm, args.seed), sort_keys=True))
        return
    if not args.execute_authorized or not all((args.model, args.tokenizer, args.parent, args.artifacts)):
        raise SystemExit("separate owner authorization required")
    real(args)


if __name__ == "__main__":
    main()
