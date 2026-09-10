"""Publish the verified successor training-runtime authority."""

from __future__ import annotations

import json
from pathlib import Path

from pastila_scout.production_core_training_runtime_authority_v1 import (
    LAUNCHER_SHA256,
    LIBCUDA_SHA256,
    PACKAGE_VERSIONS_SHA256,
    PTXAS_SHA256,
    ROOTFS_SHA256,
    SMOKE_IDENTITY,
    TOOLCHAIN_INVENTORY_SHA256,
    TRAINER_SHA256,
    build_authority,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-training-runtime-authority-v1.json"


def observation() -> dict[str, object]:
    return {
        "rootfs_materialization_sha256": {"A": ROOTFS_SHA256, "B": ROOTFS_SHA256},
        "rootfs_byte_identical": True,
        "launcher_sha256": LAUNCHER_SHA256,
        "trainer_sha256": TRAINER_SHA256,
        "package_versions_sha256": PACKAGE_VERSIONS_SHA256,
        "toolchain_inventory_sha256": TOOLCHAIN_INVENTORY_SHA256,
        "compiler": {
            "path": "/usr/bin/gcc",
            "version": "13.3.0",
            "inside_rootfs": True,
        },
        "python_headers_inside_rootfs": True,
        "cuda_headers_inside_rootfs": True,
        "ptxas_sha256": PTXAS_SHA256,
        "ptxas_version": "12.8.93",
        "libcuda_sha256": LIBCUDA_SHA256,
        "torch_version": "2.13.0+cu130",
        "torch_cuda_version": "13.0",
        "triton_version": "3.7.1",
        "bitsandbytes_version": "0.50.1",
        "transformers_version": "5.15.0",
        "peft_version": "0.20.0",
        "wsl_kernel_release": "6.18.33.2-microsoft-standard-WSL2",
        "gpu": {
            "name": "NVIDIA GeForce RTX 5080",
            "uuid": "GPU-f03193ae-ecc8-cc39-4b6a-69d4de60aa92",
            "compute_capability": "12.0",
            "driver_version": "610.47",
        },
        "toolchain_mount_read_only": True,
        "rootfs_mount_read_only": True,
        "model_mount_read_only": True,
        "predecessor_mount_read_only": True,
        "host_path_fallback": False,
        "network_activity": False,
        "smoke": {
            "compile_load_triton": True,
            "backward_4bit": True,
            "optimizer": "PAGED_ADAMW_8BIT",
            "optimizer_steps": 1,
            "save_reload": True,
            "receipt_identity": SMOKE_IDENTITY,
        },
        "qualification_attempt_consumed": False,
        "candidate_execution_performed": False,
        "promotion_effect": False,
    }


def main() -> int:
    value = build_authority(observation())
    OUTPUT.write_bytes(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        + b"\n"
    )
    print(value["training_runtime_authority_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
