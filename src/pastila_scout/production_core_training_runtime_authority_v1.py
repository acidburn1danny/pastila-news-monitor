"""Closed authority for the Core V2 successor offline training runtime."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

ROOTFS_SHA256 = "9c8a26024a36a808bf077be880a214fcb3308233354e1824ae7ebc82d931f826"
PACKAGE_VERSIONS_SHA256 = (
    "8cb0c7cdf025b69f7bfd981ca5245776022213c587b22bd6a731d8cea7da85ee"
)
TOOLCHAIN_INVENTORY_SHA256 = (
    "1e46c8017fb94632a46f1207d15a8e0014a3bf236268b95d75b1bb3b3f890d17"
)
PTXAS_SHA256 = "c960a4f238b17d5c5d3c01ad2bbc1ebd2c5aecc459cb4d223bff10b45f9b8fca"
LIBCUDA_SHA256 = "158e0c4e9427a5fbc34ebe07000505744adf115f3baf857dae87dcf1f0674732"
SMOKE_IDENTITY = "eb477ab35ec2a16820a47ee2d7f3afbfe53e4f419b26801c888be91fe9de2716"
LAUNCHER_SHA256 = "3b40efea8398475e2aacdf0d7b1dd279542349b94f9f2c4c777871f49b3dd70f"
TRAINER_SHA256 = "85c118439c6c31257972b66e0180e81eb538210346d1e316009461ca75a9ed55"


def canonical(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def validate_observation(value: Mapping[str, object]) -> None:
    expected = {
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
    if value != expected:
        raise ValueError("training runtime observation mismatch")


def build_authority(observation: Mapping[str, object]) -> dict[str, object]:
    validate_observation(observation)
    core = {
        "schema": "pastila-production-core-training-runtime-authority",
        "schema_version": 1,
        "status": "PASS_OFFLINE_TRAINING_RUNTIME_ZERO_QUALIFICATION_ATTEMPTS",
        "observation": dict(observation),
        "qualification_attempt_consumed": False,
        "candidate_execution_performed": False,
        "promotion_effect": False,
    }
    return {**core, "training_runtime_authority_identity": identity(core)}
