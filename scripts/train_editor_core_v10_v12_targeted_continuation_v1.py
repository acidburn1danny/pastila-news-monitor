"""Dedicated offline worker for the 128-row Editor Core targeted continuation."""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys
from pathlib import Path

EXPECTED_ROWS = 128
EXPECTED_STEPS = 16
CHECKPOINT_STEPS = (8, 16)
EXPECTED_CONFIG_IDENTITY = "934bc1dcd02f2eb23e98e4ef371e2fd89eb9d7b921eb0554cec8e51cc561f975"
EXPECTED_CORPUS = "c1ee2f4a6c0561eba52ef7a437a885568cf8fd2b53956b0c3a05c309ca0fad4a"
EXPECTED_MODEL = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
EXPECTED_PARENT = "8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f"
EXPECTED_CHECKPOINT = "6925fca8c5b6c9e94e96255cb21ec9442aff5d0ac2f7bd0f2038ce45475a7dd1"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def published_canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def flat_manifest(root: Path) -> str:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("materialization root mismatch")
    rows = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode()):
        if path.is_symlink() or not path.is_file():
            raise ValueError("materialization closure mismatch")
        rows.append(path.name.encode() + b"\0" + path.stat().st_size.to_bytes(8, "big") + bytes.fromhex(sha_file(path)))
    if not rows:
        raise ValueError("materialization closure empty")
    return hashlib.sha256(b"".join(rows)).hexdigest()


