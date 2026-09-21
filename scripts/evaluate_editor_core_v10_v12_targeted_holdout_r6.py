"""Deterministic inference-only runner for the R6 independent holdout."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import unicodedata
from pathlib import Path

EXPECTED_ROWS = 12
MAX_INPUT_TOKENS = 3072
MAX_NEW_TOKENS = 2048
MAX_OUTPUT_BYTES = 6268


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def flat_manifest(root: Path) -> str:
    rows = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode()):
        if path.is_symlink() or not path.is_file():
            raise ValueError("adapter/model closure mismatch")
        rows.append(path.name.encode() + b"\0" + path.stat().st_size.to_bytes(8, "big") + bytes.fromhex(sha(path.read_bytes())))
    return sha(b"".join(rows))


def validate_requests(path: Path) -> list[dict[str, object]]:
    rows = [json.loads(line) for line in path.read_bytes().splitlines()]
    if len(rows) != EXPECTED_ROWS or any(len(row.get("messages", [])) != 2 for row in rows):
        raise ValueError("holdout request closure mismatch")
    if any(any(message.get("role") == "assistant" for message in row["messages"]) for row in rows):
        raise ValueError("holdout target leakage")
    if any(any(key in row for key in ("assistant_target", "target", "answer")) for row in rows):
        raise ValueError("holdout target leakage")
    if len({row.get("example_id") for row in rows}) != EXPECTED_ROWS:
        raise ValueError("holdout identity duplication")
    if len({request_identity(row) for row in rows}) != EXPECTED_ROWS:
        raise ValueError("holdout request identity duplication")
    return rows


def request_identity(row: dict[str, object]) -> str:
    user = row["messages"][1]
    content = user.get("content") if isinstance(user, dict) else None
    if not isinstance(content, str) or "\nINPUT=" not in content:
        raise ValueError("holdout INPUT projection missing")
    payload = json.loads(content.rsplit("\nINPUT=", 1)[1])
    value = payload.get("request_identity")
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ValueError("holdout request identity missing")
    return value


def run(model_path: Path, adapter_path: Path, requests_path: Path, output: Path, candidate: str) -> dict[str, object]:
    if os.environ.get("EVALUATION_EXECUTION_AUTHORIZED") != "1" or any(output.iterdir()):
        raise ValueError("evaluation invocation mismatch")
    if flat_manifest(model_path) != os.environ["MODEL_SHA256"] or flat_manifest(adapter_path) != os.environ["ADAPTER_SHA256"]:
        raise ValueError("model/adapter identity mismatch")
    if sha(requests_path.read_bytes()) != os.environ["REQUESTS_SHA256"] or sha(Path(__file__).read_bytes()) != os.environ["RUNNER_SHA256"]:
        raise ValueError("evaluation source identity mismatch")
    rows = validate_requests(requests_path)

    import torch
    from peft import PeftModel
    from torch._native.registry import deregister_op_overrides
    from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig

    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    torch.use_deterministic_algorithms(True)
    deregister_op_overrides(disable_op_symbols="bmm")
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, fix_mistral_regex=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    loaded = AutoModelForImageTextToText.from_pretrained(
        model_path, local_files_only=True,
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True),
        device_map={"": 0}, dtype=torch.bfloat16, attn_implementation="sdpa", low_cpu_mem_usage=True,
    )
    loaded.model.vision_tower = None
    loaded.model.multi_modal_projector = None
    loaded = PeftModel.from_pretrained(loaded, adapter_path, is_trainable=False)
    loaded.eval()
    observations = []
    for index, row in enumerate(rows, 1):
        encoded = tokenizer.apply_chat_template(row["messages"], tokenize=True, add_generation_prompt=True, return_tensors="pt", return_dict=True)
        input_tokens = int(encoded["input_ids"].shape[1])
        if input_tokens > MAX_INPUT_TOKENS:
            raise ValueError("holdout input ceiling exceeded")
        encoded = {key: value.to("cuda") for key, value in encoded.items()}
        with torch.inference_mode():
            generated = loaded.generate(**encoded, do_sample=False, num_beams=1, max_new_tokens=MAX_NEW_TOKENS, eos_token_id=tokenizer.eos_token_id, pad_token_id=tokenizer.pad_token_id, use_cache=True)
        tokens = generated[0, input_tokens:].cpu()
        terminal_eos = bool(len(tokens) and int(tokens[-1]) == tokenizer.eos_token_id)
        text = tokenizer.decode(tokens, skip_special_tokens=True)
        raw = text.encode()
        observation = {
            "index": index, "example_id": row["example_id"], "request_identity": request_identity(row),
            "candidate": candidate, "input_tokens": input_tokens, "output_tokens": len(tokens),
            "output_bytes": len(raw), "terminal_eos": terminal_eos,
            "within_byte_ceiling": len(raw) <= MAX_OUTPUT_BYTES, "nfc": unicodedata.normalize("NFC", text) == text,
            "response": text, "response_sha256": sha(raw),
        }
        observations.append(observation)
        (output / f"{index:03d}.json").write_bytes(canonical(observation))
    core = {
        "schema": "pastila-editor-core-targeted-r6-holdout-inference-receipt", "schema_version": 1,
        "candidate": candidate, "adapter_sha256": os.environ["ADAPTER_SHA256"],
        "requests_sha256": os.environ["REQUESTS_SHA256"], "runner_sha256": os.environ["RUNNER_SHA256"],
        "rows": len(observations), "terminal_eos": sum(row["terminal_eos"] for row in observations),
        "within_byte_ceiling": sum(row["within_byte_ceiling"] for row in observations),
        "network_activity": False, "training_performed": False, "optimizer_activity": False, "answer_key_accessed": False,
    }
    receipt = {**core, "receipt_identity": sha(canonical(core))}
    (output / "inference-receipt.json").write_bytes(canonical(receipt))
    return receipt


def fixture_smoke(requests: list[dict[str, object]]) -> dict[str, object]:
    if len(requests) != 2 or any(any(message.get("role") == "assistant" for message in row.get("messages", [])) for row in requests):
        raise ValueError("fixture leakage")
    core = {"schema": "pastila-editor-core-targeted-r6-holdout-fixture-smoke", "schema_version": 1, "rows": 2, "model_loaded": False, "inference_performed": False, "training_performed": False}
    return {**core, "smoke_identity": sha(canonical(core))}


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit("usage: runner MODEL ADAPTER REQUESTS OUTPUT CANDIDATE")
    print(json.dumps(run(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
