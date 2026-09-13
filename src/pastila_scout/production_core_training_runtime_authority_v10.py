"""Fail-closed offline training authority for both Core V10 successors."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

BRANCH = "successor/core-v2-v10-unified-execution-contract"
SOURCE_COMMIT = "5416e3e69f790e96d47cf6942cf5bc8353893b2b"
ROOTFS_SHA256 = "9c8a26024a36a808bf077be880a214fcb3308233354e1824ae7ebc82d931f826"
BASE_MODEL_SHA256 = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
EXECUTION_CONTRACT_IDENTITY = "cb580100302d3b6c462417a2c2d4ef0cb78f0bfc149470710f76a569e70b8562"
EXECUTION_CONTRACT_SHA256 = "eb2ab0914175f0f9ae50882c4c96fbc792cfee1fe40fa39740b9ef8f58a1825d"
CORPUS_MANIFEST_IDENTITY = "817992aa93274b8076f7f54825c9fe038290849a6eb44dc90d40f09dfdd86f0f"
CORPUS_MANIFEST_SHA256 = "17e77e4c2b4c78a7b7165739630d7f81217b18da26abacd1aa7f2694d7551484"
TOKEN_AUDIT_RECEIPT_IDENTITY = "a34755fa318567856e77fe8b81b6b8ed66bcf7d906615723291c7c7722fb53a5"
TOKEN_AUDIT_RECEIPT_SHA256 = "e688204d39502514d9cd1e7392c3dc365b8edeca6bdab1cbdb1b5747da9efe4c"
TOKEN_MATERIALIZATION_EVIDENCE_IDENTITY = "116022580ec74b8d4a1c0f165652611827496d6cce3d0d4a4a37c28156dac858"
TOKEN_MATERIALIZATION_EVIDENCE_SHA256 = "34bbb4e09c13904b7cb14468265e8b0cbc50be4820f13bf06794bae5a51bc931"
TRAINING_INPUT_VALIDATOR_SHA256 = "45a84581eb78d254f431d64c748e7d113bd8b2b966f8ee52377136cb207f33ea"
LAUNCHER_SHA256 = "3b40efea8398475e2aacdf0d7b1dd279542349b94f9f2c4c777871f49b3dd70f"
TRAINER_SHA256 = "6e24c93bcaf7a0d87e8e459ce6acb9028fe49b70a7b66e9180044bbb52d70d56"
RUNTIME_SMOKE_AUTHORITY_IDENTITY = "6877f7596d0cafc9518681147f6880b7630bed6f7e23fc88a0d43aab15a2ed23"
RUNTIME_SMOKE_AUTHORITY_SHA256 = "2ba9296be11ad129b7fef010537c162e24d3c09d2722a7cde8788b6a0df7c3ed"

CANDIDATES = {
    "pastila-editor-core-v1.1-json-successor-v10": {
        "predecessor_adapter_manifest_sha256": "ac58e53492c58f635defad01009769e948819f10733c1473ea11ecf8df29107c",
        "training_corpus_sha256": "12ce4c7aeb257e9d5c1a92dd8c5d75d1e998819ecd19eddafa0e42cab83072f1",
        "shadow_corpus_sha256": "e0adbfdaf7df1ac7365692c4ceae90bee62b5c07349521ec333f721c668304f3",
        "config_sha256": "acd290dd26aade2fde98af4e9b21499bdd50c5aecb16352c3da37112b25f0a40",
        "training_config_identity": "abd5e31beaba215e9d32850a8693905beefec4b6ba45d2d977d2f0533a2495b5",
        "validated_rows": 480,
    },
    "pastila-editor-core-v1.2-json-successor-v10": {
        "predecessor_adapter_manifest_sha256": "a8c0f6778f6d218cfdec47b53f87eb8dfc4af2c55077f559983e4331876b3ab8",
        "training_corpus_sha256": "5491630f3b959f890a74cce3075a9a2e976304138e342c379d4e5fd6a0a9641c",
        "shadow_corpus_sha256": "74d79f07c2f8bc7b0182e255e2119d7c15d9e4f4642f99adef7654d9cd7754ce",
        "config_sha256": "c958ac6fbcecc0af7b4f652a7acf1e3073ed0a5aba97fb6abc3903039846e32f",
        "training_config_identity": "3abe6dc3e13f04686dbe86f546ae458407fce9e3eda3eef9b5ecb5b2de142699",
        "validated_rows": 480,
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
        "execution_contract_identity": EXECUTION_CONTRACT_IDENTITY,
        "execution_contract_sha256": EXECUTION_CONTRACT_SHA256,
        "corpus_manifest_identity": CORPUS_MANIFEST_IDENTITY,
        "corpus_manifest_sha256": CORPUS_MANIFEST_SHA256,
        "token_audit_receipt_identity": TOKEN_AUDIT_RECEIPT_IDENTITY,
        "token_audit_receipt_sha256": TOKEN_AUDIT_RECEIPT_SHA256,
        "token_materialization_evidence_identity": TOKEN_MATERIALIZATION_EVIDENCE_IDENTITY,
        "token_materialization_evidence_sha256": TOKEN_MATERIALIZATION_EVIDENCE_SHA256,
        "training_input_validator_sha256": TRAINING_INPUT_VALIDATOR_SHA256,
        "launcher_sha256": LAUNCHER_SHA256,
        "trainer_sha256": TRAINER_SHA256,
        "candidates": CANDIDATES,
        "maximum_training_sequence_tokens": 3072,
        "training_input_validation": "PASS_960_OF_960_ZERO_MODEL",
        "runtime_smoke_authority_identity": RUNTIME_SMOKE_AUTHORITY_IDENTITY,
        "runtime_smoke_authority_sha256": RUNTIME_SMOKE_AUTHORITY_SHA256,
        "runtime_smoke_scope": "UNCHANGED_ROOTFS_LAUNCHER_TRAINER_TOOLCHAIN_ONLY",
        "smoke_lifecycle": {
            "compile_load_triton": True,
            "backward_4bit": True,
            "optimizer": "PAGED_ADAMW_8BIT",
            "optimizer_step": True,
            "save_reload": True,
        },
        "authority_mounts_read_only": True,
        "output_mount_writable_only": True,
        "host_path_fallback": False,
        "network_activity": False,
        "full_training_started": False,
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }


def build_authority(observation: Mapping[str, object]) -> dict[str, object]:
    if dict(observation) != expected_observation():
        raise ValueError("V10 training authority observation mismatch")
    core = {
        "schema": "pastila-production-core-training-runtime-authority",
        "schema_version": 10,
        "status": "PASS_OFFLINE_DUAL_SUCCESSOR_V10_TRAINING_RUNTIME_ZERO_QUALIFICATION_ATTEMPTS",
        "observation": dict(observation),
        "full_training_authorized": False,
        "full_training_started": False,
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    return {**core, "training_runtime_authority_identity": identity(core)}
