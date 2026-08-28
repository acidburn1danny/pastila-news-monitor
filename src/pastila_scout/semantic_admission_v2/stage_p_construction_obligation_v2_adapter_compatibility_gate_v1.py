"""Pure, source-only adapter compatibility gate for the frozen load-only lineage."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


ADAPTER_COMPATIBILITY_GATE_IDENTITY = "66b89ee1b4d8f9832b86a59c9b83c07f8a2c0c3e1a9f25494ad50ed7c4b2ccdd"
ADAPTER_CONFIG_SHA256 = "7e75a4f0aa2b70cf29f491808fdfd7b1d93d89cb2befd6cee6cf3f7153bb996f"
ADAPTER_WEIGHTS_SHA256 = "ec780f63a5c838121f573b6bce987f1f6f5070b256b9db8480b2a95b131ec01f"
PEFT_MODEL_SOURCE_SHA256 = "c07bf9545b3b17ea0363263b11fc25d0a2ebe814e3f8083da3fa08adaa824879"
PEFT_LORA_LAYER_SOURCE_SHA256 = "1ef4e7033ebd01c9c6fbf0fc3837695b75b795c54f8a837b7578e8dfba2251a4"
LOAD_RESULT_IDENTITY = "49b74b00edb7fde2afea3c46cdc2ad53ad7910e1cec418e0ae686b9c87ae8134"
TARGET_MODULES = ("down_proj", "gate_proj", "k_proj", "o_proj", "q_proj", "up_proj", "v_proj")


@dataclass(frozen=True, slots=True)
class AdapterCompatibilityObservationV1:
    adapter_config_sha256: str
    adapter_weights_sha256: str
    peft_model_source_sha256: str
    peft_lora_layer_source_sha256: str
    target_modules: tuple[str, ...]
    init_lora_weights: bool
    inference_mode: bool
    rank: int
    lora_alpha: int
    lora_dropout: float
    adapter_tensor_keys: tuple[str, ...]
    missing_adapter_keys: tuple[str, ...]
    unexpected_adapter_keys: tuple[str, ...]


def expected_language_adapter_keys_v1() -> tuple[str, ...]:
    keys = []
    for layer in range(40):
        for module in TARGET_MODULES:
            group = "self_attn" if module in {"q_proj", "k_proj", "v_proj", "o_proj"} else "mlp"
            prefix = f"base_model.model.model.language_model.layers.{layer}.{group}.{module}"
            keys.extend((f"{prefix}.lora_A.weight", f"{prefix}.lora_B.weight"))
    return tuple(sorted(keys))


def expected_vision_missing_keys_v1() -> tuple[str, ...]:
    keys = []
    for layer in range(24):
        for module in TARGET_MODULES:
            group = "attention" if module in {"q_proj", "k_proj", "v_proj", "o_proj"} else "feed_forward"
            prefix = f"base_model.model.model.vision_tower.transformer.layers.{layer}.{group}.{module}"
            keys.extend((f"{prefix}.lora_A.default.weight", f"{prefix}.lora_B.default.weight"))
    return tuple(sorted(keys))


def canonical_adapter_compatibility_observation_v1() -> AdapterCompatibilityObservationV1:
    return AdapterCompatibilityObservationV1(
        ADAPTER_CONFIG_SHA256, ADAPTER_WEIGHTS_SHA256, PEFT_MODEL_SOURCE_SHA256,
        PEFT_LORA_LAYER_SOURCE_SHA256, TARGET_MODULES, True, True, 16, 32, 0.05,
        expected_language_adapter_keys_v1(), expected_vision_missing_keys_v1(), (),
    )


def validate_adapter_compatibility_gate_v1(
    *, observed: AdapterCompatibilityObservationV1,
) -> bytes:
    if type(observed) is not AdapterCompatibilityObservationV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_ADAPTER_COMPATIBILITY_EXACT_TYPE_REQUIRED")
    if observed != canonical_adapter_compatibility_observation_v1():
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_ADAPTER_COMPATIBILITY_MISMATCH")
    language_keys = observed.adapter_tensor_keys
    vision_keys = observed.missing_adapter_keys
    language_sha = hashlib.sha256("\n".join(language_keys).encode()).hexdigest()
    vision_sha = hashlib.sha256("\n".join(vision_keys).encode()).hexdigest()
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-adapter-compatibility-gate-receipt",
        "schema_version": "1.0.0",
        "adapter_compatibility_gate_identity": ADAPTER_COMPATIBILITY_GATE_IDENTITY,
        "load_result_identity": LOAD_RESULT_IDENTITY,
        "language_adapter_tensor_count": len(language_keys),
        "language_adapter_keys_sha256": language_sha,
        "expected_vision_missing_key_count": len(vision_keys),
        "expected_vision_missing_keys_sha256": vision_sha,
        "unexpected_missing_or_extra_key_count": 0,
        "initialization_proof": "PEFT_INIT_TRUE_LORA_B_ZERO",
        "classification": "STRUCTURAL_NO_OP_VISION_TARGET_OVERMATCH",
        "model_load_authorized": False,
        "generation_authorized": False,
        "runtime_or_production_authorized": False,
        "receipt_identity": "",
    }
    value["receipt_identity"] = hashlib.sha256(_canonical(
        {key: item for key, item in value.items() if key != "receipt_identity"})).hexdigest()
    return _canonical(value)


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "ADAPTER_COMPATIBILITY_GATE_IDENTITY", "AdapterCompatibilityObservationV1",
    "canonical_adapter_compatibility_observation_v1",
    "expected_language_adapter_keys_v1", "expected_vision_missing_keys_v1",
    "validate_adapter_compatibility_gate_v1",
)
