"""Import-only probe for the candidate-neutral Production Core runtime."""

from __future__ import annotations

import json
import os
import platform

import accelerate
import bitsandbytes
import safetensors
import tokenizers
import torch
import transformers


def runtime_probe() -> dict[str, object]:
    cuda_available = torch.cuda.is_available()
    cuda_device_count = torch.cuda.device_count()
    if not cuda_available or cuda_device_count != 1:
        raise RuntimeError("qualification profile requires exactly one CUDA device")
    capability = torch.cuda.get_device_capability(0)
    properties = torch.cuda.get_device_properties(0)
    if capability < (12, 0) or not torch.cuda.is_bf16_supported():
        raise RuntimeError("CUDA qualification capability mismatch")
    torch.use_deterministic_algorithms(True)
    return {
        "schema": "pastila-production-core-runtime-probe",
        "schema_version": 1,
        "candidate_model_loaded": False,
        "candidate_result_inspected": False,
        "network_namespace": os.readlink("/proc/self/ns/net"),
        "platform": {"machine": platform.machine(), "system": platform.system()},
        "accelerator": {
            "bf16_supported": torch.cuda.is_bf16_supported(),
            "compute_capability": list(capability),
            "device_count": cuda_device_count,
            "deterministic_algorithms_enabled": torch.are_deterministic_algorithms_enabled(),
            "total_memory_bytes": properties.total_memory,
        },
        "packages": {
            "accelerate": accelerate.__version__,
            "bitsandbytes": bitsandbytes.__version__,
            "safetensors": safetensors.__version__,
            "tokenizers": tokenizers.__version__,
            "torch": torch.__version__,
            "torch_cuda": torch.version.cuda,
            "transformers": transformers.__version__,
        },
    }


if __name__ == "__main__":
    print(json.dumps(runtime_probe(), sort_keys=True, separators=(",", ":")))