def validate_config(config: dict[str, object], corpus_sha256: str, row_count: int) -> dict[str, object]:
    identity = config.get("training_config_identity")
    core = {key: value for key, value in config.items() if key != "training_config_identity"}
    if identity != hashlib.sha256(published_canonical(core)).hexdigest() or identity != EXPECTED_CONFIG_IDENTITY:
        raise ValueError("training config identity mismatch")
    expected = {
        "status": "PREPARED_TRAINING_NOT_AUTHORIZED",
        "parent_adapter_content_identity": EXPECTED_PARENT,
        "parent_checkpoint_identity": EXPECTED_CHECKPOINT,
        "base_model_manifest_sha256": EXPECTED_MODEL,
        "training_corpus_sha256": EXPECTED_CORPUS,
        "new_training_rows": 64,
        "replay_rows": 64,
        "independent_holdout_rows": 32,
        "objective": "ASSISTANT_ONLY_NEXT_TOKEN_CROSS_ENTROPY_EXPLICIT_EOS",
        "optimizer": "PAGED_ADAMW_8BIT_NEW_STATE",
        "learning_rate": "0.000005",
        "scheduler": "CONSTANT_WITHOUT_WARMUP",
        "epochs": 1,
        "micro_batch_size": 1,
        "gradient_accumulation_steps": 8,
        "max_sequence_tokens": 3072,
        "precision": "BF16",
        "weight_decay": "0.0",
        "seed": 314159,
        "packing": False,
        "shuffle": True,
        "checkpoint_policy": "SAVE_FINAL_AND_EVERY_8_OPTIMIZER_STEPS",
        "expected_optimizer_steps": EXPECTED_STEPS,
        "network_activity": False,
        "training_authorized": False,
        "training_performed": False,
        "holdout_training_use": False,
        "r4_training_use": False,
        "human_receipt_training_use": False,
    }
    if any(config.get(key) != value for key, value in expected.items()):
        raise ValueError("frozen training configuration mismatch")
    if corpus_sha256 != EXPECTED_CORPUS or row_count != EXPECTED_ROWS:
        raise ValueError("training corpus closure mismatch")
    order = list(range(row_count))
    random.Random(314159).shuffle(order)
    return {"rows": row_count, "optimizer_steps": row_count // 8, "checkpoint_steps": list(CHECKPOINT_STEPS), "order_sha256": hashlib.sha256(canonical(order)).hexdigest()}


def token_ids(value: object) -> list[int]:
    if hasattr(value, "get") and value.get("input_ids") is not None:
        value = value.get("input_ids")
    values = getattr(value, "ids", value)
    if isinstance(values, (list, tuple)) and len(values) == 1 and hasattr(values[0], "ids"):
        values = values[0].ids
    if not isinstance(values, (list, tuple)) or not all(type(item) is int for item in values):
        raise ValueError("tokenizer output shape mismatch")
    return list(values)


def save_checkpoint(output: Path, model: object, optimizer: object, torch: object, step: int, authority: dict[str, object]) -> str:
    temporary = output / f".checkpoint-{step:06d}.tmp"
    final = output / f"checkpoint-{step:06d}"
    if temporary.exists() or final.exists():
        raise ValueError("checkpoint collision")
    temporary.mkdir()
    adapter = temporary / "adapter"
    model.save_pretrained(adapter, safe_serialization=True)
    state = temporary / "training-state.pt"
    torch.save({"optimizer_steps": step, "optimizer": optimizer.state_dict(), "cpu_rng": torch.get_rng_state(), "cuda_rng": torch.cuda.get_rng_state_all()}, state)
    core = {**authority, "optimizer_steps": step, "state_sha256": sha_file(state)}
    identity = hashlib.sha256(canonical(core)).hexdigest()
    (temporary / "checkpoint.json").write_text(json.dumps({**core, "checkpoint_identity": identity}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, final)
    return identity


def run_training(model_path: Path, parent_path: Path, corpus_path: Path, config_path: Path, output: Path) -> dict[str, object]:
    required = {"TRAINING_EXECUTION_AUTHORIZED", "MODEL_SHA256", "PARENT_SHA256", "CORPUS_SHA256", "CONFIG_SHA256", "ROOTFS_SHA256", "LAUNCHER_SHA256", "WORKER_SHA256"}
    if any(not os.environ.get(name) for name in required) or os.environ["TRAINING_EXECUTION_AUTHORIZED"] != "1":
        raise ValueError("training execution authorization missing")
    if output.is_symlink() or not output.is_dir() or any(output.iterdir()):
        raise ValueError("training output must be distinct and empty")
    corpus_sha = sha_file(corpus_path)
    config_sha = sha_file(config_path)
    if corpus_sha != os.environ["CORPUS_SHA256"] or config_sha != os.environ["CONFIG_SHA256"] or sha_file(Path(__file__)) != os.environ["WORKER_SHA256"]:
        raise ValueError("source identity mismatch")
    rows = [json.loads(line) for line in corpus_path.read_bytes().splitlines()]
    config = json.loads(config_path.read_bytes())
    plan = validate_config(config, corpus_sha, len(rows))
    model_identity, parent_identity = flat_manifest(model_path), flat_manifest(parent_path)
    if model_identity != EXPECTED_MODEL or parent_identity != EXPECTED_PARENT:
        raise ValueError("model or parent identity mismatch")

    import bitsandbytes as bnb
    import torch
    from peft import PeftModel, prepare_model_for_kbit_training
    from torch._native.registry import deregister_op_overrides
    from transformers import AutoModelForImageTextToText, AutoTokenizer, BitsAndBytesConfig

    seed = int(config["seed"])
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    deregister_op_overrides(disable_op_symbols="bmm")
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, fix_mistral_regex=True)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    loaded = AutoModelForImageTextToText.from_pretrained(model_path, local_files_only=True, quantization_config=quantization, device_map={"": 0}, dtype=torch.bfloat16, attn_implementation="sdpa", low_cpu_mem_usage=True)
    loaded.model.vision_tower = None
    loaded.model.multi_modal_projector = None
    loaded = prepare_model_for_kbit_training(loaded, use_gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": True})
    loaded = PeftModel.from_pretrained(loaded, parent_path, is_trainable=True)
    loaded.train()
    optimizer = bnb.optim.PagedAdamW8bit([p for p in loaded.parameters() if p.requires_grad], lr=float(config["learning_rate"]), weight_decay=float(config["weight_decay"]))
    optimizer.zero_grad(set_to_none=True)
    order = list(range(len(rows)))
    random.Random(seed).shuffle(order)
    steps = 0
    checkpoints = []
    authority = {"corpus_sha256": corpus_sha, "config_sha256": config_sha, "model_sha256": model_identity, "parent_sha256": parent_identity, "rootfs_sha256": os.environ["ROOTFS_SHA256"], "launcher_sha256": os.environ["LAUNCHER_SHA256"], "worker_sha256": os.environ["WORKER_SHA256"]}
    losses = []
    for position, index in enumerate(order, 1):
        messages = rows[index]["messages"]
        prefix = token_ids(tokenizer.apply_chat_template(messages[:2], tokenize=True, add_generation_prompt=True))
        tokens = token_ids(tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=False))
        if not tokens or tokens[-1] != tokenizer.eos_token_id or tokenizer.eos_token_id in tokens[len(prefix):-1] or len(tokens) > int(config["max_sequence_tokens"]):
            raise ValueError("token sequence closure mismatch")
        input_ids = torch.tensor([tokens], device="cuda")
        labels = input_ids.clone()
        labels[:, :len(prefix)] = -100
        loss = loaded(input_ids=input_ids, labels=labels, use_cache=False).loss
        (loss / 8).backward()
        losses.append(float(loss.detach().cpu()))
        if position % 8 == 0:
            optimizer.step()
            torch.cuda.synchronize()
            optimizer.zero_grad(set_to_none=True)
            steps += 1
            if steps in CHECKPOINT_STEPS:
                checkpoints.append(save_checkpoint(output, loaded, optimizer, torch, steps, authority))
    if steps != EXPECTED_STEPS or len(checkpoints) != 2:
        raise ValueError("optimizer/checkpoint schedule mismatch")
    loaded.save_pretrained(output / "adapter", safe_serialization=True)
    receipt = {"schema": "pastila-editor-core-targeted-continuation-training-receipt", "schema_version": 1, **authority, "optimizer": "PAGED_ADAMW_8BIT_NEW_STATE", "optimizer_steps": steps, "checkpoint_identities": checkpoints, "final_loss": format(losses[-1], ".17g"), "network_activity": False, "holdout_used": False, "adjudication_performed": False}
    receipt["receipt_identity"] = hashlib.sha256(canonical(receipt)).hexdigest()
    (output / "training-receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt


def fixture_smoke(config: dict[str, object]) -> dict[str, object]:
    plan = validate_config(config, EXPECTED_CORPUS, EXPECTED_ROWS)
    core = {"schema": "pastila-editor-core-targeted-worker-fixture-smoke", "schema_version": 1, "status": "PASS_FIXTURE_ONLY", **plan, "model_loaded": False, "optimizer_created": False, "optimizer_steps_executed": 0, "training_performed": False}
    return {**core, "smoke_identity": hashlib.sha256(canonical(core)).hexdigest()}


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit("usage: worker MODEL PARENT CORPUS CONFIG OUTPUT")
    print(json.dumps(run_training(*map(Path, sys.argv[1:])), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
