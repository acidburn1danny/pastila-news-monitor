"""Materialize the candidate-neutral Semantic Successor V2 generation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import stat
from pathlib import Path

from pastila_scout.production_core_candidate_qualification_generation_v2 import (
    ADAPTER_MANIFESTS,
    ASSERTIONS_IDENTITY,
    BASE_MANIFEST_SHA256,
    CORPUS_IDENTITY,
    FRAMEWORK_IDENTITY,
    HOLDOUT_IDENTITY,
    PROFILE_IDENTITY,
    PUBLIC_AUTHORITY_COMMIT,
    PUBLIC_AUTHORITY_REF,
    PUBLIC_AUTHORITY_TREE,
    REGISTRY_IDENTITY,
    RESPONSE_CONTRACT_IDENTITY,
    ROOTFS_SHA256,
    RUBRIC_IDENTITY,
    SEMANTIC_CONTRACT_IDENTITY,
    TOKENIZER_SHA256,
    UNICODE_AUTHORITY_IDENTITY,
    canonical,
    deterministic_schedule,
    identity,
    materialize_request_authorities,
    validate_generation,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"


def _load(name: str) -> dict[str, object]:
    value = json.loads((ART / name).read_bytes())
    if not isinstance(value, dict):
        raise SystemExit(f"{name}: object required")
    return value


def _write(name: str, value: object) -> None:
    (ART / name).write_bytes(
        json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _secret(supplied_root: Path, initialize: bool) -> dict[str, object]:
    repository = ROOT.resolve(strict=True)
    candidate = supplied_root if supplied_root.is_absolute() else ROOT / supplied_root
    absolute = candidate.absolute()
    if not absolute.is_relative_to(repository):
        raise SystemExit("secret root containment mismatch")
    relative = absolute.relative_to(repository)
    cursor = repository
    for component in relative.parts:
        cursor = cursor / component
        if cursor.exists() and (
            cursor.is_symlink()
            or not cursor.resolve(strict=True).is_relative_to(repository)
        ):
            raise SystemExit("secret parent symlink rejected")
    absolute.mkdir(parents=True, exist_ok=True)
    root = absolute.resolve(strict=True)
    secret_path = root / "candidate-alias-secret-v2.json"
    if secret_path.exists():
        if secret_path.is_symlink():
            raise SystemExit("secret symlink rejected")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(secret_path, flags)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                raise SystemExit("secret is not regular")
            chunks = []
            while chunk := os.read(descriptor, 4096):
                chunks.append(chunk)
        finally:
            os.close(descriptor)
        return json.loads(b"".join(chunks))
    if not initialize:
        raise SystemExit("secret absent")
    candidates = sorted(ADAPTER_MANIFESTS)
    if secrets.randbits(1):
        candidates.reverse()
    value = {
        "schema": "pastila-production-core-candidate-alias-secret",
        "schema_version": 1,
        "nonce_hex": secrets.token_hex(32),
        "aliases": {"CANDIDATE-A": candidates[0], "CANDIDATE-B": candidates[1]},
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    descriptor = os.open(secret_path, flags, 0o600)
    try:
        os.write(descriptor, canonical(value))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return value


def _sealed(core: dict[str, object], field: str) -> dict[str, object]:
    return {**core, field: identity(core)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialize-secret", action="store_true")
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--secret-root", type=Path, required=True)
    args = parser.parse_args()
    old = _load("production-core-qualification-corpus-v1.json")
    corpus = _load("production-core-qualification-corpus-v2.json")
    requests = materialize_request_authorities(old, corpus)
    request_core = {
        "schema": "pastila-production-core-candidate-request-manifest",
        "schema_version": 2,
        "status": "EXACT_CANDIDATE_VISIBLE_REQUEST_BYTES_PREINFERENCE",
        "public_authority_commit": PUBLIC_AUTHORITY_COMMIT,
        "corpus_identity": CORPUS_IDENTITY,
        "semantic_contract_identity": SEMANTIC_CONTRACT_IDENTITY,
        "structured_response_contract_identity": RESPONSE_CONTRACT_IDENTITY,
        "request_count": 200,
        "requests": requests,
        "candidate_execution_performed": False,
    }
    request_manifest = _sealed(request_core, "request_manifest_identity")
    candidate_core = {
        "schema": "pastila-production-core-candidate-object-manifest",
        "schema_version": 2,
        "status": "UNCHANGED_TECHNICAL_OBJECT_AUTHORITY_NO_EXECUTION",
        "base_model_manifest_sha256": BASE_MANIFEST_SHA256,
        "tokenizer_sha256": TOKENIZER_SHA256,
        "tokenizer_fix_mistral_regex": True,
        "adapter_manifest_sha256": ADAPTER_MANIFESTS,
        "rootfs_sha256": ROOTFS_SHA256,
        "candidate_execution_performed": False,
    }
    candidate_manifest = _sealed(candidate_core, "manifest_identity")
    _write("production-core-candidate-request-manifest-v2.json", request_manifest)
    _write("production-core-candidate-object-manifest-v2.json", candidate_manifest)
    if not args.freeze:
        print(request_manifest["request_manifest_identity"])
        return 0
    receipt_a = _load("production-core-candidate-input-envelope-a-v2.json")
    receipt_b = _load("production-core-candidate-input-envelope-b-v2.json")
    for label, receipt in (("A", receipt_a), ("B", receipt_b)):
        if (
            receipt.get("materialization") != label
            or receipt.get("request_manifest_identity")
            != request_manifest["request_manifest_identity"]
            or receipt.get("status") != "PASS_ALL_RENDERINGS_WITHIN_1924_TOKENS"
            or receipt.get("candidate_execution_performed") is not False
        ):
            raise SystemExit("input-envelope receipt mismatch")
        core = dict(receipt)
        recorded = core.pop("receipt_identity", None)
        if recorded != identity(core):
            raise SystemExit("input-envelope receipt identity mismatch")
    secret = _secret(args.secret_root, args.initialize_secret)
    commitment = hashlib.sha256(canonical(secret)).hexdigest()
    schedule = deterministic_schedule(
        [str(row["case_id"]) for row in requests], secret, commitment
    )
    bindings = {
        "public_ref": PUBLIC_AUTHORITY_REF,
        "public_commit": PUBLIC_AUTHORITY_COMMIT,
        "public_tree": PUBLIC_AUTHORITY_TREE,
        "unicode_authority_identity": UNICODE_AUTHORITY_IDENTITY,
        "semantic_contract_identity": SEMANTIC_CONTRACT_IDENTITY,
        "structured_response_contract_identity": RESPONSE_CONTRACT_IDENTITY,
        "corpus_identity": CORPUS_IDENTITY,
        "assertion_manifest_identity": ASSERTIONS_IDENTITY,
        "rubric_identity": RUBRIC_IDENTITY,
        "execution_profile_identity": PROFILE_IDENTITY,
        "framework_identity": FRAMEWORK_IDENTITY,
        "holdout_identity": HOLDOUT_IDENTITY,
        "adjudicator_registry_identity": REGISTRY_IDENTITY,
    }
    generation_core = {
        "schema": "pastila-production-core-comparative-qualification-generation",
        "schema_version": 2,
        "status": "FROZEN_PREINFERENCE_CANDIDATE_NEUTRAL",
        "authority_bindings": bindings,
        "request_manifest_identity": request_manifest["request_manifest_identity"],
        "candidate_object_manifest_identity": candidate_manifest["manifest_identity"],
        "input_envelope_receipt_identities": {
            "A": receipt_a["receipt_identity"],
            "B": receipt_b["receipt_identity"],
        },
        "alias_secret_commitment": commitment,
        "alias_mapping_public": False,
        "matrix": {
            "materializations": 2,
            "repetitions": 3,
            "cases": 200,
            "candidates": 2,
            "rows": 2400,
        },
        "schedule": schedule,
        "retry_or_redraw_authorized": False,
        "candidate_execution_performed": False,
        "promotion_effect": False,
    }
    generation = _sealed(generation_core, "qualification_generation_identity")
    validate_generation(
        generation,
        request_manifest,
        candidate_manifest,
        {"A": receipt_a, "B": receipt_b},
        old,
        corpus,
        secret,
    )
    qualification_core = {
        "schema": "pastila-production-core-candidate-generation-qualification",
        "schema_version": 2,
        "status": "PASS_OFFLINE_PREINFERENCE_ZERO_CANDIDATE_EXECUTION",
        "qualification_generation_identity": generation[
            "qualification_generation_identity"
        ],
        "request_manifest_identity": request_manifest["request_manifest_identity"],
        "candidate_object_manifest_identity": candidate_manifest["manifest_identity"],
        "input_envelope_receipt_identities": generation[
            "input_envelope_receipt_identities"
        ],
        "candidate_visible_mapping": "COMPLETE_1_TO_1",
        "request_count": 200,
        "rendering_count": 400,
        "candidate_neutral": True,
        "mechanism_source_sha256": {
            path: _sha(ROOT / path)
            for path in (
                "src/pastila_scout/production_core_semantic_authority_v2.py",
                "src/pastila_scout/production_core_candidate_qualification_generation_v2.py",
                "scripts/materialize_production_core_candidate_qualification_v2.py",
                "scripts/probe_production_core_candidate_prompt_input_envelope_v2.py",
                "scripts/probe_production_core_candidate_prompt_input_envelope_v2.sh",
                "tests/test_production_core_candidate_qualification_generation_v2.py",
            )
        },
        "candidate_execution_performed": False,
        "network_activity": False,
        "promotion_effect": False,
    }
    qualification = _sealed(qualification_core, "qualification_identity")
    _write("production-core-comparative-qualification-generation-v2.json", generation)
    _write("production-core-candidate-generation-qualification-v2.json", qualification)
    print(generation["qualification_generation_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
