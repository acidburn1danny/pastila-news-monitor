import copy
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.production_core_inference_resource_limits_v1 import (
    EXPECTED_ADAPTERS,
    EXPECTED_BASE,
    EXPECTED_EXECUTION_AUTHORITY,
    EXPECTED_RUNTIME,
    EXPECTED_TOKENS,
    InferenceResourceLimitError,
    PEAK_RSS_CEILING_BYTES,
    WALL_TIME_CEILING_NS,
    enforce_inference_resource_limits,
)

ROOT = Path(__file__).resolve().parents[1]


def valid_receipt() -> dict:
    return {
        "schema": "pastila-production-core-inference-resource-calibration-observation",
        "schema_version": 1,
        "candidate": "pastila-editor-core-v1.1-experimental",
        "base_manifest": {"sha256": EXPECTED_BASE, "bytes": 27924394330, "files": 17},
        "adapter_manifest": {"sha256": EXPECTED_ADAPTERS["pastila-editor-core-v1.1-experimental"], "bytes": 243884513, "files": 3},
        "authority_effect": "NON_SEMANTIC_OBSERVATION_NOT_OWNER_APPROVED_LIMITS",
        "execution_authority": EXPECTED_EXECUTION_AUTHORITY.copy(),
        "runtime_versions": EXPECTED_RUNTIME.copy(),
        "network": "DENY_ALL_NEW_NAMESPACE",
        "semantic_candidate_evaluation": False,
        "candidate_promotion_effect": False,
        "candidate_model_executed_non_semantically": True,
        "profile": {
            "total_context_tokens": 8192,
            "max_prefill_tokens": 8192,
            "generation_prompt_tokens": 1924,
            "generated_tokens": 6268,
            "prefill_trials": 3,
            "generation_trials": 1,
            "semantic_input": False,
            "output_decoded_or_inspected": False,
            "technical_token_ceiling": 6268,
            "deterministic": True,
            "nf4_bf16_double_quant": True,
            "triton_cache": "EPHEMERAL_TMPFS",
            "torch_native_bmm_override": "DISABLED_TO_USE_PINNED_ATEN_FALLBACK",
        },
        "load_wall_ns": 10,
        "load_peak_rss_bytes": 10,
        "prefill_trials": [{"wall_ns": 10, "peak_rss_bytes": 10} for _ in range(3)],
        "generation_trials": [{"wall_ns": WALL_TIME_CEILING_NS - 10, "peak_rss_bytes": PEAK_RSS_CEILING_BYTES, "token_identity": EXPECTED_TOKENS["pastila-editor-core-v1.1-experimental"]}],
    }


def test_exact_boundaries_pass_without_mutation() -> None:
    receipt = valid_receipt()
    before = copy.deepcopy(receipt)
    assert enforce_inference_resource_limits(receipt) is None
    assert receipt == before


@pytest.mark.parametrize("field", ["wall", "rss"])
def test_overflow_fails_closed_without_mutation(field: str) -> None:
    receipt = valid_receipt()
    if field == "wall":
        receipt["generation_trials"][0]["wall_ns"] += 1
    else:
        receipt["generation_trials"][0]["peak_rss_bytes"] += 1
    before = copy.deepcopy(receipt)
    with pytest.raises(InferenceResourceLimitError):
        enforce_inference_resource_limits(receipt)
    assert receipt == before


@pytest.mark.parametrize("bad", [None, True, "1", 1.0, -1])
def test_malformed_measurements_are_not_coerced(bad: object) -> None:
    receipt = valid_receipt()
    receipt["load_wall_ns"] = bad
    with pytest.raises(InferenceResourceLimitError):
        enforce_inference_resource_limits(receipt)


@pytest.mark.parametrize("field", ["schema_version", "prefill_trials", "generation_trials", "technical_token_ceiling"])
def test_boolean_numeric_authority_is_rejected(field: str) -> None:
    receipt = valid_receipt()
    if field == "schema_version":
        receipt[field] = True
    else:
        receipt["profile"][field] = True
    with pytest.raises(InferenceResourceLimitError):
        enforce_inference_resource_limits(receipt)


def test_profile_rebinding_is_rejected() -> None:
    receipt = valid_receipt()
    receipt["profile"]["deterministic"] = False
    with pytest.raises(InferenceResourceLimitError):
        enforce_inference_resource_limits(receipt)


def test_framework_binds_owner_approved_limits_and_calibration() -> None:
    value = json.loads((ROOT / "docs/artifacts/production-core-model-qualification-framework-v1.json").read_text(encoding="utf-8"))
    assert value["thresholds"]["wall_time_seconds_per_case_max"] == 600
    assert value["thresholds"]["peak_rss_bytes_per_case_max"] == 16_106_127_360
    evidence = json.loads((ROOT / "docs/artifacts/production-core-inference-resource-limits-qualification-v1.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "OWNER_APPROVED_LIMITS_OFFLINE_QUALIFIED"


def test_committed_receipts_reproduce_declared_json_identities() -> None:
    directory = ROOT / "docs/artifacts/production-core-inference-resource-calibration-receipts"
    expected = {
        "v1-1-a.receipt": "bcd03f8f63d278b80fabea4db24e55a5b7f65007a185cfcfea1398c20e78b069",
        "v1-2-a.receipt": "aeb3fd538b2c00c6b2acaa10ac94d912b6497140f6ead7c6f79d1c3ad01ed887",
        "v1-1-b.receipt": "30a3b8581ecc9c0cdfefbee66764959126023528d8d1bb95bd77bf781c4bcd4d",
        "v1-2-b.receipt": "46570ab41f247d782f1d7ac9c24ee0ae5332d56e28b5f18001b70f253f12995f",
    }
    for name, identity in expected.items():
        lines = (directory / name).read_bytes().splitlines()
        assert len(lines) == 2
        assert hashlib.sha256(lines[0]).hexdigest() == identity
        assert lines[1].decode("ascii") == identity
