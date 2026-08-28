"""V1.1 load-only child with exact adapter-warning compatibility enforcement."""
from __future__ import annotations

import ast
import gc
import json
import struct
import warnings
from dataclasses import replace
from multiprocessing.queues import Queue
from pathlib import Path

from .stage_p_construction_obligation_v2_adapter_compatibility_gate_v1 import (
    canonical_adapter_compatibility_observation_v1,
    validate_adapter_compatibility_gate_v1,
)
from .stage_p_construction_obligation_v2_model_load_linux_worker_v1 import (
    ADAPTER_PATH, BASE_MODEL_PATH,
)


WORKER_V1_1_IDENTITY = "c34bf8d854b1d873cdd320773d477b04e18a4f3d88475f2a5bcd2225813ca37c"
_MISSING_PREFIX = "Found missing adapter keys while loading the checkpoint: "


def parse_peft_missing_adapter_warning_v1(*, messages: tuple[str, ...]) -> tuple[str, ...]:
    if len(messages) != 1 or not messages[0].startswith(_MISSING_PREFIX) or not messages[0].endswith("."):
        raise ValueError("MODEL_LOAD_PEFT_WARNING_SET_UNEXPECTED")
    try:
        value = ast.literal_eval(messages[0][len(_MISSING_PREFIX):-1])
    except Exception as exc:
        raise ValueError("MODEL_LOAD_PEFT_MISSING_KEYS_WARNING_INVALID") from exc
    if type(value) is not list or any(type(item) is not str for item in value):
        raise ValueError("MODEL_LOAD_PEFT_MISSING_KEYS_WARNING_INVALID")
    return tuple(sorted(value))


def adapter_tensor_keys_from_header_v1(*, adapter_path: Path) -> tuple[str, ...]:
    with (adapter_path / "adapter_model.safetensors").open("rb") as handle:
        header_length = struct.unpack("<Q", handle.read(8))[0]
        if not 1 <= header_length <= 16 * 1024 * 1024:
            raise ValueError("MODEL_LOAD_ADAPTER_HEADER_LENGTH_INVALID")
        header = json.loads(handle.read(header_length).decode("utf-8", errors="strict"))
    if type(header) is not dict:
        raise ValueError("MODEL_LOAD_ADAPTER_HEADER_SHAPE_INVALID")
    return tuple(sorted(key for key in header if key != "__metadata__"))


def run_load_only_linux_child_v1_1(*, events: Queue) -> None:
    torch = None
    model = None
    try:
        adapter_keys = adapter_tensor_keys_from_header_v1(adapter_path=Path(ADAPTER_PATH))
        import torch as runtime_torch
        from peft import PeftModel
        from transformers import AutoModelForImageTextToText, BitsAndBytesConfig

        torch = runtime_torch
        quantization = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
        model = AutoModelForImageTextToText.from_pretrained(
            BASE_MODEL_PATH, local_files_only=True, quantization_config=quantization,
            device_map={"": 0}, dtype=torch.bfloat16, low_cpu_mem_usage=True)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            model = PeftModel.from_pretrained(
                model, ADAPTER_PATH, is_trainable=False)
        messages = tuple(str(item.message) for item in caught)
        missing_keys = parse_peft_missing_adapter_warning_v1(messages=messages)
        observed = replace(canonical_adapter_compatibility_observation_v1(),
                           adapter_tensor_keys=adapter_keys,
                           missing_adapter_keys=missing_keys)
        compatibility_receipt = validate_adapter_compatibility_gate_v1(observed=observed)
        model.eval()
        events.put(("MODEL_LOAD_COMPLETED", None, compatibility_receipt.decode("ascii")))
    except Exception as exc:
        events.put(("MODEL_LOAD_FAILED", type(exc).__name__, None))
        raise
    finally:
        if model is not None:
            del model
        gc.collect()
        if torch is not None:
            torch.cuda.empty_cache()
        events.put(("MODEL_LOAD_CLEANUP_COMPLETED", None, None))


__all__ = (
    "WORKER_V1_1_IDENTITY", "adapter_tensor_keys_from_header_v1",
    "parse_peft_missing_adapter_warning_v1", "run_load_only_linux_child_v1_1",
)
