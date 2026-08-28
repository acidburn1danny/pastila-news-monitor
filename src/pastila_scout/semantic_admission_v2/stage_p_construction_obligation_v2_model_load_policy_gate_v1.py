"""Source-only Construction-Obligation V2 model-load policy validation gate."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass


POLICY_GATE_IDENTITY = "9410ef484986fc14534334ebf6a6912d381e2882b8fca948de4b215b2e7a8931"
IMMUTABLE_MANIFEST_IDENTITY = "bb5a4767bb2eca6d2a71e0aacc2cbaaeab6e01a5baa693cb1330474385e5b6f9"
BASE_MANIFEST_SHA256 = "bd0f84711c825a2c213b458a0e2c41d189914ad5ac4bdf283c91a38daab0c090"
ADAPTER_MANIFEST_SHA256 = "312d6f8cb7c14c769742901c4c80042c104f5a60ba2f80b2913487af22d67ae2"
FEASIBILITY_IDENTITY = "96078a0269e80e9ae356ed1032594c43e324bbdc81b66bfbc2c0196405f1d8e0"
LIFECYCLE_PREAMBLE_IDENTITY = "a4f958ac8b793da4e5c9d2d91145b8d49c2ca8624d209e9aed0670eced35f678"
PROJECTOR_FREEZE_IDENTITY = "974d5e6257256d7397cb68f90952c66809a536cf5525cbef58b3bbfce6791587"
TOKENIZER_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
DECODER_IDENTITY = "ministral-tokenizer-decode-skip-special-cleanup-false-v1"
CORE_V1_2_SOURCE_SHA256 = "8fe9e740b3263f2988a653a0343334b502fddf0d3cb2be36746de4646242bed5"
CORE_V1_2_MODEL_IDENTITY = "pastila-editor-core-v1.2-experimental"
PACKAGE_IDENTITIES = (
    "transformers==5.15.0", "torch==2.13.0+cu130", "peft==0.20.0",
    "accelerate==1.14.0", "bitsandbytes==0.50.1",
)


@dataclass(frozen=True, slots=True)
class ObservedModelLoadPolicyV1:
    immutable_manifest_identity: str
    base_manifest_sha256: str
    adapter_manifest_sha256: str
    feasibility_identity: str
    lifecycle_preamble_identity: str
    projector_freeze_identity: str
    tokenizer_identity: str
    decoder_identity: str
    core_v1_2_source_sha256: str
    core_v1_2_model_identity: str
    package_identities: tuple[str, ...]
    model_declared_transformers_version: str
    gpu_name: str
    vram_total_mib: int
    compute_capability: str
    quantization: str
    double_quantization: bool
    compute_dtype: str
    prompt_token_ceiling: int
    output_token_ceiling: int
    batch_size: int
    cuda_device: int
    preserve_vision_components: bool
    local_files_only: bool
    cpu_offload: bool
    disk_offload: bool
    retry_count: int
    fallback_enabled: bool


def canonical_observed_model_load_policy_v1() -> ObservedModelLoadPolicyV1:
    return ObservedModelLoadPolicyV1(
        IMMUTABLE_MANIFEST_IDENTITY, BASE_MANIFEST_SHA256,
        ADAPTER_MANIFEST_SHA256, FEASIBILITY_IDENTITY,
        LIFECYCLE_PREAMBLE_IDENTITY, PROJECTOR_FREEZE_IDENTITY,
        TOKENIZER_IDENTITY, DECODER_IDENTITY, CORE_V1_2_SOURCE_SHA256,
        CORE_V1_2_MODEL_IDENTITY, PACKAGE_IDENTITIES, "5.0.0.dev0",
        "NVIDIA GeForce RTX 5080", 16303, "12.0", "NF4_4BIT", True,
        "BF16", 8192, 3200, 1, 0, True, True, False, False, 0, False,
    )


def validate_model_load_policy_gate_v1(
    *, observed: ObservedModelLoadPolicyV1,
) -> bytes:
    """Return a canonical validation receipt; construct or load nothing."""
    if type(observed) is not ObservedModelLoadPolicyV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_MODEL_LOAD_POLICY_EXACT_TYPE_REQUIRED")
    if observed != canonical_observed_model_load_policy_v1():
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_MODEL_LOAD_POLICY_MISMATCH")
    observed_value = asdict(observed)
    observed_value["package_identities"] = list(observed.package_identities)
    observed_sha256 = hashlib.sha256(_canonical(observed_value)).hexdigest()
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-model-load-policy-gate-receipt",
        "schema_version": "1.0.0",
        "policy_gate_identity": POLICY_GATE_IDENTITY,
        "observed_policy_sha256": observed_sha256,
        "result": "POLICY_VALIDATED_SOURCE_ONLY",
        "compatibility_status": "EXACT_VERSION_PAIR_BOUND_NOT_LOAD_VERIFIED",
        "next_event_authorized": False,
        "model_load_started": False,
        "receipt_identity": "",
    }
    value["receipt_identity"] = hashlib.sha256(
        _canonical({key: item for key, item in value.items()
                    if key != "receipt_identity"})).hexdigest()
    return _canonical(value)


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "ObservedModelLoadPolicyV1", "POLICY_GATE_IDENTITY",
    "canonical_observed_model_load_policy_v1",
    "validate_model_load_policy_gate_v1",
)
