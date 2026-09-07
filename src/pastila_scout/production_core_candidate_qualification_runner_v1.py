"""Frozen-rootfs batch runner for comparative Core V2 candidate qualification."""

from __future__ import annotations

import hashlib
import json
import os
import resource
import sys
import time
from pathlib import Path

EXPECTED_ENV = {
    "CUBLAS_WORKSPACE_CONFIG": ":4096:8",
    "CUDA_VISIBLE_DEVICES": "0",
    "HF_HUB_OFFLINE": "1",
    "PYTHONHASHSEED": "0",
    "TOKENIZERS_PARALLELISM": "false",
    "TRANSFORMERS_OFFLINE": "1",
    "TRITON_CACHE_DIR": "/tmp/triton-cache",
    "TRITON_LIBCUDA_PATH": "/usr/lib/wsl/lib",
}
EXPECTED_RUNTIME = {
    "bitsandbytes": "0.50.1",
    "peft": "0.20.0",
    "torch": "2.13.0+cu130",
    "transformers": "5.15.0",
}
EXPECTED_ADAPTERS = {
    "pastila-editor-core-v1.1-experimental": "0bc4bb1b83b5c1375c1e676844dea079831e7ad0b90db955fa89a2f7d65c3e47",
    "pastila-editor-core-v1.2-experimental": "22b5a7bde7194c66d895b9acab5791a8d8573df67f93704eab933666df7978a2",
}
EXPECTED_BASE = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
EXPECTED_PROMPTS = {
    "pastila-editor-core-v1.1-experimental": "9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc",
    "pastila-editor-core-v1.2-experimental": "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17",
}
MAX_INPUT = 1924
MAX_OUTPUT = 6268
MAX_WALL_NS = 600_000_000_000
MAX_RSS = 16_106_127_360


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _manifest(root: Path) -> str:
    rows = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode()):
        if path.is_symlink() or not path.is_file():
            raise SystemExit("candidate object closure mismatch")
        data = path.read_bytes()
        rows.append(path.name.encode() + b"\0" + len(data).to_bytes(8, "big") + hashlib.sha256(data).digest())
    return _sha(b"".join(rows))


