"""Linux child for one load-only attempt; imported runtime packages only when called."""
from __future__ import annotations

import gc
from multiprocessing.queues import Queue


BASE_MODEL_PATH = "/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142"
ADAPTER_PATH = "/home/pastila/PastilaAcida-Model-Lab/experimental-0.3/runs/pastila-editor-core-v1-2-deontology-20260820-003/checkpoint-final/adapter"


def run_load_only_linux_child_v1(*, events: Queue) -> None:
    """Load once, attach once, preserve vision, and release the CUDA context."""
    torch = None
    model = None
    try:
        import torch as runtime_torch
        from peft import PeftModel
        from transformers import AutoModelForImageTextToText, BitsAndBytesConfig

        torch = runtime_torch
        quantization = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
        model = AutoModelForImageTextToText.from_pretrained(
            BASE_MODEL_PATH, local_files_only=True,
            quantization_config=quantization, device_map={"": 0},
            dtype=torch.bfloat16, low_cpu_mem_usage=True,
        )
        model = PeftModel.from_pretrained(
            model, ADAPTER_PATH, is_trainable=False)
        model.eval()
        events.put(("MODEL_LOAD_COMPLETED", None))
    except Exception as exc:
        events.put(("MODEL_LOAD_FAILED", type(exc).__name__))
        raise
    finally:
        if model is not None:
            del model
        gc.collect()
        if torch is not None:
            torch.cuda.empty_cache()
        events.put(("MODEL_LOAD_CLEANUP_COMPLETED", None))


__all__ = ("ADAPTER_PATH", "BASE_MODEL_PATH", "run_load_only_linux_child_v1")
