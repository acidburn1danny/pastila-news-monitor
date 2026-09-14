"""Offline, deterministic continuation training for one Core V2 successor adapter."""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys
import time
from contextlib import nullcontext
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

PERFORMANCE_VARIANT_CAPABILITIES = {
    "BASELINE": frozenset(),
    "FLASH_ONLY": frozenset({"flash"}),
    "EFFICIENT_ONLY": frozenset({"efficient"}),
    "EXPANDABLE_ALLOCATOR": frozenset({"expandable_allocator"}),
    "FLASH_ONLY_EXPANDABLE_ALLOCATOR": frozenset({"flash", "expandable_allocator"}),
    "FLASH_REPEAT_KV": frozenset({"flash", "repeat_kv"}),
    "FLASH_REPEAT_KV_EXPANDABLE_ALLOCATOR": frozenset({"flash", "repeat_kv", "expandable_allocator"}),
    "BF16_AUTOCAST": frozenset({"bf16"}),
    "BF16_AUTOCAST_FLASH_REPEAT_KV": frozenset({"bf16", "flash", "repeat_kv"}),
    "BF16_AUTOCAST_FLASH_REPEAT_KV_EXPANDABLE_ALLOCATOR": frozenset(
        {"bf16", "flash", "repeat_kv", "expandable_allocator"}
    ),
    "BF16_FLASH_REPEAT_KV_MEMORY_DIAGNOSTIC": frozenset({"bf16", "flash", "repeat_kv"}),
    "BF16_FLASH_REPEAT_KV_SELECTIVE_LOGITS_DIAGNOSTIC": frozenset(
        {"bf16", "flash", "repeat_kv", "selective_logits"}
    ),
    "BF16_FLASH_REPEAT_KV_SELECTIVE_LOGITS": frozenset(
        {"bf16", "flash", "repeat_kv", "selective_logits"}
    ),
    "BF16_FLEX_ATTENTION_SELECTIVE_LOGITS_DIAGNOSTIC": frozenset(
        {"bf16", "flex", "selective_logits"}
    ),
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


def recursive_manifest(root: Path) -> str:
    rows = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix().encode()):
        if path.is_symlink() or not path.is_file():
            raise SystemExit("checkpoint adapter closure mismatch")
        data = path.read_bytes()
        name = path.relative_to(root).as_posix().encode()
        rows.append(name + b"\0" + len(data).to_bytes(8, "big") + hashlib.sha256(data).digest())
    if not rows:
        raise SystemExit("checkpoint adapter closure empty")
    return hashlib.sha256(b"".join(rows)).hexdigest()


def canonicalize_adapter_config(root: Path) -> None:
    path = root / "adapter_config.json"
    value = json.loads(path.read_bytes())
    modules = value.get("target_modules")
    if not isinstance(modules, list) or not modules or not all(isinstance(item, str) for item in modules):
        raise SystemExit("adapter target_modules closure mismatch")
    value["target_modules"] = sorted(modules, key=lambda item: item.encode())
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def performance_snapshot(output: Path, torch: object, phase: str, started_ns: int) -> None:
    torch.cuda.synchronize()
    value = {
        "schema": "pastila-production-core-v10-performance-memory-snapshot",
        "schema_version": 1,
        "phase": phase,
        "elapsed_ms": (time.monotonic_ns() - started_ns) // 1_000_000,
        "allocated_bytes": torch.cuda.memory_allocated(),
        "reserved_bytes": torch.cuda.memory_reserved(),
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
    }
    with (output / "performance-telemetry.jsonl").open("ab") as handle:
        handle.write(json.dumps(value, separators=(",", ":"), sort_keys=True).encode() + b"\n")
        handle.flush()
        os.fsync(handle.fileno())


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


def assistant_logit_span(prefix_length: int, total_length: int) -> tuple[int, int]:
    if not 0 < prefix_length < total_length:
        raise SystemExit("assistant selective-logit span mismatch")
    return prefix_length - 1, total_length - 1