def _write_new(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink() or path.parent != Path("/tmp/output"):
        raise SystemExit("output collision or containment failure")
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _heartbeat(value: dict[str, object]) -> None:
    target = Path("/tmp/output/heartbeat.json")
    temporary = Path("/tmp/output/.heartbeat.tmp")
    temporary.write_bytes(json.dumps(value, separators=(",", ":")).encode())
    os.replace(temporary, target)


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit("usage: runner MODEL ADAPTER PROMPT BATCH CANDIDATE")
    model, adapter, prompt_path, batch_path = map(Path, sys.argv[1:5])
    candidate = sys.argv[5]
    authority_names = {"BATCH_SHA256", "PROMPT_SHA256", "QUALIFICATION_GENERATION_IDENTITY", "ROOTFS_SHA256", "RUNNER_SHA256"}
    if set(os.environ) != set(EXPECTED_ENV) | authority_names:
        raise SystemExit("qualification environment mismatch")
    if {key: value for key, value in os.environ.items() if key not in authority_names} != EXPECTED_ENV:
        raise SystemExit("qualification environment values mismatch")
    if candidate not in EXPECTED_ADAPTERS or _manifest(model) != EXPECTED_BASE:
        raise SystemExit("base or candidate authority mismatch")
    if _manifest(adapter) != EXPECTED_ADAPTERS[candidate]:
        raise SystemExit("adapter authority mismatch")
    prompt_bytes = prompt_path.read_bytes()
    if _sha(prompt_bytes) != EXPECTED_PROMPTS[candidate] or _sha(prompt_bytes) != os.environ["PROMPT_SHA256"]:
        raise SystemExit("system prompt authority mismatch")
    if _sha(Path(__file__).read_bytes()) != os.environ["RUNNER_SHA256"]:
        raise SystemExit("runner snapshot mismatch")
    batch = json.loads(batch_path.read_bytes())
    if _sha(batch_path.read_bytes()) != os.environ["BATCH_SHA256"] or not isinstance(batch, list) or len(batch) != 200:
        raise SystemExit("batch cardinality mismatch")

    import bitsandbytes
    import peft
    import torch
    import transformers
    from peft import PeftModel
    from torch._native.registry import deregister_op_overrides
    from transformers import (
        AutoModelForImageTextToText,
        AutoTokenizer,
        BitsAndBytesConfig,
    )

    versions = {
        "bitsandbytes": bitsandbytes.__version__, "peft": peft.__version__,
        "torch": torch.__version__, "transformers": transformers.__version__,
    }
    if versions != EXPECTED_RUNTIME or not torch.cuda.is_available():
        raise SystemExit("frozen runtime mismatch")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)
    deregister_op_overrides(disable_op_symbols="bmm")
    tokenizer = AutoTokenizer.from_pretrained(
        model, local_files_only=True, fix_mistral_regex=True
    )
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    configuration = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True,
    )
    load_started = time.monotonic_ns()
    _heartbeat({"stage": "LOAD", "deadline_boottime_ns": time.clock_gettime_ns(time.CLOCK_BOOTTIME) + MAX_WALL_NS})
    loaded = AutoModelForImageTextToText.from_pretrained(
        model, local_files_only=True, quantization_config=configuration,
        device_map={"": 0}, dtype=torch.bfloat16, attn_implementation="sdpa",
        low_cpu_mem_usage=True,
    )
    loaded.model.vision_tower = None
    loaded.model.multi_modal_projector = None
    loaded = PeftModel.from_pretrained(loaded, adapter, is_trainable=False)
    loaded.eval()
    load_ns = time.monotonic_ns() - load_started
    for row in batch:
        if list(row) != ["case_id", "request_identity", "prompt"]:
            raise SystemExit("batch row schema/order mismatch")
        case_id = row["case_id"]
        request_identity = row["request_identity"]
        messages = [
            {"role": "system", "content": prompt_bytes.decode("utf-8", errors="strict")},
            {"role": "user", "content": row["prompt"]},
        ]
        encoded = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_tensors="pt", return_dict=True,
        )
        input_tokens = int(encoded["input_ids"].shape[1])
        if input_tokens > MAX_INPUT:
            raise SystemExit("input token ceiling exceeded")
        encoded = {key: value.to("cuda") for key, value in encoded.items()}
        torch.cuda.reset_peak_memory_stats()
        started = time.monotonic_ns()
        _heartbeat({"stage": "GENERATE", "case_id": case_id, "deadline_boottime_ns": time.clock_gettime_ns(time.CLOCK_BOOTTIME) + MAX_WALL_NS - load_ns})
        with torch.inference_mode():
            generated = loaded.generate(
                **encoded, do_sample=False, num_beams=1, repetition_penalty=1.0,
                max_new_tokens=MAX_OUTPUT, eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id, use_cache=True,
            )
        generation_ns = time.monotonic_ns() - started
        tokens = generated[0, input_tokens:].cpu()
        output = tokenizer.decode(tokens, skip_special_tokens=True).encode("utf-8")
        terminal_eos = bool(len(tokens) and int(tokens[-1]) == tokenizer.eos_token_id)
        peak_rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
        if (
            not terminal_eos or len(tokens) > MAX_OUTPUT or len(output) > 6268
            or load_ns + generation_ns > MAX_WALL_NS or peak_rss > MAX_RSS
        ):
            raise SystemExit("candidate result exceeded frozen execution envelope")
        stem = f"{case_id}.{request_identity.removeprefix('sha256:')}"
        _write_new(Path("/tmp/output") / f"{stem}.raw", output)
        observation_core = {
            "schema": "pastila-production-core-frozen-runner-observation",
            "schema_version": 1,
            "qualification_generation_identity": os.environ["QUALIFICATION_GENERATION_IDENTITY"],
            "candidate": candidate,
            "rootfs_sha256": os.environ["ROOTFS_SHA256"],
            "base_manifest_sha256": EXPECTED_BASE,
            "adapter_manifest_sha256": EXPECTED_ADAPTERS[candidate],
            "system_prompt_sha256": EXPECTED_PROMPTS[candidate],
            "batch_sha256": _sha(batch_path.read_bytes()),
            "runner_sha256": os.environ["RUNNER_SHA256"],
            "case_id": case_id,
            "request_identity": request_identity,
            "input_tokens": input_tokens,
            "output_tokens": len(tokens),
            "load_wall_ns": load_ns,
            "generation_wall_ns": generation_ns,
            "peak_rss_bytes": peak_rss,
            "raw_output_sha256": _sha(output),
            "runtime_versions": versions,
            "terminal_eos": terminal_eos,
        }
        observation = {**observation_core, "observation_identity": _sha(json.dumps(observation_core, ensure_ascii=False, separators=(",", ":")).encode())}
        _write_new(
            Path("/tmp/output") / f"{stem}.observation.json",
            json.dumps(observation, ensure_ascii=False, separators=(",", ":")).encode(),
        )
        _heartbeat({"stage": "CASE_COMPLETE", "case_id": case_id, "deadline_boottime_ns": time.clock_gettime_ns(time.CLOCK_BOOTTIME) + MAX_WALL_NS})
    _heartbeat({"stage": "BATCH_COMPLETE", "deadline_boottime_ns": time.clock_gettime_ns(time.CLOCK_BOOTTIME) + MAX_WALL_NS})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
