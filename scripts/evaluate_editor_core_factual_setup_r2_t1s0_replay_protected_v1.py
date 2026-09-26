"""Frozen deterministic development/replay inference for the T1/S0 replay experiment."""
from __future__ import annotations

import argparse, hashlib, json, os, sys, unicodedata
from collections import Counter
from pathlib import Path

ROWS = 48
CANDIDATES = 7
MAX_INPUT_TOKENS = 3072
MAX_NEW_TOKENS = 2048


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def flat(root):
    rows = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode()):
        if path.is_symlink() or not path.is_file():
            raise ValueError("adapter/model closure")
        rows.append(path.name.encode() + b"\0" + path.stat().st_size.to_bytes(8, "big") + bytes.fromhex(sha(path.read_bytes())))
    return sha(b"".join(rows))


def load_requests(path):
    rows = [json.loads(line) for line in path.read_bytes().splitlines()]
    splits = Counter(row.get("split") for row in rows)
    if len(rows) != ROWS or len({row["example_id"] for row in rows}) != ROWS:
        raise ValueError("request inventory")
    if splits != {"INDEPENDENT_SELECTION_BENCHMARK": 24, "REPLAY_RETENTION": 24}:
        raise ValueError("partition inventory")
    for row in rows:
        if len(row.get("messages", [])) != 2 or any(message.get("role") == "assistant" for message in row["messages"]):
            raise ValueError("answer leakage")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--requests", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("EDITOR_T1S0_REPLAY_EVALUATION_AUTHORIZED") != "1":
        raise ValueError("evaluation authority")
    if args.output.is_symlink() or not args.output.is_dir() or any(args.output.iterdir()):
        raise ValueError("output authority")
    manifest = json.loads(args.candidates.read_text(encoding="utf-8"))
    rows = load_requests(args.requests)
    if sha(args.requests.read_bytes()) != manifest["requests_sha256"]:
        raise ValueError("requests identity")
    candidates = manifest["candidates"]
    if len(candidates) != CANDIDATES or len({item["candidate_id"] for item in candidates}) != CANDIDATES:
        raise ValueError("candidate inventory")
    for item in candidates:
        if flat(Path(item["adapter_path"])) != item["adapter_identity"]:
            raise ValueError("adapter identity")

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import torch
    from peft import PeftModel
    from torch._native.registry import deregister_op_overrides
    from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig
    from editor_core_bridge_json_constraint_v3 import BridgeJSONStateV3, BridgeTokenTrieV3
    from evaluate_editor_core_factual_setup_benchmark_v1 import validate_generated_response

    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    torch.use_deterministic_algorithms(True)
    deregister_op_overrides(disable_op_symbols="bmm")
    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True, fix_mistral_regex=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForImageTextToText.from_pretrained(
        args.model,
        local_files_only=True,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True),
        device_map={"": 0}, dtype=torch.bfloat16, attn_implementation="sdpa", low_cpu_mem_usage=True,
    )
    base.model.vision_tower = None
    base.model.multi_modal_projector = None
    first = candidates[0]
    model = PeftModel.from_pretrained(base, first["adapter_path"], adapter_name=first["candidate_id"], is_trainable=False)
    for item in candidates[1:]:
        model.load_adapter(item["adapter_path"], adapter_name=item["candidate_id"], is_trainable=False)
    pieces = {index: tokenizer.decode([index], skip_special_tokens=True, clean_up_tokenization_spaces=False) for index in range(len(tokenizer))}
    trie = BridgeTokenTrieV3(token_pieces=pieces, eos_token_id=tokenizer.eos_token_id, excluded_token_ids=set(tokenizer.all_special_ids) - {tokenizer.eos_token_id})

    receipts = []
    for item in candidates:
        candidate_id = item["candidate_id"]
        model.set_adapter(candidate_id)
        model.eval()
        target = args.output / candidate_id
        target.mkdir()
        responses, observations = [], []
        for index, row in enumerate(rows, 1):
            payload = json.loads(row["messages"][1]["content"].split("\nINPUT=", 1)[1])
            encoded = tokenizer.apply_chat_template(row["messages"], tokenize=True, add_generation_prompt=True, return_tensors="pt", return_dict=True)
            prompt_tokens = int(encoded["input_ids"].shape[1])
            if prompt_tokens > MAX_INPUT_TOKENS:
                raise ValueError("input ceiling")
            encoded = {key: value.to("cuda") for key, value in encoded.items()}

            def allowed(_batch, input_ids):
                decoded = tokenizer.decode(input_ids[prompt_tokens:].tolist(), skip_special_tokens=True, clean_up_tokenization_spaces=False)
                return list(trie.allowed_token_ids(BridgeJSONStateV3.start(payload).feed(decoded)))

            with torch.inference_mode():
                generated = model.generate(**encoded, do_sample=False, num_beams=1, max_new_tokens=MAX_NEW_TOKENS, repetition_penalty=1.0, prefix_allowed_tokens_fn=allowed, eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id, use_cache=True)
            tokens = generated[0, prompt_tokens:].cpu()
            text = tokenizer.decode(tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)
            eos = bool(len(tokens) and int(tokens[-1]) == tokenizer.eos_token_id)
            if not text or unicodedata.normalize("NFC", text) != text:
                raise ValueError(f"invalid text {candidate_id} {row['example_id']}")
            validate_generated_response(text, payload, eos)
            responses.append({"case_id": row["example_id"], "split": row["split"], "request_identity": payload["request_identity"], "response": text})
            observations.append({"index": index, "case_id": row["example_id"], "split": row["split"], "output_tokens": len(tokens), "terminal_eos": eos, "response_sha256": sha(text.encode())})
        response_bytes = b"".join(canonical(row) + b"\n" for row in responses)
        observation_bytes = b"".join(canonical(row) + b"\n" for row in observations)
        (target / "responses.jsonl").write_bytes(response_bytes)
        (target / "observations.jsonl").write_bytes(observation_bytes)
        core = {"schema": "editor-factual-setup-t1s0-replay-protected-evaluation", "schema_version": 1, "candidate_id": candidate_id, "adapter_identity": item["adapter_identity"], "rows": ROWS, "partitions": dict(Counter(row["split"] for row in responses)), "terminal_eos": sum(row["terminal_eos"] for row in observations), "responses_sha256": sha(response_bytes), "observations_sha256": sha(observation_bytes), "requests_sha256": sha(args.requests.read_bytes()), "answer_key_accessed": False, "historical_holdout_accessed": False, "training_performed": False, "optimizer_steps": 0}
        receipt = {**core, "receipt_identity": sha(canonical(core))}
        (target / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
        receipts.append(receipt)
    program = {"status": "PASS_7_DEVELOPMENT_REPLAY_BUNDLES", "candidates": CANDIDATES, "rows": CANDIDATES * ROWS, "terminal_eos": sum(item["terminal_eos"] for item in receipts), "receipts": [item["receipt_identity"] for item in receipts], "answer_key_accessed": False, "historical_holdout_accessed": False, "training_performed": False, "optimizer_steps": 0}
    (args.output / "program-terminal.json").write_text(json.dumps(program, sort_keys=True, indent=2) + "\n")
    print(json.dumps(program, sort_keys=True))


if __name__ == "__main__":
    main()
