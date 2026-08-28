"""Canonical authority and environment contracts for a load-only V1.5 attempt."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


AUTHORITY_CONTRACT_IDENTITY = "0aa5e785b3c06fc8acab6692da5088d74fc8649b71e16a2eaa9f2b29ca04d58b"
POLICY_GATE_IDENTITY = "9410ef484986fc14534334ebf6a6912d381e2882b8fca948de4b215b2e7a8931"
PACKAGE_IDENTITIES = (
    "transformers==5.15.0", "torch==2.13.0+cu130", "peft==0.20.0",
    "accelerate==1.14.0", "bitsandbytes==0.50.1",
)


@dataclass(frozen=True, slots=True)
class LoadOnlyAuthorityV1:
    load_candidate_identity: str
    owner_authority_identity: str
    required_free_vram_mib: int
    attempt_ceiling: int
    operation: str
    generation_authorized: bool
    retry_authorized: bool
    fallback_authorized: bool
    authority_receipt_identity: str


@dataclass(frozen=True, slots=True)
class PreloadEnvironmentV1:
    package_identities: tuple[str, ...]
    gpu_name: str
    vram_total_mib: int
    vram_free_mib: int
    compute_capability: str
    cuda_device: int
    immutable_manifest_identity: str
    base_manifest_sha256: str
    adapter_manifest_sha256: str
    manifests_verified: bool
    model_declared_transformers_version: str
    runtime_transformers_version: str
    compatibility_pair_explicitly_accepted: bool


def parse_load_only_authority_v1(
    *, raw_receipt: bytes, expected_load_candidate_identity: str,
) -> LoadOnlyAuthorityV1:
    value = _object(raw_receipt, "AUTHORITY_RECEIPT")
    required = {
        "schema_name", "schema_version", "authority_contract_identity",
        "policy_gate_identity", "load_candidate_identity",
        "owner_authority_identity", "required_free_vram_mib", "attempt_ceiling",
        "operation", "generation_authorized", "retry_authorized",
        "fallback_authorized", "authority_receipt_identity",
    }
    if set(value) != required:
        raise ValueError("MODEL_LOAD_AUTHORITY_RECEIPT_SHAPE_MISMATCH")
    fixed = (
        value["schema_name"], value["schema_version"],
        value["authority_contract_identity"], value["policy_gate_identity"],
        value["load_candidate_identity"], value["attempt_ceiling"],
        value["operation"], value["generation_authorized"],
        value["retry_authorized"], value["fallback_authorized"],
    )
    expected = (
        "pastila-semantic-admission-v2-construction-obligation-v2-model-load-authority",
        "1.0.0", AUTHORITY_CONTRACT_IDENTITY, POLICY_GATE_IDENTITY,
        expected_load_candidate_identity, 1, "LOAD_ONLY", False, False, False,
    )
    if fixed != expected or type(value["owner_authority_identity"]) is not str or not value["owner_authority_identity"]:
        raise ValueError("MODEL_LOAD_AUTHORITY_RECEIPT_POLICY_MISMATCH")
    if type(value["required_free_vram_mib"]) is not int or value["required_free_vram_mib"] <= 0:
        raise ValueError("MODEL_LOAD_AUTHORITY_CAPACITY_INVALID")
    identity = hashlib.sha256(_canonical({k: v for k, v in value.items()
                                          if k != "authority_receipt_identity"})).hexdigest()
    if value["authority_receipt_identity"] != identity or raw_receipt != _canonical(value):
        raise ValueError("MODEL_LOAD_AUTHORITY_RECEIPT_SEAL_MISMATCH")
    return LoadOnlyAuthorityV1(
        value["load_candidate_identity"], value["owner_authority_identity"],
        value["required_free_vram_mib"], 1, "LOAD_ONLY", False, False, False,
        identity,
    )


def validate_preload_environment_v1(
    *, observed: PreloadEnvironmentV1, authority: LoadOnlyAuthorityV1,
) -> None:
    if type(observed) is not PreloadEnvironmentV1 or type(authority) is not LoadOnlyAuthorityV1:
        raise TypeError("MODEL_LOAD_PRELOAD_EXACT_TYPES_REQUIRED")
    exact = (
        observed.package_identities == PACKAGE_IDENTITIES
        and observed.gpu_name == "NVIDIA GeForce RTX 5080"
        and observed.vram_total_mib == 16303
        and observed.compute_capability == "12.0"
        and observed.cuda_device == 0
        and observed.immutable_manifest_identity == "bb5a4767bb2eca6d2a71e0aacc2cbaaeab6e01a5baa693cb1330474385e5b6f9"
        and observed.base_manifest_sha256 == "bd0f84711c825a2c213b458a0e2c41d189914ad5ac4bdf283c91a38daab0c090"
        and observed.adapter_manifest_sha256 == "312d6f8cb7c14c769742901c4c80042c104f5a60ba2f80b2913487af22d67ae2"
        and observed.manifests_verified is True
        and observed.model_declared_transformers_version == "5.0.0.dev0"
        and observed.runtime_transformers_version == "5.15.0"
        and observed.compatibility_pair_explicitly_accepted is True
        and type(observed.vram_free_mib) is int
        and observed.vram_free_mib >= authority.required_free_vram_mib
    )
    if not exact:
        raise ValueError("MODEL_LOAD_PRELOAD_ENVIRONMENT_MISMATCH")


def _object(raw: bytes, label: str) -> dict[str, object]:
    if type(raw) is not bytes or not raw:
        raise ValueError(f"{label}_BYTES_REQUIRED")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise ValueError(f"{label}_JSON_INVALID") from exc
    if type(value) is not dict:
        raise ValueError(f"{label}_SHAPE_INVALID")
    return value


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "AUTHORITY_CONTRACT_IDENTITY", "LoadOnlyAuthorityV1", "PreloadEnvironmentV1",
    "parse_load_only_authority_v1", "validate_preload_environment_v1",
)
