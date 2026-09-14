"""Fail-closed checkpoint/resume training authority for Core V10 successors."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

from pastila_scout.production_core_training_runtime_authority_v10 import (
    BASE_MODEL_SHA256,
    BRANCH,
    CANDIDATES,
    CORPUS_MANIFEST_IDENTITY,
    CORPUS_MANIFEST_SHA256,
    EXECUTION_CONTRACT_IDENTITY,
    EXECUTION_CONTRACT_SHA256,
    ROOTFS_SHA256,
    RUNTIME_SMOKE_AUTHORITY_IDENTITY,
    RUNTIME_SMOKE_AUTHORITY_SHA256,
    TOKEN_AUDIT_RECEIPT_IDENTITY,
    TOKEN_AUDIT_RECEIPT_SHA256,
    TOKEN_MATERIALIZATION_EVIDENCE_IDENTITY,
    TOKEN_MATERIALIZATION_EVIDENCE_SHA256,
    TRAINING_INPUT_VALIDATOR_SHA256,
)

SOURCE_COMMIT = "fe46c5ef9806a83c14cb4a4598525eedb044c4ec"
SOURCE_TREE = "9f47ea9e08979bdecc4294a2411bd01f79bdef94"
LAUNCHER_SHA256 = "69381e707890b052bebe98fd481f29cf318351f8ba8694cc512d9a502763170f"
TRAINER_SHA256 = "aaafcf3794e335e6757b9ee23a1cc21b5e9e6bc6e33cf055de0e2c2963252669"
PREDECESSOR_AUTHORITY_IDENTITY = "2b791ce874604dd1ce571bcb933ba3912987f9b890a99beb55a00f2c167fd635"
PREDECESSOR_AUTHORITY_SHA256 = "a5cb5a1add20f6b99ac841b75d9e4232e0045f6ce3a67e116f153c6dfbf52261"
CHECKPOINT_AUDIT_IDENTITY = "914730733543eecbfebc869959397356161c2f892d2178f1327459f043e47377"
CHECKPOINT_AUDIT_SHA256 = "e30bb1b81b47bfcd7adfd5aaaf6e40fab7de8e9b79914c7c459149d5bd441884"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()


def identity(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def expected_observation() -> dict[str, object]:
    return {
        "branch": BRANCH,
        "source_commit": SOURCE_COMMIT,
        "source_tree": SOURCE_TREE,
        "predecessor_training_authority_identity": PREDECESSOR_AUTHORITY_IDENTITY,
        "predecessor_training_authority_sha256": PREDECESSOR_AUTHORITY_SHA256,
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
        "checkpoint_resume_audit_identity": CHECKPOINT_AUDIT_IDENTITY,
        "checkpoint_resume_audit_sha256": CHECKPOINT_AUDIT_SHA256,
        "checkpoint_semantics": {
            "frequency": "EVERY_OPTIMIZER_STEP",
            "atomic_publish": True,
            "content_addressed_closure": True,
            "accepted_optimizer_steps_recomputed": False,
            "incomplete_current_batch_may_recompute": True,
            "progress_observability": "PER_MICROSTEP_AND_OPTIMIZER_STEP",
            "save_restart_resume_byte_exact": True,
        },
        "smoke_lifecycle": {
            "compile_load_triton": True,
            "backward_4bit": True,
            "optimizer": "PAGED_ADAMW_8BIT",
            "optimizer_step": True,
            "save_reload": True,
            "save_restart_resume": True,
        },
        "authority_mounts_read_only": True,
        "output_mount_writable_only": True,
        "host_path_fallback": False,
        "network_activity": False,
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }


def build_authority(observation: Mapping[str, object]) -> dict[str, object]:
    if dict(observation) != expected_observation():
        raise ValueError("V10.1 training authority observation mismatch")
    core = {
        "schema": "pastila-production-core-training-runtime-authority",
        "schema_version": "10.1",
        "status": "PASS_CHECKPOINT_RESUME_DUAL_SUCCESSOR_V10_TRAINING_RUNTIME_ZERO_QUALIFICATION_ATTEMPTS",
        "observation": dict(observation),
        "full_training_authorized": True,
        "full_training_started": False,
        "candidate_execution_performed": False,
        "qualification_attempt_consumed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    return {**core, "training_runtime_authority_identity": identity(core)}
