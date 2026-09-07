"""Freeze the candidate-neutral comparative qualification generation; no inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import secrets
from pathlib import Path

from pastila_scout.production_core_candidate_qualification_v1 import (
    ADAPTER_MANIFESTS,
    BASE_MANIFEST_SHA256,
    CORPUS_IDENTITY,
    FREEZE_IDENTITY,
    HOLDOUT_IDENTITY,
    REGISTRY_IDENTITY,
    REPLACEMENT_AUTHORITY,
    ROOTFS_SHA256,
    RUBRIC_IDENTITY,
    TOKENIZER_SHA256,
    canonical_json_bytes,
    deterministic_schedule,
    identity,
    validate_secret_mapping,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs" / "artifacts"
RUNTIME = ROOT / ".pastila-runtime" / "production-core-qualification-v1"
SECRET = RUNTIME / "candidate-alias-secret-v1.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: object) -> None:
    path.write_bytes(json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n")


def _load(name: str) -> dict[str, object]:
    value = json.loads((ARTIFACTS / name).read_bytes())
    if not isinstance(value, dict):
        raise SystemExit(f"{name} is not an object")
    return value


def _secret(initialize: bool) -> dict[str, object]:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    if SECRET.exists():
        if SECRET.is_symlink():
            raise SystemExit("alias secret symlink rejected")
        value = json.loads(SECRET.read_bytes())
        if not isinstance(value, dict):
            raise SystemExit("alias secret invalid")
        return value
    if not initialize:
        raise SystemExit("alias secret absent; pass --initialize-secret exactly once")
    candidates = sorted(ADAPTER_MANIFESTS)
    if secrets.randbits(1):
        candidates.reverse()
    value = {
        "schema": "pastila-production-core-candidate-alias-secret",
        "schema_version": 1,
        "nonce_hex": secrets.token_hex(32),
        "aliases": {"CANDIDATE-A": candidates[0], "CANDIDATE-B": candidates[1]},
    }
    with SECRET.open("xb") as handle:
        handle.write(canonical_json_bytes(value))
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialize-secret", action="store_true")
    options = parser.parse_args()
    corpus = _load("production-core-qualification-corpus-v1.json")
    holdout = _load("production-core-qualification-holdout-v1.json")
    rubric = _load("production-core-qualification-rubric-v1.json")
    registry = _load("production-core-semantic-adjudicator-public-key-registry-v1.json")
    if (
        corpus.get("corpus_identity") != CORPUS_IDENTITY
        or holdout.get("holdout_identity") != HOLDOUT_IDENTITY
        or rubric.get("rubric_identity") != RUBRIC_IDENTITY
        or registry.get("registry_identity") != REGISTRY_IDENTITY
    ):
        raise SystemExit("published qualification authority mismatch")
    cases = corpus.get("cases")
    if not isinstance(cases, list):
        raise SystemExit("corpus cases absent")
    case_ids = [row["case_id"] for row in cases]
    secret = _secret(options.initialize_secret)
    commitment = hashlib.sha256(canonical_json_bytes(secret)).hexdigest()
    validate_secret_mapping(secret, commitment)
    schedule = deterministic_schedule(case_ids, secret, commitment)
    candidate_manifest_core = {
        "schema": "pastila-production-core-candidate-object-manifest",
        "schema_version": 1,
        "status": "PRE_EXECUTION_CONTENT_ADDRESSED_AUTHORITY",
        "base_model": {"manifest_sha256": BASE_MANIFEST_SHA256, "bytes": 27924394330, "files": 17},
        "tokenizer": {"object_sha256": TOKENIZER_SHA256, "fix_mistral_regex": True},
        "adapters": {
            candidate: {"manifest_sha256": digest, "bytes": 243884513, "files": 3}
            for candidate, digest in ADAPTER_MANIFESTS.items()
        },
        "system_prompts": {
            "pastila-editor-core-v1.1-experimental": "9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc",
            "pastila-editor-core-v1.2-experimental": "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17",
        },
        "rootfs_sha256": ROOTFS_SHA256,
        "object_resolution": "EXPLICIT_READ_ONLY_PATH_PLUS_COMPLETE_FLAT_FILE_MANIFEST",
        "absolute_paths_are_authority": False,
        "network": "DENY_ALL_NEW_CHILD_NAMESPACE",
        "candidate_execution_performed": False,
    }
    candidate_manifest = {**candidate_manifest_core, "manifest_identity": identity(candidate_manifest_core)}
    plan_core = {
        "schema": "pastila-production-core-comparative-qualification-generation",
        "schema_version": 1,
        "status": "FROZEN_BEFORE_FIRST_SEMANTIC_CANDIDATE_INFERENCE",
        "corpus_identity": CORPUS_IDENTITY,
        "holdout_identity": HOLDOUT_IDENTITY,
        "freeze_identity": FREEZE_IDENTITY,
        "rubric_identity": RUBRIC_IDENTITY,
        "adjudicator_registry_identity": REGISTRY_IDENTITY,
        "candidate_object_manifest_identity": candidate_manifest["manifest_identity"],
        "alias_secret_commitment": commitment,
        "alias_mapping_public": False,
        "replacement_authority": REPLACEMENT_AUTHORITY,
        "matrix": {"materializations": 2, "repetitions": 3, "cases": 200, "candidates": 2, "rows": 2400},
        "clean_materialization_authority": {
            "A": {"accepted_calibration_receipts": ["bcd03f8f63d278b80fabea4db24e55a5b7f65007a185cfcfea1398c20e78b069", "aeb3fd538b2c00c6b2acaa10ac94d912b6497140f6ead7c6f79d1c3ad01ed887"], "provenance_identity": "21782e3b5ed3a1643fcf376c1010e23a09f18986351a83115668908c5cf88cfc"},
            "B": {"accepted_calibration_receipts": ["30a3b8581ecc9c0cdfefbee66764959126023528d8d1bb95bd77bf781c4bcd4d", "46570ab41f247d782f1d7ac9c24ee0ae5332d56e28b5f18001b70f253f12995f"], "provenance_identity": "240a920deaae1127ab380b05238cd152dd63b9c36b60d6c9f21219e5be373f75"},
        },
        "schedule": schedule,
        "request_construction": "COMMON_STRUCTURED_QUALIFICATION_RESPONSE_V1_PROMPT",
        "limits": {"context_tokens": 8192, "input_tokens_max": 1924, "output_tokens_max": 6268, "wall_time_ns": 600000000000, "peak_rss_bytes": 16106127360},
        "runtime": {"rootfs_sha256": ROOTFS_SHA256, "network": "DENY_ALL_NEW_CHILD_NAMESPACE", "candidate_processes_concurrent": 1, "retry_or_redraw": False},
        "durable_outputs": ["raw", "observation", "execution_receipt", "network_boundary_log", "file_boundary_log", "blind_adjudication_packet"],
        "promotion_effect": False,
        "candidate_execution_performed": False,
    }
    plan = {**plan_core, "qualification_generation_identity": identity(plan_core)}
    source_paths = [
        "src/pastila_scout/production_core_candidate_qualification_v1.py",
        "src/pastila_scout/production_core_candidate_qualification_runner_v1.py",
        "scripts/run_production_core_candidate_qualification_v1.sh",
        "scripts/resolve_production_core_object_identity_v1.sh",
        "scripts/execute_production_core_candidate_qualification_v1.py",
        "scripts/materialize_production_core_candidate_qualification_v1.py",
        "tests/test_production_core_candidate_qualification_v1.py",
        "tests/fixtures/production_core_candidate_qualification_isolation_v1.sh",
        "tests/fixtures/production_core_candidate_qualification_watchdog_v1.sh",
        "tests/fixtures/production_core_candidate_qualification_terminal_v1.sh",
        "docs/production-core-candidate-qualification-v1.md",
    ]
    qualification_core = {
        "schema": "pastila-production-core-candidate-qualification-mechanism-qualification",
        "schema_version": 1,
        "status": "OFFLINE_PREINFERENCE_QUALIFIED",
        "candidate_manifest_identity": candidate_manifest["manifest_identity"],
        "qualification_generation_identity": plan["qualification_generation_identity"],
        "alias_secret_commitment": commitment,
        "source_sha256": {name: _sha(ROOT / name) for name in source_paths},
        "synthetic_only": True,
        "candidate_models_loaded_or_executed": False,
        "candidate_outputs_inspected": False,
        "network_activity": False,
        "promotion_effect": False,
    }
    qualification = {**qualification_core, "qualification_identity": identity(qualification_core)}
    _write(ARTIFACTS / "production-core-candidate-object-manifest-v1.json", candidate_manifest)
    _write(ARTIFACTS / "production-core-comparative-qualification-generation-v1.json", plan)
    _write(ARTIFACTS / "production-core-candidate-qualification-mechanism-v1.json", qualification)
    print(plan["qualification_generation_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
