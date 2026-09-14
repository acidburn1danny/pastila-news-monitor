"""Fail-closed optimized training authority for Core V10 successors."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from pastila_scout.production_core_training_runtime_authority_v10_1 import (
    BASE_MODEL_SHA256,
    BRANCH,
    CHECKPOINT_AUDIT_IDENTITY,
    CHECKPOINT_AUDIT_SHA256,
    EXECUTION_CONTRACT_IDENTITY,
    EXECUTION_CONTRACT_SHA256,
    ROOTFS_SHA256,
    RUNTIME_SMOKE_AUTHORITY_IDENTITY,
    RUNTIME_SMOKE_AUTHORITY_SHA256,
)

SOURCE_COMMIT = "89828ca769c8d13ba5196f0a157937720ab5b84b"
SOURCE_TREE = "5758f6597358a9e8c775bb2dfae7d0cd05727bac"
LAUNCHER_SHA256 = "69381e707890b052bebe98fd481f29cf318351f8ba8694cc512d9a502763170f"
TRAINER_SHA256 = "ffb5484d7f9d22a82b1933f4d8faab148391c3d88c948992c3a8b7e8f2afa402"
VALIDATOR_SHA256 = "f5407a3311b62459c09b6899426c5722c697081a3f497e9d2fe49a61c7d8a058"
PREDECESSOR_IDENTITY = "080717b853a959552f102f22db2dfdf1c8453921b310eec310d82a810e89b129"
PREDECESSOR_SHA256 = "94ba3f4426387c9f6208d7d2f1469f05f335448bfc7764fa67d7ae07f543bb01"
MANIFEST_IDENTITY = "f409dde31dd778c89d534eb94294fab115589388268048088e91f9d0c9500084"
MANIFEST_SHA256 = "aedc6e9a01e3170dd670d95432cee89c5b254418d5bcff6489534a7d03ecba9a"
PERFORMANCE_FREEZE_IDENTITY = "d418ac661108e44237d3be7bbbda8e0ae9b4d0a5a918d95a47594095d055cfff"
PERFORMANCE_FREEZE_SHA256 = "02d4413106261d7f197533c7a061288c6ca4fdab41288e4b6802cd925f4c71b8"
CANDIDATES = {
    "pastila-editor-core-v1.1-json-successor-v10": {
        "config_sha256": "be4f28f967bdc128094e06a3092f9be27ddbaf03ac5fdb270d2cfd036b3f10ae",
        "training_config_identity": "1d7587ae93158c644a56e8f64d51e862a09b2060864def619b9814835b1049a7",
    },
    "pastila-editor-core-v1.2-json-successor-v10": {
        "config_sha256": "f7c2cd9bbadea3fd845c49456c95a6ca6e420d34d868113e4df6d4729216527c",
        "training_config_identity": "b89d91261657f8ac7f26ed77b24fdb62266c99bbfce7f410ede38ece37334d87",
    },
}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()


def expected_observation() -> dict[str, object]:
    return {
        "branch": BRANCH,
        "source_commit": SOURCE_COMMIT,
        "source_tree": SOURCE_TREE,
        "predecessor_training_authority_identity": PREDECESSOR_IDENTITY,
        "predecessor_training_authority_sha256": PREDECESSOR_SHA256,
        "rootfs_materialization_sha256": {"D": ROOTFS_SHA256, "E": ROOTFS_SHA256},
        "rootfs_byte_identical": True,
        "base_model_manifest_sha256": BASE_MODEL_SHA256,
        "execution_contract_identity": EXECUTION_CONTRACT_IDENTITY,
        "execution_contract_sha256": EXECUTION_CONTRACT_SHA256,
        "corpus_manifest_identity": MANIFEST_IDENTITY,
        "corpus_manifest_sha256": MANIFEST_SHA256,
        "performance_freeze_identity": PERFORMANCE_FREEZE_IDENTITY,
        "performance_freeze_sha256": PERFORMANCE_FREEZE_SHA256,
        "training_execution_profile": "BF16_FLASH_REPEAT_KV_SELECTIVE_LOGITS",
        "trainer_sha256": TRAINER_SHA256,
        "launcher_sha256": LAUNCHER_SHA256,
        "training_input_validator_sha256": VALIDATOR_SHA256,
        "candidates": CANDIDATES,
        "runtime_smoke_authority_identity": RUNTIME_SMOKE_AUTHORITY_IDENTITY,
        "runtime_smoke_authority_sha256": RUNTIME_SMOKE_AUTHORITY_SHA256,
        "checkpoint_resume_audit_identity": CHECKPOINT_AUDIT_IDENTITY,
        "checkpoint_resume_audit_sha256": CHECKPOINT_AUDIT_SHA256,
        "checkpoint_frequency": "EVERY_OPTIMIZER_STEP",
        "optimizer": "PAGED_ADAMW_8BIT",
        "host_path_fallback": False,
        "network_activity": False,
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }


def build_authority(observation: Mapping[str, object]) -> dict[str, object]:
    if dict(observation) != expected_observation():
        raise ValueError("V10.2 training authority observation mismatch")
    core = {
        "schema": "pastila-production-core-training-runtime-authority",
        "schema_version": "10.2",
        "status": "PASS_OPTIMIZED_DUAL_SUCCESSOR_V10_TRAINING_RUNTIME_ZERO_QUALIFICATION_ATTEMPTS",
        "observation": dict(observation),
        "full_training_authorized": True,
        "full_training_started": False,
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    return {**core, "training_runtime_authority_identity": hashlib.sha256(canonical(core)).hexdigest()}
