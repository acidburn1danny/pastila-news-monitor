"""Candidate-neutral, non-semantic inference resource calibration probe."""

from __future__ import annotations

import gc
import hashlib
import json
import os
import sys
import time
from pathlib import Path

EXPECTED_RUNTIME = {
    "torch": "2.13.0+cu130",
    "transformers": "5.15.0",
    "peft": "0.20.0",
    "bitsandbytes": "0.50.1",
}
CANDIDATES = {
    "pastila-editor-core-v1.1-experimental",
    "pastila-editor-core-v1.2-experimental",
}
BASE_MANIFEST_SHA256 = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
ADAPTER_MANIFESTS = {
    "pastila-editor-core-v1.1-experimental": "0bc4bb1b83b5c1375c1e676844dea079831e7ad0b90db955fa89a2f7d65c3e47",
    "pastila-editor-core-v1.2-experimental": "22b5a7bde7194c66d895b9acab5791a8d8573df67f93704eab933666df7978a2",
}
TOTAL_CONTEXT_TOKENS = 8192
GENERATION_PROMPT_TOKENS = 1924
TECHNICAL_TOKEN_CEILING = 6268
PREFILL_TRIALS = 3
GENERATION_TRIALS = 1


def _file_manifest(root: Path) -> tuple[str, int, int]:
    records: list[bytes] = []
    total = 0
    count = 0
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode("utf-8")):
        if not path.is_file():
            raise SystemExit("calibration object contains a non-file entry")
        data = path.read_bytes()
        total += len(data)
        count += 1
        records.append(
            path.name.encode("utf-8")
            + b"\0"
            + len(data).to_bytes(8, "big")
            + hashlib.sha256(data).digest()
        )
    if not records:
        raise SystemExit("empty calibration object")
    return hashlib.sha256(b"".join(records)).hexdigest(), total, count


def _rss_bytes() -> int:
    import resource

    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024


def _now() -> int:
    import torch

    torch.cuda.synchronize()
    return time.monotonic_ns()


