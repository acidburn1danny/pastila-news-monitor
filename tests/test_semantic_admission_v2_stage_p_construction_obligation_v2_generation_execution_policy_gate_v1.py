from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import fields, replace
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_execution_policy_gate_v1 import (
    POLICY_GATE_IDENTITY,
    canonical_observed_generation_execution_policy_v1,
    validate_generation_execution_policy_gate_v1,
)


SOURCE = Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_generation_execution_policy_gate_v1.py")
ARTIFACT = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-execution-policy-gate-v1.json")
RECEIPT = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-policy-validation-receipt-v1.json")


def _mutation(field):
    observed = canonical_observed_generation_execution_policy_v1()
    value = getattr(observed, field.name)
    if type(value) is bool:
        changed = not value
    elif type(value) is int:
        changed = value + 1
    elif type(value) is float:
        changed = value + 0.5
    elif type(value) is tuple:
        changed = value + ("unexpected",)
    else:
        changed = value + "-drift"
    return replace(observed, **{field.name: changed})


def test_canonical_policy_is_deterministic_non_authorizing_and_frozen() -> None:
    observed = canonical_observed_generation_execution_policy_v1()
    raw = validate_generation_execution_policy_gate_v1(observed=observed)
    assert raw == validate_generation_execution_policy_gate_v1(observed=observed)
    assert raw == RECEIPT.read_bytes()
    receipt = json.loads(raw)
    assert receipt["policy_gate_identity"] == POLICY_GATE_IDENTITY
    assert receipt["generation_started"] is receipt["generation_authorized"] is False
    material = {key: value for key, value in receipt.items() if key != "receipt_identity"}
    canonical = (json.dumps(material, ensure_ascii=True, sort_keys=True,
                            separators=(",", ":")) + "\n").encode()
    assert hashlib.sha256(canonical).hexdigest() == receipt["receipt_identity"]


@pytest.mark.parametrize(
    "field", fields(type(canonical_observed_generation_execution_policy_v1())),
    ids=lambda field: field.name,
)
def test_every_policy_mutation_fails_closed(field) -> None:
    with pytest.raises(ValueError, match="POLICY_MISMATCH"):
        validate_generation_execution_policy_gate_v1(observed=_mutation(field))


def test_wrong_type_and_source_execution_surfaces_fail_review() -> None:
    with pytest.raises(TypeError, match="EXACT_TYPE_REQUIRED"):
        validate_generation_execution_policy_gate_v1(observed=object())
    source = SOURCE.read_text("utf-8")
    imported = {
        node.module for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not imported.intersection({"transformers", "torch", "peft", "subprocess", "importlib"})
    assert all(term not in source for term in (
        "from_pretrained", "BitsAndBytesConfig", ".generate(", "build_invocation",
        ".execute(", "MODEL_LOAD_STARTED", "GENERATION_STARTED", "AutoTokenizer",
    ))


def test_artifact_identity_and_provider_local_authority_separation() -> None:
    artifact = json.loads(ARTIFACT.read_text("utf-8"))
    fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == POLICY_GATE_IDENTITY
    assert artifact["canonical_identity"] == POLICY_GATE_IDENTITY
    reconciliation = artifact["execution_reconciliation"]
    assert reconciliation["request_provider_execution_authorized"] is False
    assert reconciliation["selected_execution_mode"] == "LOCAL_MODEL_DIRECT_EXECUTION"
    assert artifact["limits"] == {
        "prompt_tokens_maximum": 8192, "output_tokens_maximum": 3200,
        "batch_size": 1, "attempt_ceiling": 1,
    }
    assert all(value is False for key, value in artifact["authority"].items()
               if key != "policy_validation")
