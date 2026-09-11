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
    "pastila-editor-core-v1.1-json-successor-v2": "0b3b8c317b8bfbf73dd4c131d92f1bc768d5e638034a49cecdc76da2d4e07f4b",
    "pastila-editor-core-v1.2-json-successor": "dccfee343ad1e305a0e193501b3a8adba11da01afd3d890ee38275dda82ac719",
}
EXPECTED_BASE = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
EXPECTED_PROMPTS = {
    "pastila-editor-core-v1.1-json-successor-v2": "9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc",
    "pastila-editor-core-v1.2-json-successor": "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17",
}
MAX_INPUT = 1924
MAX_OUTPUT = 6268
MAX_WALL_NS = 600_000_000_000
MAX_RSS = 16_106_127_360
EXPECTED_GENERATION = "6d388a99731e3d4a08fa2a629374c37dd97994806ac54ffe49ab9fb1b41d630d"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _manifest(root: Path) -> str:
    rows = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.encode()):
        if path.is_symlink() or not path.is_file():
            raise SystemExit("candidate object closure mismatch")
        data = path.read_bytes()
        rows.append(
            path.name.encode()
            + b"\0"
            + len(data).to_bytes(8, "big")
            + hashlib.sha256(data).digest()
        )
    return _sha(b"".join(rows))


