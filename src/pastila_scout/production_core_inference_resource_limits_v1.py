"""Fail-closed resource gates for Qualification Execution Profile v1."""

from __future__ import annotations

WALL_TIME_CEILING_NS = 600_000_000_000
PEAK_RSS_CEILING_BYTES = 16_106_127_360
EXPECTED_EXECUTION_AUTHORITY = {
    "commit": "4a9bd25b3a451157faffb069a4231623168a8779",
    "tree": "750c5356f2fee8eef1f4d5a11e83628f7c7de8d3",
    "probe_sha256": "80a7d0453c29386e9832ef94627426d312cb6bcfe440dfcf64750db601e66ec8",
    "launcher_sha256": "8735cac3c7370af40d6f46be7adf299cbbd669c2c5f7258ef2df1782382de5df",
    "rootfs_sha256": "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4",
}
EXPECTED_RUNTIME = {"bitsandbytes": "0.50.1", "peft": "0.20.0", "torch": "2.13.0+cu130", "transformers": "5.15.0"}
EXPECTED_BASE = "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"
EXPECTED_ADAPTERS = {
    "pastila-editor-core-v1.1-experimental": "0bc4bb1b83b5c1375c1e676844dea079831e7ad0b90db955fa89a2f7d65c3e47",
    "pastila-editor-core-v1.2-experimental": "22b5a7bde7194c66d895b9acab5791a8d8573df67f93704eab933666df7978a2",
}
EXPECTED_TOKENS = {
    "pastila-editor-core-v1.1-experimental": "25c1afc80d33c17c2356da884e2a9d541b4af219943b705a2bdf198b1db07ab6",
    "pastila-editor-core-v1.2-experimental": "8f4f05e60805d8d1f470b40c3f060d7a2c1f2a0618eb1d9b81339482a1430a84",
}


class InferenceResourceLimitError(ValueError):
    """The receipt is malformed or exceeds an owner-approved envelope."""


def enforce_inference_resource_limits(receipt: object) -> None:
    """Validate one receipt without coercion, truncation, retry, or mutation."""
    if not isinstance(receipt, dict):
        raise InferenceResourceLimitError("receipt must be an object")
    if receipt.get("schema") != "pastila-production-core-inference-resource-calibration-observation":
        raise InferenceResourceLimitError("unexpected receipt schema")
    if type(receipt.get("schema_version")) is not int or receipt.get("schema_version") != 1:
        raise InferenceResourceLimitError("unexpected receipt schema version")
    candidate = receipt.get("candidate")
    base = receipt.get("base_manifest")
    adapter = receipt.get("adapter_manifest")
    if receipt.get("execution_authority") != EXPECTED_EXECUTION_AUTHORITY or receipt.get("runtime_versions") != EXPECTED_RUNTIME:
        raise InferenceResourceLimitError("unbound execution authority")
    if candidate not in EXPECTED_ADAPTERS or not isinstance(base, dict) or not isinstance(adapter, dict):
        raise InferenceResourceLimitError("unbound candidate authority")
    if base != {"sha256": EXPECTED_BASE, "bytes": 27924394330, "files": 17} or adapter != {"sha256": EXPECTED_ADAPTERS[candidate], "bytes": 243884513, "files": 3}:
        raise InferenceResourceLimitError("candidate object identity mismatch")
    if receipt.get("authority_effect") != "NON_SEMANTIC_OBSERVATION_NOT_OWNER_APPROVED_LIMITS":
        raise InferenceResourceLimitError("invalid receipt authority effect")
    if receipt.get("network") != "DENY_ALL_NEW_NAMESPACE" or receipt.get("semantic_candidate_evaluation") is not False:
        raise InferenceResourceLimitError("invalid execution boundary")
    if receipt.get("candidate_promotion_effect") is not False or receipt.get("candidate_model_executed_non_semantically") is not True:
        raise InferenceResourceLimitError("invalid authority effect")
    profile = receipt.get("profile")
    required_profile = {
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
    }
    integer_profile_keys = {"total_context_tokens", "max_prefill_tokens", "generation_prompt_tokens", "generated_tokens", "prefill_trials", "generation_trials", "technical_token_ceiling"}
    if profile != required_profile or any(type(profile[key]) is not int for key in integer_profile_keys):
        raise InferenceResourceLimitError("unexpected inference measurement profile")
    load_ns = receipt.get("load_wall_ns")
    load_rss = receipt.get("load_peak_rss_bytes")
    generations = receipt.get("generation_trials")
    prefills = receipt.get("prefill_trials")
    if type(load_ns) is not int or type(load_rss) is not int or not isinstance(generations, list) or not isinstance(prefills, list):
        raise InferenceResourceLimitError("malformed resource measurements")
    if load_ns < 0 or load_rss < 0 or len(generations) != 1 or len(prefills) != 3:
        raise InferenceResourceLimitError("unexpected resource measurement cardinality")
    measurements = [*prefills, *generations]
    if any(not isinstance(item, dict) for item in measurements):
        raise InferenceResourceLimitError("malformed resource trial")
    walls = [item.get("wall_ns") for item in measurements]
    rss = [item.get("peak_rss_bytes") for item in measurements]
    if any(type(value) is not int or value < 0 for value in [*walls, *rss]):
        raise InferenceResourceLimitError("invalid resource measurement")
    if generations[0].get("token_identity") != EXPECTED_TOKENS[candidate]:
        raise InferenceResourceLimitError("generation identity mismatch")
    if load_ns + walls[-1] > WALL_TIME_CEILING_NS:
        raise InferenceResourceLimitError("inference wall-time ceiling exceeded")
    if max([load_rss, *rss]) > PEAK_RSS_CEILING_BYTES:
        raise InferenceResourceLimitError("inference peak-RSS ceiling exceeded")
