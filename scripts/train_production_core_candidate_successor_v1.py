"""Offline, deterministic continuation training for one Core V2 successor adapter."""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys
from pathlib import Path

EXPECTED_ENV = {
    "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
    "CC": "/usr/bin/gcc",
    "CUDA_VISIBLE_DEVICES": "0",
    "HF_HUB_OFFLINE": "1",
    "PYTHONHASHSEED": "0",
    "PATH": "/usr/bin:/bin",
    "TOKENIZERS_PARALLELISM": "false",
    "TRANSFORMERS_OFFLINE": "1",
    "TRITON_CACHE_DIR": "/tmp/triton-cache",
    "TRITON_LIBCUDA_PATH": "/usr/lib/wsl/lib",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def flat_manifest(root: Path) -> str:
    rows = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode()):
        if path.is_symlink() or not path.is_file():
            raise SystemExit("predecessor adapter closure mismatch")
        data = path.read_bytes()
        rows.append(
            path.name.encode()
            + b"\0"
            + len(data).to_bytes(8, "big")
            + hashlib.sha256(data).digest()
        )
    return hashlib.sha256(b"".join(rows)).hexdigest()


def token_ids(encoded: object) -> list[int]:
    if hasattr(encoded, "get") and encoded.get("input_ids") is not None:
        encoded = encoded.get("input_ids")
    values = getattr(encoded, "ids", encoded)
    if (
        isinstance(values, (list, tuple))
        and len(values) == 1
        and hasattr(values[0], "ids")
    ):
        values = values[0].ids
    if not isinstance(values, (list, tuple)) or not all(
        type(item) is int for item in values
    ):
        raise SystemExit(
            "tokenizer output shape mismatch: "
            f"outer={type(encoded).__name__}, values={type(values).__name__}, "
            f"member={type(values[0]).__name__ if isinstance(values, (list, tuple)) and values else 'none'}"
        )
    return list(values)


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit("usage: trainer MODEL PREDECESSOR CORPUS CONFIG OUTPUT")
    model, predecessor, corpus, config_path, output = map(Path, sys.argv[1:])
    authority = {
        "AUTHORITY_MOUNTS_READ_ONLY",
        "CONFIG_SHA256",
        "CORPUS_SHA256",
        "LAUNCHER_SHA256",
        "MODEL_SHA256",
        "OUTPUT_MOUNT_WRITABLE",
        "PREDECESSOR_SHA256",
        "ROOTFS_SHA256",
        "TRAINER_SHA256",
        "TRAINING_MODE",
    }
    if set(os.environ) != set(EXPECTED_ENV) | authority:
        raise SystemExit("training environment mismatch")
    if {key: os.environ[key] for key in EXPECTED_ENV} != EXPECTED_ENV:
        raise SystemExit("training environment value mismatch")
    if (
        sha(corpus) != os.environ["CORPUS_SHA256"]
        or sha(config_path) != os.environ["CONFIG_SHA256"]
    ):
        raise SystemExit("training input identity mismatch")
    if sha(Path(__file__)) != os.environ["TRAINER_SHA256"]:
        raise SystemExit("trainer identity mismatch")
    config = json.loads(config_path.read_bytes())
    if config.get("status") != "FROZEN_PRETRAINING_ZERO_EXECUTION":
        raise SystemExit("training config status mismatch")
    model_sha = flat_manifest(model)
    predecessor_sha = flat_manifest(predecessor)
    if model_sha != os.environ["MODEL_SHA256"] or model_sha != config.get(
        "base_model_manifest_sha256"
    ):
        raise SystemExit("base model identity mismatch")
    if predecessor_sha != os.environ[
        "PREDECESSOR_SHA256"
    ] or predecessor_sha != config.get("predecessor_adapter_manifest_sha256"):
        raise SystemExit("predecessor adapter identity mismatch")
    if any(output.iterdir()):
        raise SystemExit("successor output must be empty")
    rows = [json.loads(line) for line in corpus.read_text("utf-8").splitlines()]
    expected_rows = 320 if config.get("schema_version") == 2 else 240
    if len(rows) != expected_rows:
        raise SystemExit("remediation corpus cardinality mismatch")

    import bitsandbytes as bnb
    import torch
    from peft import PeftModel, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForImageTextToText,
        AutoTokenizer,
        BitsAndBytesConfig,
    )

    mode = os.environ["TRAINING_MODE"]
    if mode not in {"SMOKE", "FULL"}:
        raise SystemExit("training mode authority mismatch")
    seed = int(config["seed"])
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    tokenizer = AutoTokenizer.from_pretrained(
        model, local_files_only=True, fix_mistral_regex=True
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    loaded = AutoModelForImageTextToText.from_pretrained(
        model,
        local_files_only=True,
        quantization_config=quantization,
        device_map={"": 0},
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
        low_cpu_mem_usage=True,
    )
    loaded.model.vision_tower = None
    loaded.model.multi_modal_projector = None
    loaded = prepare_model_for_kbit_training(loaded, use_gradient_checkpointing=True)
    loaded = PeftModel.from_pretrained(loaded, predecessor, is_trainable=True)
    loaded.train()
    parameters = [
        parameter for parameter in loaded.parameters() if parameter.requires_grad
    ]
    if config.get("optimizer") != "PAGED_ADAMW_8BIT":
        raise SystemExit("unsupported frozen optimizer")
    optimizer = bnb.optim.PagedAdamW8bit(
        parameters,
        lr=float(config["learning_rate"]),
        weight_decay=float(config["weight_decay"]),
    )
    accumulation = 1 if mode == "SMOKE" else int(config["gradient_accumulation_steps"])
    epochs = 1 if mode == "SMOKE" else int(config["epochs"])
    if mode == "SMOKE":
        rows = rows[:1]
    optimizer.zero_grad(set_to_none=True)
    losses = []
    steps = 0
    for epoch in range(epochs):
        order = list(range(len(rows)))
        random.Random(seed + epoch).shuffle(order)
        for position, index in enumerate(order, 1):
            messages = rows[index]["messages"]
            prefix = token_ids(
                tokenizer.apply_chat_template(
                    messages[:2], tokenize=True, add_generation_prompt=True
                )
            )
            tokens = token_ids(
                tokenizer.apply_chat_template(
                    messages, tokenize=True, add_generation_prompt=False
                )
            )
            if not tokens or tokens[-1] != tokenizer.eos_token_id:
                raise SystemExit("training target must end with supervised EOS")
            if tokenizer.eos_token_id in tokens[len(prefix) : -1]:
                raise SystemExit("training target contains premature supervised EOS")
            if len(tokens) > int(config["max_sequence_tokens"]):
                raise SystemExit("training sequence ceiling exceeded")
            input_ids = torch.tensor([tokens], device="cuda")
            labels = input_ids.clone()
            labels[:, : len(prefix)] = -100
            result = loaded(input_ids=input_ids, labels=labels, use_cache=False)
            loss = result.loss / accumulation
            loss.backward()
            losses.append(float(result.loss.detach().cpu()))
            if position % accumulation == 0:
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                steps += 1
    loaded.save_pretrained(output, safe_serialization=True)
    base = loaded.unload()
    reloaded = PeftModel.from_pretrained(base, output, is_trainable=False)
    if not any(True for _ in reloaded.peft_config):
        raise SystemExit("saved successor reload failed")
    if not any(Path("/tmp/triton-cache").rglob("*")):
        raise SystemExit("Triton compile/load evidence missing")
    receipt = {
        "schema": "pastila-production-core-candidate-successor-training-receipt",
        "schema_version": 1,
        "candidate": config["candidate"],
        "corpus_sha256": sha(corpus),
        "config_sha256": sha(config_path),
        "rootfs_sha256": os.environ["ROOTFS_SHA256"],
        "base_model_manifest_sha256": model_sha,
        "predecessor_adapter_manifest_sha256": predecessor_sha,
        "launcher_sha256": os.environ["LAUNCHER_SHA256"],
        "trainer_sha256": os.environ["TRAINER_SHA256"],
        "authority_mounts_read_only": os.environ["AUTHORITY_MOUNTS_READ_ONLY"] == "1",
        "output_mount_writable": os.environ["OUTPUT_MOUNT_WRITABLE"] == "1",
        "triton_compile_load": True,
        "backward_4bit": True,
        "optimizer": "PAGED_ADAMW_8BIT",
        "save_reload": True,
        "epochs": epochs,
        "optimizer_steps": steps,
        "training_mode": mode,
        "final_loss": format(losses[-1], ".17g"),
        "network_activity": False,
        "qualification_attempt_consumed": False,
        "candidate_execution_performed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    core = json.dumps(receipt, separators=(",", ":"), sort_keys=True).encode()
    receipt["receipt_identity"] = hashlib.sha256(core).hexdigest()
    (output / "training-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
