from __future__ import annotations

import hashlib
import json
from pathlib import Path


ARTIFACT = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-model-load-policy-feasibility-v1.json")


def artifact():
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_receipt_identity_and_frozen_manifest_bindings():
    value = artifact()
    fields = value["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == value["canonical_identity"]
    assert value["bindings"]["immutable_manifest_identity"] == "bb5a4767bb2eca6d2a71e0aacc2cbaaeab6e01a5baa693cb1330474385e5b6f9"


def test_candidate_token_and_kv_lower_bound_arithmetic():
    value = artifact()
    policy = value["candidate_policy"]
    kv = value["kv_cache_lower_bound"]
    assert policy["maximum_combined_tokens"] == policy["maximum_prompt_tokens"] + policy["maximum_output_tokens"]
    assert kv["bytes_per_token"] == kv["layers"] * 2 * kv["kv_heads"] * kv["head_dim"] * kv["bytes_per_value"]
    assert kv["candidate_combined_token_bytes"] == policy["maximum_combined_tokens"] * kv["bytes_per_token"]


def test_candidate_is_not_load_authority():
    value = artifact()
    assert value["candidate_policy"]["status"] == "CANDIDATE_NOT_AUTHORIZED"
    assert all(decision is False for decision in value["owner_decisions_remaining"].values())
    assert value["authority"]["feasibility_receipt_normalization"] is True
    assert all(
        permission is False
        for name, permission in value["authority"].items()
        if name != "feasibility_receipt_normalization"
    )


def test_activity_proves_header_only_zero_execution():
    activity = artifact()["activity"]
    assert activity["safetensors_header_reads"] == 7
    assert all(value == 0 for name, value in activity.items() if name != "safetensors_header_reads")
