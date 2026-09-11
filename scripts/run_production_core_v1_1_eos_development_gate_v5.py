"""Offline development-only EOS gate for the trained V5 V1.1 adapter."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path

EXPECTED_ENV = {
    "ADAPTER_SHA256",
    "CUBLAS_WORKSPACE_CONFIG",
    "CUDA_VISIBLE_DEVICES",
    "DEVELOPMENT_SHA256",
    "HF_HUB_OFFLINE",
    "MODEL_SHA256",
    "PATH",
    "PYTHONHASHSEED",
    "TOKENIZERS_PARALLELISM",
    "TRANSFORMERS_OFFLINE",
    "TRITON_CACHE_DIR",
    "TRITON_LIBCUDA_PATH",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def flat_manifest(root: Path) -> str:
    rows = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode()):
        if path.is_symlink() or not path.is_file():
            raise SystemExit("development object closure mismatch")
        data = path.read_bytes()
        rows.append(path.name.encode() + b"\0" + len(data).to_bytes(8, "big") + hashlib.sha256(data).digest())
    return sha(b"".join(rows))


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()


def repeated_ngram_ceiling(text: str, width: int = 8) -> int:
    words = text.split()
    if len(words) < width:
        return 1
    return max(Counter(tuple(words[i : i + width]) for i in range(len(words) - width + 1)).values())


def main() -> int:
    if len(sys.argv) != 6 or set(os.environ) != EXPECTED_ENV:
        raise SystemExit("development gate invocation mismatch")
    model, adapter, probes, output = map(Path, sys.argv[1:5])
    materialization = sys.argv[5]
    if materialization not in {"A", "B"} or any(output.iterdir()):
        raise SystemExit("development gate output mismatch")
    if flat_manifest(model) != os.environ["MODEL_SHA256"]:
        raise SystemExit("development model identity mismatch")
    if flat_manifest(adapter) != os.environ["ADAPTER_SHA256"]:
        raise SystemExit("development adapter identity mismatch")
    if sha(probes.read_bytes()) != os.environ["DEVELOPMENT_SHA256"]:
        raise SystemExit("development probe identity mismatch")
    rows = [json.loads(line) for line in probes.read_text("utf-8").splitlines()]
    if len(rows) != 48 or any(row.get("split") != "DEVELOPMENT" for row in rows):
        raise SystemExit("development probe closure mismatch")

    import torch
    from peft import PeftModel
    from torch._native.registry import deregister_op_overrides
    from transformers import (
        AutoModelForImageTextToText,
        AutoTokenizer,
        BitsAndBytesConfig,
    )

    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    deregister_op_overrides(disable_op_symbols="bmm")
    tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True, fix_mistral_regex=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    loaded = AutoModelForImageTextToText.from_pretrained(
        model,
        local_files_only=True,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        ),
        device_map={"": 0},
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
        low_cpu_mem_usage=True,
    )
    loaded.model.vision_tower = None
    loaded.model.multi_modal_projector = None
    loaded = PeftModel.from_pretrained(loaded, adapter, is_trainable=False)
    loaded.eval()
    observations = []
    for index, row in enumerate(rows, 1):
        encoded = tokenizer.apply_chat_template(
            row["messages"][:2], tokenize=True, add_generation_prompt=True, return_tensors="pt", return_dict=True
        )
        input_tokens = int(encoded["input_ids"].shape[1])
        encoded = {key: value.to("cuda") for key, value in encoded.items()}
        with torch.inference_mode():
            generated = loaded.generate(
                **encoded,
                do_sample=False,
                num_beams=1,
                repetition_penalty=1.0,
                max_new_tokens=6268,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id,
                use_cache=True,
            )
        tokens = generated[0, input_tokens:].cpu()
        terminal_eos = bool(len(tokens) and int(tokens[-1]) == tokenizer.eos_token_id)
        text = tokenizer.decode(tokens, skip_special_tokens=True)
        try:
            parsed = json.loads(text)
            canonical_json = json.dumps(parsed, ensure_ascii=False, allow_nan=False, separators=(",", ":")) == text
        except (ValueError, TypeError):
            canonical_json = False
        expected = row["messages"][2]["content"]
        observation = {
            "index": index,
            "example_id": row["example_id"],
            "terminal_eos": terminal_eos,
            "canonical_json": canonical_json,
            "exact_target": text == expected,
            "output_tokens": len(tokens),
            "repeated_8gram_ceiling": repeated_ngram_ceiling(text),
            "output_sha256": sha(text.encode()),
        }
        observations.append(observation)
        (output / f"{index:03d}.json").write_bytes(canonical(observation))
    passed = all(
        row["terminal_eos"]
        and row["canonical_json"]
        and row["repeated_8gram_ceiling"] <= 3
        for row in observations
    )
    core = {
        "schema": "pastila-production-core-v1.1-eos-development-gate",
        "schema_version": 5,
        "materialization": materialization,
        "adapter_sha256": os.environ["ADAPTER_SHA256"],
        "development_sha256": os.environ["DEVELOPMENT_SHA256"],
        "rows": len(observations),
        "terminal_eos_passed": sum(row["terminal_eos"] for row in observations),
        "canonical_json_passed": sum(row["canonical_json"] for row in observations),
        "exact_target_passed": sum(row["exact_target"] for row in observations),
        "anti_repetition_passed": sum(row["repeated_8gram_ceiling"] <= 3 for row in observations),
        "status": "PASS" if passed else "FAIL_CLOSED",
        "qualification_attempt_consumed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    receipt = {**core, "gate_identity": sha(canonical(core))}
    (output / "gate-receipt.json").write_bytes(canonical(receipt))
    if not passed:
        raise SystemExit("development gate failed closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
