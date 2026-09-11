"""Fail-closed training-runtime authority for the Core V2 V1.1 EOS successor."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

BRANCH = "successor/core-v2-v1-1-eos-remediation-v5"
SOURCE_COMMIT = "a140a612a7c80131064d2e44323345c5985ca613"
ROOTFS_SHA256 = "9c8a26024a36a808bf077be880a214fcb3308233354e1824ae7ebc82d931f826"
BASE_MODEL_SHA256 = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
PREDECESSOR_SHA256 = "16d6384355abfeff9a2c35cfa9866c604f8fd9703c19dcfbefcfdbb7fdb7dcf3"
CORPUS_SHA256 = "d87018809fde41a2bf23e0a98395d0258b757b683e2fdf11e678cf933dadbed5"
DEVELOPMENT_SHA256 = "58590d6c63e71dd32149de73f77daf949c69183ee35fdb733d85b2915e5f3511"
CONFIG_SHA256 = "0616d633d568326fdd5e85db87a4f430e773cb1cc1cd5ac5ce35e87ac0d927ac"
LAUNCHER_SHA256 = "3b40efea8398475e2aacdf0d7b1dd279542349b94f9f2c4c777871f49b3dd70f"
TRAINER_SHA256 = "b14feac0c425bba82420ae375d47ac00eee91acc6537716463cb12c7f1b52286"
SMOKE_RECEIPT_IDENTITY = "c15981119778c4a89af4d3cd7a12cb258187a42893b7e6dea2af7bed8be0879a"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def expected_observation() -> dict[str, object]:
    return {
        "branch": BRANCH,
        "source_commit": SOURCE_COMMIT,
        "rootfs_materialization_sha256": {"D": ROOTFS_SHA256, "E": ROOTFS_SHA256},
        "rootfs_byte_identical": True,
        "base_model_manifest_sha256": BASE_MODEL_SHA256,
        "predecessor_adapter_manifest_sha256": PREDECESSOR_SHA256,
        "corpus_sha256": CORPUS_SHA256,
        "development_probe_sha256": DEVELOPMENT_SHA256,
        "config_sha256": CONFIG_SHA256,
        "launcher_sha256": LAUNCHER_SHA256,
        "trainer_sha256": TRAINER_SHA256,
        "authority_mounts_read_only": True,
        "output_mount_writable_only": True,
        "host_path_fallback": False,
        "network_activity": False,
        "optimizer": "PAGED_ADAMW_8BIT",
        "smoke": {
            "mode": "SMOKE",
            "compile_load_triton": True,
            "backward_4bit": True,
            "optimizer_steps": 1,
            "save_reload": True,
            "receipt_identity": SMOKE_RECEIPT_IDENTITY,
        },
        "post_training_gate_required": True,
        "full_training_started": False,
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
        "retry_or_redraw": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }


def build_authority(observation: Mapping[str, object]) -> dict[str, object]:
    if dict(observation) != expected_observation():
        raise ValueError("V5 training authority observation mismatch")
    core = {
        "schema": "pastila-production-core-training-runtime-authority",
        "schema_version": 5,
        "status": "PASS_OFFLINE_V1_1_EOS_TRAINING_RUNTIME_ZERO_QUALIFICATION_ATTEMPTS",
        "observation": dict(observation),
        "full_training_started": False,
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    return {**core, "training_runtime_authority_identity": identity(core)}