def main() -> int:
    self_bytes = Path(__file__).read_bytes()
    if GENERATION_PROMPT_TOKENS + TECHNICAL_TOKEN_CEILING != TOTAL_CONTEXT_TOKENS:
        raise SystemExit("invalid total-context calibration matrix")
    if len(sys.argv) != 4:
        raise SystemExit("invalid calibration arguments")
    base, adapter = Path(sys.argv[1]), Path(sys.argv[2])
    candidate = sys.argv[3]
    if candidate not in CANDIDATES or not base.is_dir() or not adapter.is_dir():
        raise SystemExit("invalid calibration authority")
    expected_fixed_environment = {
        "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
        "CUDA_VISIBLE_DEVICES": "0",
        "HF_HUB_OFFLINE": "1",
        "PYTHONHASHSEED": "0",
        "TOKENIZERS_PARALLELISM": "false",
        "TRANSFORMERS_OFFLINE": "1",
        "TRITON_LIBCUDA_PATH": "/usr/lib/wsl/lib",
        "TRITON_CACHE_DIR": "/tmp/triton-cache",
    }
    authority_names = {
        "CALIBRATION_COMMIT", "CALIBRATION_TREE", "CALIBRATION_PROBE_SHA256",
        "CALIBRATION_LAUNCHER_SHA256", "CALIBRATION_ROOTFS_SHA256",
    }
    if {k: v for k, v in os.environ.items() if k not in authority_names} != expected_fixed_environment:
        raise SystemExit("invalid calibration environment")
    if set(os.environ) != set(expected_fixed_environment) | authority_names:
        raise SystemExit("invalid calibration authority environment")
    for name in authority_names:
        value = os.environ[name]
        expected_length = 40 if name in {"CALIBRATION_COMMIT", "CALIBRATION_TREE"} else 64
        if len(value) != expected_length or any(ch not in "0123456789abcdef" for ch in value):
            raise SystemExit("invalid calibration authority identity")
    if hashlib.sha256(self_bytes).hexdigest() != os.environ["CALIBRATION_PROBE_SHA256"]:
        raise SystemExit("calibration probe snapshot mismatch")

    base_before = _file_manifest(base)
    adapter_before = _file_manifest(adapter)
    if base_before[0] != BASE_MANIFEST_SHA256 or adapter_before[0] != ADAPTER_MANIFESTS[candidate]:
        raise SystemExit("candidate object identity mismatch")

    import bitsandbytes
    import peft
    import torch
    import transformers
    from peft import PeftModel
    from torch._native.registry import deregister_op_overrides
    from transformers import AutoModelForImageTextToText, BitsAndBytesConfig

    versions = {
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "peft": peft.__version__,
        "bitsandbytes": bitsandbytes.__version__,
    }
    if versions != EXPECTED_RUNTIME or not torch.cuda.is_available():
        raise SystemExit("frozen inference runtime mismatch")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    deregister_op_overrides(disable_op_symbols="bmm")
    load_started = _now()
    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    model = AutoModelForImageTextToText.from_pretrained(
        base,
        local_files_only=True,
        quantization_config=quantization,
        device_map={"": 0},
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
        low_cpu_mem_usage=True,
    )
    model.model.vision_tower = None
    model.model.multi_modal_projector = None
    model = PeftModel.from_pretrained(model, adapter, is_trainable=False)
    model.eval()
    load_elapsed = _now() - load_started
    load_rss = _rss_bytes()
    torch.cuda.reset_peak_memory_stats()

    # Token IDs are synthetic structural input, never decoded or semantically inspected.
    max_input_ids = (torch.arange(TOTAL_CONTEXT_TOKENS, device="cuda") % 1000 + 1000).long().unsqueeze(0)
    max_attention = torch.ones_like(max_input_ids)
    prefill_trials: list[dict[str, int]] = []
    with torch.inference_mode():
        for _ in range(PREFILL_TRIALS):
            torch.cuda.reset_peak_memory_stats()
            started = _now()
            result = model(input_ids=max_input_ids, attention_mask=max_attention, use_cache=False)
            prefill_elapsed = _now() - started
            prefill_trials.append({
                "wall_ns": prefill_elapsed,
                "peak_rss_bytes": _rss_bytes(),
                "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated(),
                "peak_cuda_reserved_bytes": torch.cuda.max_memory_reserved(),
            })
            del result
            gc.collect()
            torch.cuda.empty_cache()

        generation_trials: list[dict[str, int | str]] = []
        generation_input = (torch.arange(GENERATION_PROMPT_TOKENS, device="cuda") % 1000 + 1000).long().unsqueeze(0)
        generation_attention = torch.ones_like(generation_input)
        for _ in range(GENERATION_TRIALS):
            torch.cuda.reset_peak_memory_stats()
            started = _now()
            result = model(input_ids=generation_input, attention_mask=generation_attention, use_cache=True)
            past = result.past_key_values
            next_token = result.logits[:, -1:].argmax(dim=-1)
            token_hasher = hashlib.sha256()
            for _step in range(TECHNICAL_TOKEN_CEILING):
                token_hasher.update(int(next_token.item()).to_bytes(4, "big"))
                result = model(input_ids=next_token, past_key_values=past, use_cache=True)
                past = result.past_key_values
                next_token = result.logits[:, -1:].argmax(dim=-1)
            generation_trials.append(
                {
                    "wall_ns": _now() - started,
                    "peak_rss_bytes": _rss_bytes(),
                    "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated(),
                    "peak_cuda_reserved_bytes": torch.cuda.max_memory_reserved(),
                    "token_identity": token_hasher.hexdigest(),
                }
            )
            del result, past, next_token
            gc.collect()
            torch.cuda.empty_cache()

    if _file_manifest(base) != base_before or _file_manifest(adapter) != adapter_before:
        raise SystemExit("calibration object mutated during execution")
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != os.environ["CALIBRATION_PROBE_SHA256"]:
        raise SystemExit("calibration probe mutated during execution")
    receipt = {
        "schema": "pastila-production-core-inference-resource-calibration-observation",
        "schema_version": 1,
        "authority_effect": "NON_SEMANTIC_OBSERVATION_NOT_OWNER_APPROVED_LIMITS",
        "execution_authority": {
            "commit": os.environ["CALIBRATION_COMMIT"],
            "tree": os.environ["CALIBRATION_TREE"],
            "probe_sha256": os.environ["CALIBRATION_PROBE_SHA256"],
            "launcher_sha256": os.environ["CALIBRATION_LAUNCHER_SHA256"],
            "rootfs_sha256": os.environ["CALIBRATION_ROOTFS_SHA256"],
        },
        "candidate": candidate,
        "base_manifest": {"sha256": base_before[0], "bytes": base_before[1], "files": base_before[2]},
        "adapter_manifest": {"sha256": adapter_before[0], "bytes": adapter_before[1], "files": adapter_before[2]},
        "runtime_versions": versions,
        "profile": {
            "total_context_tokens": TOTAL_CONTEXT_TOKENS,
            "max_prefill_tokens": TOTAL_CONTEXT_TOKENS,
            "generation_prompt_tokens": GENERATION_PROMPT_TOKENS,
            "generated_tokens": TECHNICAL_TOKEN_CEILING,
            "technical_token_ceiling": TECHNICAL_TOKEN_CEILING,
            "prefill_trials": PREFILL_TRIALS,
            "generation_trials": GENERATION_TRIALS,
            "nf4_bf16_double_quant": True,
            "deterministic": True,
            "semantic_input": False,
            "output_decoded_or_inspected": False,
            "triton_cache": "EPHEMERAL_TMPFS",
            "torch_native_bmm_override": "DISABLED_TO_USE_PINNED_ATEN_FALLBACK",
        },
        "load_wall_ns": load_elapsed,
        "load_peak_rss_bytes": load_rss,
        "prefill_trials": prefill_trials,
        "generation_trials": generation_trials,
        "candidate_model_executed_non_semantically": True,
        "semantic_candidate_evaluation": False,
        "candidate_promotion_effect": False,
        "network": "DENY_ALL_NEW_NAMESPACE",
    }
    encoded = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
    print(encoded.decode("utf-8"))
    print(hashlib.sha256(encoded).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