def progress_event(
    output: Path,
    *,
    previous_identity: str | None,
    event_ordinal: int,
    event: str,
    epoch: int,
    position: int,
    row_index: int,
    example_id: str,
    token_count: int,
    optimizer_steps_completed: int,
    started_ns: int,
) -> str:
    """Durably append one chained, content-addressed training progress event."""
    core = {
        "schema": "pastila-production-core-training-progress-event",
        "schema_version": 1,
        "event_ordinal": event_ordinal,
        "event": event,
        "epoch": epoch,
        "position": position,
        "row_index": row_index,
        "example_id": example_id,
        "token_count": token_count,
        "optimizer_steps_completed": optimizer_steps_completed,
        "previous_event_identity": previous_identity,
    }
    event_identity = hashlib.sha256(
        json.dumps(core, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    raw = json.dumps(
        {
            **core,
            "event_identity": event_identity,
            "observed_elapsed_ms": (time.monotonic_ns() - started_ns) // 1_000_000,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode() + b"\n"
    descriptor = os.open(
        output / "training-progress.jsonl",
        os.O_APPEND | os.O_CREAT | os.O_WRONLY,
        0o600,
    )
    try:
        if os.write(descriptor, raw) != len(raw):
            raise SystemExit("training progress short write")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return event_identity


def validate_training_corpus_binding(config: object, corpus_sha256: str) -> None:
    if not isinstance(config, dict) or config.get("training_corpus_sha256") != corpus_sha256:
        raise SystemExit("training corpus/config binding mismatch")


def validate_progress(path: Path) -> tuple[int, str | None, list[dict[str, object]]]:
    if not path.exists():
        return 0, None, []
    events = []
    previous = None
    for ordinal, line in enumerate(path.read_text("utf-8").splitlines(), 1):
        event = json.loads(line)
        identity = event.pop("event_identity", None)
        event.pop("observed_elapsed_ms", None)
        expected = hashlib.sha256(
            json.dumps(event, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
        if (
            identity != expected
            or event.get("event_ordinal") != ordinal
            or event.get("previous_event_identity") != previous
        ):
            raise SystemExit("training progress chain mismatch")
        event["event_identity"] = identity
        events.append(event)
        previous = identity
    return len(events), previous, events


def discover_checkpoint(output: Path, expected: dict[str, str]) -> dict[str, object] | None:
    checkpoints = output / "training-checkpoints"
    if not checkpoints.exists():
        return None
    if checkpoints.is_symlink() or not checkpoints.is_dir():
        raise SystemExit("training checkpoint root mismatch")
    manifests = []
    previous = None
    for checkpoint_ordinal, path in enumerate(
        sorted(checkpoints.iterdir(), key=lambda item: item.name), 1
    ):
        if path.is_symlink() or not path.is_dir() or not path.name.startswith("step-"):
            raise SystemExit("training checkpoint entry mismatch")
        manifest_path = path / "checkpoint.json"
        state_path = path / "training-state.pt"
        adapter = path / "adapter"
        if not manifest_path.is_file() or not state_path.is_file() or not adapter.is_dir():
            raise SystemExit("training checkpoint closure incomplete")
        value = json.loads(manifest_path.read_bytes())
        identity = value.pop("checkpoint_identity", None)
        calculated = hashlib.sha256(
            json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
        if identity != calculated or value.get("previous_checkpoint_identity") != previous:
            raise SystemExit("training checkpoint identity chain mismatch")
        for field, expected_value in expected.items():
            if value.get(field) != expected_value:
                raise SystemExit("training checkpoint authority binding mismatch")
        if (
            value.get("optimizer") != "PAGED_ADAMW_8BIT"
            or value.get("triton_compile_load") is not True
            or value.get("adapter_manifest_sha256") != recursive_manifest(adapter)
            or value.get("state_sha256") != sha(state_path)
            or value.get("optimizer_steps_completed") != checkpoint_ordinal
            or path.name != f"step-{checkpoint_ordinal:06d}"
        ):
            raise SystemExit("training checkpoint content mismatch")
        value["checkpoint_identity"] = identity
        value["path"] = path
        manifests.append(value)
        previous = identity
    return manifests[-1] if manifests else None


def save_checkpoint(
    *,
    output: Path,
    loaded: object,
    optimizer: object,
    torch: object,
    position: int,
    row_index: int,
    example_id: str,
    token_count: int,
    steps: int,
    last_loss: float,
    previous_checkpoint_identity: str | None,
    authority: dict[str, str],
) -> dict[str, object]:
    root = output / "training-checkpoints"
    root.mkdir(exist_ok=True)
    final = root / f"step-{steps:06d}"
    temporary = root / f".step-{steps:06d}.tmp"
    if final.exists() or temporary.exists():
        raise SystemExit("training checkpoint publication collision")
    if not any(Path("/tmp/triton-cache").rglob("*")):
        raise SystemExit("Triton compile/load evidence missing before checkpoint")
    temporary.mkdir()
    adapter = temporary / "adapter"
    loaded.save_pretrained(adapter, safe_serialization=True)
    canonicalize_adapter_config(adapter)
    state = {
        "schema": "pastila-production-core-training-checkpoint-state",
        "schema_version": 1,
        "next_position": position,
        "optimizer_steps_completed": steps,
        "last_loss": last_loss,
        "optimizer_state_dict": optimizer.state_dict(),
        "torch_rng_state": torch.get_rng_state(),
        "cuda_rng_states": torch.cuda.get_rng_state_all(),
    }
    state_path = temporary / "training-state.pt"
    torch.save(state, state_path)
    core = {
        "schema": "pastila-production-core-training-checkpoint",
        "schema_version": 1,
        **authority,
        "optimizer": "PAGED_ADAMW_8BIT",
        "triton_compile_load": True,
        "position_completed": position,
        "row_index": row_index,
        "example_id": example_id,
        "token_count": token_count,
        "optimizer_steps_completed": steps,
        "previous_checkpoint_identity": previous_checkpoint_identity,
        "adapter_manifest_sha256": recursive_manifest(adapter),
        "state_sha256": sha(state_path),
    }
    checkpoint_identity = hashlib.sha256(
        json.dumps(core, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    (temporary / "checkpoint.json").write_text(
        json.dumps({**core, "checkpoint_identity": checkpoint_identity}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, final)
    descriptor = os.open(root, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return {"checkpoint_identity": checkpoint_identity, "path": final}


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
    validate_training_corpus_binding(config, os.environ["CORPUS_SHA256"])
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
    existing = {path.name for path in output.iterdir()}
    if existing - {"training-progress.jsonl", "training-checkpoints", "performance-telemetry.jsonl"}:
        raise SystemExit("successor output is neither empty nor resumable")
    rows = [json.loads(line) for line in corpus.read_text("utf-8").splitlines()]
    expected_rows_by_schema = {1: 240, 2: 320, 3: 480}
    try:
        expected_rows = expected_rows_by_schema[config.get("schema_version")]
    except (KeyError, TypeError) as exc:
        raise SystemExit("training config schema version mismatch") from exc
    if len(rows) != expected_rows:
        raise SystemExit("remediation corpus cardinality mismatch")

    mode = os.environ["TRAINING_MODE"]
    if mode not in {"SMOKE", "CHECKPOINT_SMOKE", "BATCH_SMOKE", "FULL"}:
        raise SystemExit("training mode authority mismatch")
    performance_variant = config.get("performance_variant")
    training_execution_profile = config.get("training_execution_profile")
    if performance_variant is not None and training_execution_profile is not None:
        raise SystemExit("training execution profile conflicts with performance variant")
    if performance_variant is not None and performance_variant not in PERFORMANCE_VARIANT_CAPABILITIES:
        raise SystemExit("training performance variant mismatch")
    if performance_variant is not None and mode != "BATCH_SMOKE":
        raise SystemExit("performance variants are BATCH_SMOKE only")
    if training_execution_profile not in {None, "BF16_FLASH_REPEAT_KV_SELECTIVE_LOGITS"}:
        raise SystemExit("training execution profile mismatch")
    if training_execution_profile is not None and mode != "FULL":
        raise SystemExit("training execution profile is FULL only")
    effective_performance_profile = performance_variant or training_execution_profile
    performance_capabilities = PERFORMANCE_VARIANT_CAPABILITIES.get(
        effective_performance_profile, frozenset()
    )
    if "expandable_allocator" in performance_capabilities:
        os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"
    effective_mode = "SMOKE" if mode == "CHECKPOINT_SMOKE" else mode
    accumulation = 1 if effective_mode == "SMOKE" else int(config["gradient_accumulation_steps"])
    epochs = 1 if effective_mode == "SMOKE" else int(config["epochs"])
    if effective_mode == "SMOKE":
        rows = rows[:1]
    checkpoint_authority = {
        "corpus_sha256": os.environ["CORPUS_SHA256"],
        "config_sha256": os.environ["CONFIG_SHA256"],
        "predecessor_sha256": os.environ["PREDECESSOR_SHA256"],
        "model_sha256": os.environ["MODEL_SHA256"],
        "rootfs_sha256": os.environ["ROOTFS_SHA256"],
        "launcher_sha256": os.environ["LAUNCHER_SHA256"],
        "trainer_sha256": os.environ["TRAINER_SHA256"],
        "training_mode": effective_mode,
    }
    progress_events, progress_identity, progress_rows = validate_progress(
        output / "training-progress.jsonl"
    )
    checkpoint = discover_checkpoint(output, checkpoint_authority)
    adapter_source = checkpoint["path"] / "adapter" if checkpoint else predecessor

    import bitsandbytes as bnb
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from peft import PeftModel, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForImageTextToText,
        AutoTokenizer,
        BitsAndBytesConfig,
    )
    if "repeat_kv" in performance_capabilities:
        from transformers.integrations import sdpa_attention

        sdpa_attention.use_gqa_in_sdpa = lambda attention_mask, key, value: False

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
        attn_implementation=(
            "flex_attention"
            if "flex" in performance_capabilities
            else "sdpa"
        ),
        low_cpu_mem_usage=True,
    )
    loaded.model.vision_tower = None
    loaded.model.multi_modal_projector = None
    loaded = prepare_model_for_kbit_training(
        loaded,
        use_gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": True},
    )
    loaded = PeftModel.from_pretrained(loaded, adapter_source, is_trainable=True)
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
    if performance_variant is not None:
        performance_snapshot(output, torch, "MODEL_ADAPTER_OPTIMIZER_READY", time.monotonic_ns())
    resumed_from_checkpoint_identity = None
    start_position = 0
    previous_checkpoint_identity = None
    if checkpoint is not None:
        start_position = int(checkpoint["position_completed"])
        steps = int(checkpoint["optimizer_steps_completed"])
        if start_position != steps * accumulation or not 0 < start_position <= len(rows):
            raise SystemExit("training checkpoint schedule mismatch")
        state = torch.load(checkpoint["path"] / "training-state.pt", map_location="cpu", weights_only=False)
        if state.get("next_position") != start_position or state.get("optimizer_steps_completed") != steps:
            raise SystemExit("training checkpoint state mismatch")
        optimizer.load_state_dict(state["optimizer_state_dict"])
        torch.set_rng_state(state["torch_rng_state"])
        torch.cuda.set_rng_state_all(state["cuda_rng_states"])
        resumed_from_checkpoint_identity = checkpoint["checkpoint_identity"]
        previous_checkpoint_identity = checkpoint["checkpoint_identity"]
        losses = [float(state["last_loss"])]
    elif progress_rows:
        raise SystemExit("training progress exists without resumable checkpoint")
    optimizer.zero_grad(set_to_none=True)
    if checkpoint is None:
        losses = []
        steps = 0
    started_ns = time.monotonic_ns()
    torch.cuda.reset_peak_memory_stats()
    batch_started_ns = time.monotonic_ns()
    if checkpoint is not None:
        progress_events += 1
        progress_identity = progress_event(
            output,
            previous_identity=progress_identity,
            event_ordinal=progress_events,
            event="RESUME_FROM_CHECKPOINT",
            epoch=1,
            position=start_position,
            row_index=int(checkpoint["row_index"]),
            example_id=str(checkpoint["example_id"]),
            token_count=int(checkpoint["token_count"]),
            optimizer_steps_completed=steps,
            started_ns=started_ns,
        )
    for epoch in range(epochs):
        order = list(range(len(rows)))
        random.Random(seed + epoch).shuffle(order)
        if mode == "BATCH_SMOKE":
            probe_microsteps = int(config.get("performance_probe_microsteps", accumulation))
            if not 1 <= probe_microsteps <= accumulation:
                raise SystemExit("performance probe cardinality mismatch")
            order = order[:probe_microsteps]
        for position, index in enumerate(order, 1):
            if position <= start_position:
                continue
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
            progress_events += 1
            progress_identity = progress_event(
                output,
                previous_identity=progress_identity,
                event_ordinal=progress_events,
                event="MICROSTEP_STARTED",
                epoch=epoch + 1,
                position=position,
                row_index=index,
                example_id=rows[index]["example_id"],
                token_count=len(tokens),
                optimizer_steps_completed=steps,
                started_ns=started_ns,
            )
            input_ids = torch.tensor([tokens], device="cuda")
            labels = input_ids.clone()
            labels[:, : len(prefix)] = -100
            attention_context = nullcontext()
            if "flash" in performance_capabilities:
                attention_context = sdpa_kernel(SDPBackend.FLASH_ATTENTION)
            elif performance_variant == "EFFICIENT_ONLY":
                attention_context = sdpa_kernel(SDPBackend.EFFICIENT_ATTENTION)
            autocast_context = nullcontext()
            if "bf16" in performance_capabilities:
                autocast_context = torch.autocast(device_type="cuda", dtype=torch.bfloat16)
            selective_logits = "selective_logits" in performance_capabilities
            with autocast_context, attention_context:
                if selective_logits:
                    logit_start, logit_stop = assistant_logit_span(len(prefix), len(tokens))
                    logit_indices = torch.arange(logit_start, logit_stop, device="cuda")
                    result = loaded(
                        input_ids=input_ids,
                        use_cache=False,
                        logits_to_keep=logit_indices,
                    )
                    raw_loss = torch.nn.functional.cross_entropy(
                        result.logits.float().reshape(-1, result.logits.shape[-1]),
                        labels[:, len(prefix) :].reshape(-1),
                    )
                else:
                    result = loaded(input_ids=input_ids, labels=labels, use_cache=False)
                    raw_loss = result.loss
            if performance_variant is not None:
                performance_snapshot(output, torch, f"FORWARD_COMPLETED_POSITION_{position}", batch_started_ns)
            loss = raw_loss / accumulation
            loss.backward()
            if performance_variant is not None:
                performance_snapshot(output, torch, f"BACKWARD_COMPLETED_POSITION_{position}", batch_started_ns)
            losses.append(float(raw_loss.detach().cpu()))
            progress_events += 1
            progress_identity = progress_event(
                output,
                previous_identity=progress_identity,
                event_ordinal=progress_events,
                event="MICROSTEP_COMPLETED",
                epoch=epoch + 1,
                position=position,
                row_index=index,
                example_id=rows[index]["example_id"],
                token_count=len(tokens),
                optimizer_steps_completed=steps,
                started_ns=started_ns,
            )
            if position % accumulation == 0:
                optimizer.step()
                torch.cuda.synchronize()
                optimizer.zero_grad(set_to_none=True)
                steps += 1
                checkpoint = save_checkpoint(
                    output=output,
                    loaded=loaded,
                    optimizer=optimizer,
                    torch=torch,
                    position=position,
                    row_index=index,
                    example_id=rows[index]["example_id"],
                    token_count=len(tokens),
                    steps=steps,
                    last_loss=losses[-1],
                    previous_checkpoint_identity=previous_checkpoint_identity,
                    authority=checkpoint_authority,
                )
                previous_checkpoint_identity = checkpoint["checkpoint_identity"]
                progress_events += 1
                progress_identity = progress_event(
                    output,
                    previous_identity=progress_identity,
                    event_ordinal=progress_events,
                    event="OPTIMIZER_STEP_COMPLETED",
                    epoch=epoch + 1,
                    position=position,
                    row_index=index,
                    example_id=rows[index]["example_id"],
                    token_count=len(tokens),
                    optimizer_steps_completed=steps,
                    started_ns=started_ns,
                )
                if mode == "CHECKPOINT_SMOKE":
                    return 75
    loaded.save_pretrained(output, safe_serialization=True)
    canonicalize_adapter_config(output)
    base = loaded.unload()
    reloaded = PeftModel.from_pretrained(base, output, is_trainable=False)
    if not any(True for _ in reloaded.peft_config):
        raise SystemExit("saved successor reload failed")
    if not any(Path("/tmp/triton-cache").rglob("*")) and checkpoint is None:
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
        "progress_event_count": progress_events,
        "progress_final_identity": progress_identity,
        "checkpoint_count": steps,
        "final_checkpoint_identity": previous_checkpoint_identity,
        "resumed_from_checkpoint_identity": resumed_from_checkpoint_identity,
        "training_mode": effective_mode,
        "final_loss": format(losses[-1], ".17g"),
        "network_activity": False,
        "qualification_attempt_consumed": False,
        "candidate_execution_performed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    if performance_variant is not None:
        torch.cuda.synchronize()
        receipt["performance_bakeoff"] = {
            "variant": performance_variant,
            "attention_backend_enforcement": (
                "FLEX_ATTENTION"
                if "flex" in performance_capabilities
                else
                "FLASH_ONLY"
                if "flash" in performance_capabilities
                else "EFFICIENT_ONLY"
                if performance_variant == "EFFICIENT_ONLY"
                else "AUTOMATIC_SDPA"
            ),
            "allocator": (
                "EXPANDABLE_SEGMENTS"
                if "expandable_allocator" in performance_capabilities
                else "DEFAULT"
            ),
            "gqa_strategy": (
                "REPEAT_KV_TO_QUERY_HEAD_COUNT"
                if "repeat_kv" in performance_capabilities
                else "NATIVE_ENABLE_GQA"
            ),
            "autocast_dtype": (
                "BF16"
                if "bf16" in performance_capabilities
                else "DISABLED"
            ),
            "logits_scope": "ASSISTANT_TARGETS_PLUS_PRECEDING_PREDICTOR" if selective_logits else "FULL_SEQUENCE",
            "elapsed_ms": (time.monotonic_ns() - batch_started_ns) // 1_000_000,
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
        }
    core = json.dumps(receipt, separators=(",", ":"), sort_keys=True).encode()
    receipt["receipt_identity"] = hashlib.sha256(core).hexdigest()
    (output / "training-receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