def _write_new(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink() or path.parent != Path("/tmp/output"):
        raise SystemExit("output collision or containment failure")
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def _boottime_centisecond_ns() -> int:
    uptime = Path("/proc/uptime").read_text("ascii").split(maxsplit=1)[0]
    whole, separator, fraction = uptime.partition(".")
    if not separator or not whole.isascii() or not whole.isdigit():
        raise SystemExit("CLOCK_BOOTTIME authority malformed")
    centiseconds = (fraction + "00")[:2]
    if not centiseconds.isascii() or not centiseconds.isdigit():
        raise SystemExit("CLOCK_BOOTTIME authority malformed")
    return int(whole) * 1_000_000_000 + int(centiseconds) * 10_000_000


def _heartbeat(
    stage: str, sequence: int, completed_count: int, case_id: str | None = None
) -> None:
    target = Path("/tmp/output/heartbeat.json")
    temporary = Path("/tmp/output/.heartbeat.tmp")
    value: dict[str, object] = {
        "stage": stage,
        "sequence": sequence,
        "completed_count": completed_count,
    }
    if case_id is not None:
        value["case_id"] = case_id
    value["deadline_boottime_ns"] = _boottime_centisecond_ns() + MAX_WALL_NS
    temporary.write_bytes(json.dumps(value, separators=(",", ":")).encode())
    os.replace(temporary, target)


def main() -> int:
    if len(sys.argv) != 6:
        raise SystemExit("usage: runner MODEL ADAPTER PROMPT BATCH CANDIDATE")
    model, adapter, prompt_path, batch_path = map(Path, sys.argv[1:5])
    candidate = sys.argv[5]
    authority_names = {
        "BATCH_SHA256",
        "PROMPT_SHA256",
        "QUALIFICATION_GENERATION_IDENTITY",
        "ROOTFS_SHA256",
        "RUNNER_SHA256",
    }
    if set(os.environ) != set(EXPECTED_ENV) | authority_names:
        raise SystemExit("qualification environment mismatch")
    if {
        key: value for key, value in os.environ.items() if key not in authority_names
    } != EXPECTED_ENV:
        raise SystemExit("qualification environment values mismatch")
    if os.environ["QUALIFICATION_GENERATION_IDENTITY"] != EXPECTED_GENERATION:
        raise SystemExit("qualification generation authority mismatch")
    if candidate not in EXPECTED_ADAPTERS or _manifest(model) != EXPECTED_BASE:
        raise SystemExit("base or candidate authority mismatch")
    if _manifest(adapter) != EXPECTED_ADAPTERS[candidate]:
        raise SystemExit("adapter authority mismatch")
    prompt_bytes = prompt_path.read_bytes()
    if (
        _sha(prompt_bytes) != EXPECTED_PROMPTS[candidate]
        or _sha(prompt_bytes) != os.environ["PROMPT_SHA256"]
    ):
        raise SystemExit("system prompt authority mismatch")
    if _sha(Path(__file__).read_bytes()) != os.environ["RUNNER_SHA256"]:
        raise SystemExit("runner snapshot mismatch")
    batch = json.loads(batch_path.read_bytes())
    if (
        _sha(batch_path.read_bytes()) != os.environ["BATCH_SHA256"]
        or not isinstance(batch, list)
        or len(batch) != 200
    ):
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
        StoppingCriteria,
        StoppingCriteriaList,
    )

    versions = {
        "bitsandbytes": bitsandbytes.__version__,
        "peft": peft.__version__,
        "torch": torch.__version__,
        "transformers": transformers.__version__,
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

    class OutputByteCeiling(StoppingCriteria):
        """Stop once a response cannot satisfy the frozen UTF-8 byte envelope."""

        def __init__(self, prompt_tokens: int) -> None:
            self.prompt_tokens = prompt_tokens
            self.exceeded = False

        def __call__(self, input_ids, scores, **kwargs):
            response = input_ids[0, self.prompt_tokens :]
            if response.shape[0] % 32:
                return False
            response = response.detach().cpu()
            size = len(tokenizer.decode(response, skip_special_tokens=True).encode("utf-8"))
            self.exceeded = size > 6268
            return self.exceeded
    configuration = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    load_started = time.monotonic_ns()
    _heartbeat("LOAD", 0, 0)
    loaded = AutoModelForImageTextToText.from_pretrained(
        model,
        local_files_only=True,
        quantization_config=configuration,
        device_map={"": 0},
        dtype=torch.bfloat16,
        attn_implementation="sdpa",
        low_cpu_mem_usage=True,
    )
    loaded.model.vision_tower = None
    loaded.model.multi_modal_projector = None
    loaded = PeftModel.from_pretrained(loaded, adapter, is_trainable=False)
    loaded.eval()
    load_ns = time.monotonic_ns() - load_started
    for sequence, row in enumerate(batch, 1):
        if list(row) != ["case_id", "request_identity", "prompt", "prompt_sha256"]:
            raise SystemExit("batch row schema/order mismatch")
        case_id = row["case_id"]
        request_identity = row["request_identity"]
        if _sha(row["prompt"].encode("utf-8", errors="strict")) != row["prompt_sha256"]:
            raise SystemExit("candidate-visible request snapshot mismatch")
        messages = [
            {
                "role": "system",
                "content": prompt_bytes.decode("utf-8", errors="strict"),
            },
            {"role": "user", "content": row["prompt"]},
        ]
        encoded = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
            return_dict=True,
        )
        input_tokens = int(encoded["input_ids"].shape[1])
        if input_tokens > MAX_INPUT:
            raise SystemExit("input token ceiling exceeded")
        encoded = {key: value.to("cuda") for key, value in encoded.items()}
        torch.cuda.reset_peak_memory_stats()
        started = time.monotonic_ns()
        inference_start_core = {
            "schema": "pastila-production-core-inference-lifecycle-event",
            "schema_version": 1,
            "phase": "STARTED",
            "sequence": sequence,
            "completed_count": sequence - 1,
            "case_id": case_id,
            "request_identity": request_identity,
            "input_tokens": input_tokens,
            "started_boottime_ns": _boottime_centisecond_ns(),
        }
        inference_start = {
            **inference_start_core,
            "event_identity": _sha(
                json.dumps(
                    inference_start_core,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode()
            ),
        }
        _write_new(
            Path("/tmp/output") / f"inference-{sequence:03d}-started.json",
            json.dumps(
                inference_start, ensure_ascii=False, separators=(",", ":")
            ).encode(),
        )
        _heartbeat("GENERATE", sequence, sequence - 1, case_id)
        byte_ceiling = OutputByteCeiling(input_tokens)
        with torch.inference_mode():
            generated = loaded.generate(
                **encoded,
                do_sample=False,
                num_beams=1,
                repetition_penalty=1.0,
                max_new_tokens=MAX_OUTPUT,
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id,
                stopping_criteria=StoppingCriteriaList([byte_ceiling]),
                use_cache=True,
            )
        generation_ns = time.monotonic_ns() - started
        tokens = generated[0, input_tokens:].cpu()
        output = tokenizer.decode(tokens, skip_special_tokens=True).encode("utf-8")
        terminal_eos = bool(len(tokens) and int(tokens[-1]) == tokenizer.eos_token_id)
        termination_reason = (
            "TERMINAL_EOS"
            if terminal_eos
            else "OUTPUT_BYTE_CEILING_EXCEEDED"
            if byte_ceiling.exceeded
            else "MAX_NEW_TOKENS_EXHAUSTED"
            if len(tokens) >= MAX_OUTPUT
            else "GENERATION_STOPPED_WITHOUT_EOS"
        )
        peak_rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
        fatal_resource_exceeded = (
            load_ns + generation_ns > MAX_WALL_NS or peak_rss > MAX_RSS
        )
        candidate_output_status = (
            "EXECUTION_ENVELOPE_PASS"
            if terminal_eos and len(tokens) <= MAX_OUTPUT and len(output) <= 6268
            else "EXECUTION_ENVELOPE_FAIL_CLOSED"
        )
        stem = f"{case_id}.{request_identity.removeprefix('sha256:')}"
        _write_new(Path("/tmp/output") / f"{stem}.raw", output)
        observation_core = {
            "schema": "pastila-production-core-frozen-runner-observation",
            "schema_version": 2,
            "qualification_generation_identity": os.environ[
                "QUALIFICATION_GENERATION_IDENTITY"
            ],
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
            "termination_reason": termination_reason,
            "candidate_output_status": candidate_output_status,
        }
        observation = {
            **observation_core,
            "observation_identity": _sha(
                json.dumps(
                    observation_core, ensure_ascii=False, separators=(",", ":")
                ).encode()
            ),
        }
        _write_new(
            Path("/tmp/output") / f"{stem}.observation.json",
            json.dumps(observation, ensure_ascii=False, separators=(",", ":")).encode(),
        )
        inference_complete_core = {
            "schema": "pastila-production-core-inference-lifecycle-event",
            "schema_version": 1,
            "phase": "COMPLETED",
            "sequence": sequence,
            "completed_count": sequence,
            "case_id": case_id,
            "request_identity": request_identity,
            "started_event_identity": inference_start["event_identity"],
            "generation_wall_ns": generation_ns,
            "output_tokens": len(tokens),
            "terminal_eos": terminal_eos,
            "termination_reason": termination_reason,
        }
        inference_complete = {
            **inference_complete_core,
            "event_identity": _sha(
                json.dumps(
                    inference_complete_core,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode()
            ),
        }
        _write_new(
            Path("/tmp/output") / f"inference-{sequence:03d}-completed.json",
            json.dumps(
                inference_complete, ensure_ascii=False, separators=(",", ":")
            ).encode(),
        )
        if fatal_resource_exceeded:
            raise SystemExit(
                "candidate resource envelope exceeded after durable capture"
            )
        _heartbeat("CASE_COMPLETE", sequence, sequence, case_id)
    _heartbeat("BATCH_COMPLETE", 201, 200)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
