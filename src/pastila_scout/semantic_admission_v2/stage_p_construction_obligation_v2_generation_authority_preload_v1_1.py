"""Non-executing V1.1 generation-authority and preload admission gate."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass

AUTHORITY_PRELOAD_IDENTITY = "54a5cfc079c0cde964328d9cd03033411b9b50c79b13683ad348ebfc0b93d0d1"
AUTHORITY_CONTRACT_V1_IDENTITY = "d37a8a7ad5f0fed905654e74cb6111570b1abf19ac0629a3b3eee5ed5fa84844"
POLICY_GATE_IDENTITY = "7a6e3629275e80d61b0af20d88393b158f2ac1154d6e9017f5bf3489f5d6b7d4"
SUPERVISOR_IDENTITY = "ce43ed32836005bcd471da40f9003e3d9ba66e090e57fbf66cdf77d0c8b95391"
WORKER_IDENTITY = "8f2b6e445375d2295583ee3eeec6c643dec57bb5f711bdcf2b12abf310e03489"
COMPOSITION_IDENTITY = "c52b5126add3f7975e3e630a618db81549dc74aeea2ab0b6756b6e0d8582e183"
RUNNER_IDENTITY = "ed9303593dea53b9375913e3cb1640cdb11f2e347299435532f7e3935bf755da"
WSL_BINDING_IDENTITY = "c7a09557517e2a762d1d60738bc2c073be458533769bd0a968f25930fe3b6843"
HOST_EXECUTOR_IDENTITY = "7749b2b075c7db788927130505edbaafa1c7cfbd398b1132b01b396f94d97942"
WSL_PROFILE_IDENTITY = "71f66b8bf20b3decb31cfe65d3d94720f9fd1d2c6500c9ef259197cbf94bc7f4"
PACKAGE_IDENTITIES = (
    "transformers==5.15.0", "torch==2.13.0+cu130", "peft==0.20.0",
    "accelerate==1.14.0", "bitsandbytes==0.50.1",
)


@dataclass(frozen=True, slots=True)
class GenerationAuthorityV1_1:
    owner_authority_identity: str
    host_payload_sha256: str
    runner_request_sha256: str
    provider_request_id: str
    source_context_identity: str
    required_free_vram_mib: int
    authority_receipt_identity: str


@dataclass(frozen=True, slots=True)
class GenerationPreloadObservationV1_1:
    package_identities: tuple[str, ...]
    base_manifest_sha256: str
    adapter_manifest_sha256: str
    gpu_name: str
    vram_total_mib: int
    vram_free_mib: int
    compute_capability: str
    cuda_device: int
    quantization: str
    double_quantization: bool
    compute_dtype: str


def parse_generation_authority_v1_1(
    *, raw_receipt: bytes, expected_host_payload_sha256: str,
    expected_runner_request_sha256: str, expected_provider_request_id: str,
    expected_source_context_identity: str,
) -> GenerationAuthorityV1_1:
    """Validate a future owner-issued receipt; this module issues none."""
    value = _object(raw_receipt)
    required = {
        "schema_name", "schema_version", "authority_preload_identity",
        "authority_contract_v1_identity", "policy_gate_identity",
        "supervisor_identity", "worker_identity", "composition_identity",
        "runner_identity", "wsl_binding_identity", "host_executor_identity",
        "wsl_profile_identity", "owner_authority_identity", "host_payload_sha256",
        "runner_request_sha256", "provider_request_id", "source_context_identity",
        "required_free_vram_mib", "attempt_ceiling", "operation",
        "model_load_authorized", "generation_authorized", "prompt_token_ceiling",
        "output_token_ceiling", "retry_authorized", "fallback_authorized",
        "repair_authorized", "selection_authorized", "stage_c_authorized",
        "authority_receipt_identity",
    }
    if set(value) != required:
        raise ValueError("GENERATION_AUTHORITY_V1_1_SHAPE_MISMATCH")
    fixed = (
        value["schema_name"], value["schema_version"], value["authority_preload_identity"],
        value["authority_contract_v1_identity"], value["policy_gate_identity"],
        value["supervisor_identity"], value["worker_identity"],
        value["composition_identity"], value["runner_identity"],
        value["wsl_binding_identity"], value["host_executor_identity"],
        value["wsl_profile_identity"], value["required_free_vram_mib"],
        value["attempt_ceiling"], value["operation"], value["model_load_authorized"],
        value["generation_authorized"], value["prompt_token_ceiling"],
        value["output_token_ceiling"], value["retry_authorized"],
        value["fallback_authorized"], value["repair_authorized"],
        value["selection_authorized"], value["stage_c_authorized"],
    )
    expected = (
        "pastila-semantic-admission-v2-construction-obligation-v2-generation-authority",
        "1.1.0", AUTHORITY_PRELOAD_IDENTITY, AUTHORITY_CONTRACT_V1_IDENTITY,
        POLICY_GATE_IDENTITY, SUPERVISOR_IDENTITY, WORKER_IDENTITY,
        COMPOSITION_IDENTITY, RUNNER_IDENTITY, WSL_BINDING_IDENTITY,
        HOST_EXECUTOR_IDENTITY, WSL_PROFILE_IDENTITY, 14000, 1,
        "GENERATE_ONCE_STAGE_P_ONLY", True, True, 8192, 3200,
        False, False, False, False, False,
    )
    bound = (
        value["host_payload_sha256"], value["runner_request_sha256"],
        value["provider_request_id"], value["source_context_identity"],
    )
    expected_bound = (
        expected_host_payload_sha256, expected_runner_request_sha256,
        expected_provider_request_id, expected_source_context_identity,
    )
    if fixed != expected or bound != expected_bound:
        raise ValueError("GENERATION_AUTHORITY_V1_1_POLICY_OR_BINDING_MISMATCH")
    text_bindings = (value["owner_authority_identity"], *bound)
    if any(type(item) is not str or not item for item in text_bindings):
        raise ValueError("GENERATION_AUTHORITY_V1_1_BINDING_INVALID")
    hashes = (value["host_payload_sha256"], value["runner_request_sha256"],
              value["source_context_identity"])
    if any(not _is_sha256(item) for item in hashes):
        raise ValueError("GENERATION_AUTHORITY_V1_1_HASH_INVALID")
    identity = hashlib.sha256(_canonical(_without_identity(value))).hexdigest()
    if value["authority_receipt_identity"] != identity or raw_receipt != _canonical(value):
        raise ValueError("GENERATION_AUTHORITY_V1_1_SEAL_MISMATCH")
    return GenerationAuthorityV1_1(
        value["owner_authority_identity"], value["host_payload_sha256"],
        value["runner_request_sha256"], value["provider_request_id"],
        value["source_context_identity"], value["required_free_vram_mib"], identity,
    )


def validate_generation_preload_v1_1(
    *, authority: GenerationAuthorityV1_1,
    observed: GenerationPreloadObservationV1_1,
) -> bytes:
    """Admit the start boundary only after exact injected environment validation."""
    if type(authority) is not GenerationAuthorityV1_1:
        raise TypeError("GENERATION_AUTHORITY_V1_1_EXACT_TYPE_REQUIRED")
    if type(observed) is not GenerationPreloadObservationV1_1:
        raise TypeError("GENERATION_PRELOAD_V1_1_EXACT_TYPE_REQUIRED")
    expected = GenerationPreloadObservationV1_1(
        PACKAGE_IDENTITIES,
        "bd0f84711c825a2c213b458a0e2c41d189914ad5ac4bdf283c91a38daab0c090",
        "312d6f8cb7c14c769742901c4c80042c104f5a60ba2f80b2913487af22d67ae2",
        "NVIDIA GeForce RTX 5080", 16303, observed.vram_free_mib, "12.0", 0,
        "NF4_4BIT", True, "BF16",
    )
    if observed != expected or type(observed.vram_free_mib) is not int:
        raise ValueError("GENERATION_PRELOAD_V1_1_ENVIRONMENT_MISMATCH")
    if observed.vram_free_mib < authority.required_free_vram_mib:
        raise ValueError("GENERATION_PRELOAD_V1_1_INSUFFICIENT_FREE_VRAM")
    observation = asdict(observed)
    observation["package_identities"] = list(observed.package_identities)
    value = {
        "schema_name": "pastila-semantic-admission-v2-generation-preload-admission",
        "schema_version": "1.1.0", "authority_preload_identity": AUTHORITY_PRELOAD_IDENTITY,
        "authority_receipt_identity": authority.authority_receipt_identity,
        "observation_sha256": hashlib.sha256(_canonical(observation)).hexdigest(),
        "admission": "MODEL_LOAD_START_ADMITTED", "model_load_started": False,
        "generation_started": False, "receipt_identity": "",
    }
    value["receipt_identity"] = hashlib.sha256(_canonical(_without_identity(
        value, "receipt_identity"))).hexdigest()
    return _canonical(value)


def admit_generation_start_v1_1[T](
    *, authority: GenerationAuthorityV1_1,
    observed: GenerationPreloadObservationV1_1, start: Callable[[], T],
) -> tuple[bytes, T]:
    """Validate first, then invoke the injected start operation exactly once."""
    admission = validate_generation_preload_v1_1(authority=authority, observed=observed)
    return admission, start()


def _object(raw: bytes) -> dict[str, object]:
    if type(raw) is not bytes or not raw:
        raise ValueError("GENERATION_AUTHORITY_V1_1_BYTES_REQUIRED")
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise ValueError("GENERATION_AUTHORITY_V1_1_JSON_INVALID") from exc
    if type(value) is not dict:
        raise ValueError("GENERATION_AUTHORITY_V1_1_SHAPE_INVALID")
    return value


def _without_identity(value: dict[str, object], key: str = "authority_receipt_identity") -> dict[str, object]:
    return {name: item for name, item in value.items() if name != key}


def _is_sha256(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "AUTHORITY_PRELOAD_IDENTITY", "GenerationAuthorityV1_1",
    "GenerationPreloadObservationV1_1", "admit_generation_start_v1_1",
    "parse_generation_authority_v1_1", "validate_generation_preload_v1_1",
)
