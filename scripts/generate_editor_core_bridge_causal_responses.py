"""Deterministic inference-only worker for the A1/A2 causal development pilot."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unicodedata
from pathlib import Path

ROWS = 24
MAX_INPUT_TOKENS = 3072
MAX_NEW_TOKENS = 2048


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def flat_manifest(root: Path) -> str:
    rows = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode()):
        if path.is_symlink() or not path.is_file():
            raise ValueError("adapter/model closure")
        rows.append(path.name.encode() + b"\0" + path.stat().st_size.to_bytes(8, "big") + bytes.fromhex(sha(path.read_bytes())))
    return sha(b"".join(rows))


def requests(path: Path) -> list[dict]:
    values = [json.loads(line) for line in path.read_bytes().splitlines()]
    if len(values) != ROWS or len({row.get("example_id") for row in values}) != ROWS:
        raise ValueError("development request inventory")
    for row in values:
        if row.get("split") != "DEVELOPMENT" or len(row.get("messages", [])) != 2:
            raise ValueError("development split")
        if any(message.get("role") == "assistant" for message in row["messages"]):
            raise ValueError("target leakage")
        payload = json.loads(row["messages"][1]["content"].split("\nINPUT=", 1)[1])
        if payload.get("case_id") != row["example_id"] or not str(payload.get("request_identity", "")).startswith("sha256:"):
            raise ValueError("request binding")
    return values


def run(model: Path, adapter: Path, request_path: Path, output: Path, candidate: str) -> dict:
    if os.environ.get("BRIDGE_CAUSAL_INFERENCE_AUTHORIZED") != "1" or any(output.iterdir()):
        raise ValueError("inference invocation/output")
    if flat_manifest(model) != os.environ["MODEL_SHA256"] or flat_manifest(adapter) != os.environ["ADAPTER_SHA256"]:
        raise ValueError("model/adapter identity")
    if sha(request_path.read_bytes()) != os.environ["REQUESTS_SHA256"] or sha(Path(__file__).read_bytes()) != os.environ["WORKER_SHA256"]:
        raise ValueError("source identity")
    values = requests(request_path)

    import torch
    from peft import PeftModel
    from torch._native.registry import deregister_op_overrides
    from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig

    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    torch.use_deterministic_algorithms(True)
    deregister_op_overrides(disable_op_symbols="bmm")
    tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True, fix_mistral_regex=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    loaded = AutoModelForImageTextToText.from_pretrained(
        model, local_files_only=True,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True),
        device_map={"": 0}, dtype=torch.bfloat16, attn_implementation="sdpa", low_cpu_mem_usage=True,
    )
    loaded.model.vision_tower = None
    loaded.model.multi_modal_projector = None
    loaded = PeftModel.from_pretrained(loaded, adapter, is_trainable=False)
    loaded.eval()
    response_rows = []
    observations = []
    for index, row in enumerate(values, 1):
        payload = json.loads(row["messages"][1]["content"].split("\nINPUT=", 1)[1])
        encoded = tokenizer.apply_chat_template(row["messages"], tokenize=True, add_generation_prompt=True, return_tensors="pt", return_dict=True)
        input_tokens = int(encoded["input_ids"].shape[1])
        if input_tokens > MAX_INPUT_TOKENS:
            raise ValueError("input token ceiling")
        encoded = {key: value.to("cuda") for key, value in encoded.items()}
        with torch.inference_mode():
            generated = loaded.generate(**encoded, do_sample=False, num_beams=1, max_new_tokens=MAX_NEW_TOKENS,
                                        eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id, use_cache=True)
        tokens = generated[0, input_tokens:].cpu()
        text = tokenizer.decode(tokens, skip_special_tokens=True)
        if not text or unicodedata.normalize("NFC", text) != text:
            raise ValueError("empty/non-NFC response")
        response_rows.append({"case_id": row["example_id"], "request_identity": payload["request_identity"], "response": text})
        observations.append({"index": index, "case_id": row["example_id"], "request_identity": payload["request_identity"],
                             "input_tokens": input_tokens, "output_tokens": len(tokens),
                             "terminal_eos": bool(len(tokens) and int(tokens[-1]) == tokenizer.eos_token_id),
                             "response_sha256": sha(text.encode())})
    response_bytes = b"".join(canonical(row) + b"\n" for row in response_rows)
    observation_bytes = b"".join(canonical(row) + b"\n" for row in observations)
    (output / "responses.jsonl").write_bytes(response_bytes)
    (output / "observations.jsonl").write_bytes(observation_bytes)
    core = {"schema": "editor-core-bridge-causal-development-inference-receipt", "schema_version": 1,
            "candidate": candidate, "rows": ROWS, "model_sha256": os.environ["MODEL_SHA256"],
            "adapter_sha256": os.environ["ADAPTER_SHA256"], "requests_sha256": os.environ["REQUESTS_SHA256"],
            "worker_sha256": os.environ["WORKER_SHA256"], "responses_sha256": sha(response_bytes),
            "observations_sha256": sha(observation_bytes), "terminal_eos": sum(row["terminal_eos"] for row in observations),
            "answer_key_accessed": False, "holdout_accessed": False, "network_activity": False,
            "training_performed": False, "optimizer_steps": 0}
    receipt = {**core, "receipt_identity": sha(canonical(core))}
    (output / "inference-receipt.json").write_bytes(json.dumps(receipt, sort_keys=True, indent=2).encode() + b"\n")
    return receipt


def fixture_smoke() -> dict:
    core = {"schema": "editor-core-bridge-causal-inference-fixture", "schema_version": 1,
            "model_loaded": False, "inference": False, "training": False, "optimizer_steps": 0}
    return {**core, "fixture_identity": sha(canonical(core))}


if __name__ == "__main__":
    if len(sys.argv) != 6:
        raise SystemExit("usage: worker MODEL ADAPTER REQUESTS OUTPUT CANDIDATE")
    print(json.dumps(run(*(Path(value) for value in sys.argv[1:5]), sys.argv[5]), sort_keys=True))
