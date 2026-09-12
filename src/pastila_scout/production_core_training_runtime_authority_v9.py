"""Fail-closed offline training authority for both Core V2 V9 successors."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

BRANCH = "successor/core-v2-v9-dual-structural-remediation"
SOURCE_COMMIT = "6da4edb718a27b14690ca8b0fd41b3597cb55524"
ROOTFS_SHA256 = "9c8a26024a36a808bf077be880a214fcb3308233354e1824ae7ebc82d931f826"
BASE_MODEL_SHA256 = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
CORPUS_SHA256 = "ecac8fe5b1c1069de2ff69614d210aa800b7838cdf8911d5b505747f515fddcd"
DEVELOPMENT_SHA256 = "9d276d4d49088ee52539a032874609de75d492027e2a6bfd70ec54da95f74059"
LAUNCHER_SHA256 = "3b40efea8398475e2aacdf0d7b1dd279542349b94f9f2c4c777871f49b3dd70f"
TRAINER_SHA256 = "6e24c93bcaf7a0d87e8e459ce6acb9028fe49b70a7b66e9180044bbb52d70d56"

CANDIDATES = {
    "pastila-editor-core-v1.1-json-successor-v9": {
        "predecessor_adapter_manifest_sha256": "0b3b8c317b8bfbf73dd4c131d92f1bc768d5e638034a49cecdc76da2d4e07f4b",
        "config_sha256": "3724c106dba7d7a9ed85fee9c0159e4c62c77a3ea2d5470991eaab80c73937fa",
        "training_config_identity": "78dd9da4c6e16494cf5b92e44cae10c0bf660b6398a3825574e412cab2df71cf",
        "smoke_receipt_identity": "9265e984f7a14207fc6d1e3c6c93d1395096fba4e1861f1c2133b96ea972a43a",
    },
    "pastila-editor-core-v1.2-json-successor-v9": {
        "predecessor_adapter_manifest_sha256": "dccfee343ad1e305a0e193501b3a8adba11da01afd3d890ee38275dda82ac719",
        "config_sha256": "0984f500efb9a0ccae0c89bf4c7f081a2e30c3be3439120021412dbdb05edf5f",
        "training_config_identity": "12e8390b5b2ad70dda32612eb8b805c34f3840a8f7a45d3b836f77b34b75a95c",
        "smoke_receipt_identity": "b23fc25fc815f6a0e8d3accd12a4b9b848fc8de80d5416094347de1bdc86a7d1",
    },
}


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
        "corpus_sha256": CORPUS_SHA256,
        "development_probe_sha256": DEVELOPMENT_SHA256,
        "launcher_sha256": LAUNCHER_SHA256,
        "trainer_sha256": TRAINER_SHA256,
        "candidates": CANDIDATES,
        "authority_mounts_read_only": True,
        "output_mount_writable_only": True,
        "host_path_fallback": False,
        "network_activity": False,
        "optimizer": "PAGED_ADAMW_8BIT",
        "smoke_lifecycle": {
            "mode": "SMOKE",
            "compile_load_triton": True,
            "backward_4bit": True,
            "optimizer_steps_per_candidate": 1,
            "save_reload": True,
        },
        "full_training_started": False,
        "post_training_gate_required": True,
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
        "retry_or_redraw": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }


def build_authority(observation: Mapping[str, object]) -> dict[str, object]:
    if dict(observation) != expected_observation():
        raise ValueError("V9 training authority observation mismatch")
    core = {
        "schema": "pastila-production-core-training-runtime-authority",
        "schema_version": 9,
        "status": "PASS_OFFLINE_DUAL_SUCCESSOR_TRAINING_RUNTIME_ZERO_QUALIFICATION_ATTEMPTS",
        "observation": dict(observation),
        "full_training_started": False,
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    return {**core, "training_runtime_authority_identity": identity(core)}
