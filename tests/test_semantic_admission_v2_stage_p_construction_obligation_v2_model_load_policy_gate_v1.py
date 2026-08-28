from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import fields, replace
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_model_load_policy_gate_v1 import (
    POLICY_GATE_IDENTITY,
    canonical_observed_model_load_policy_v1,
    validate_model_load_policy_gate_v1,
)


SOURCE = Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_model_load_policy_gate_v1.py")
ARTIFACT = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-model-load-policy-gate-v1.json")


def _mutation(field):
    observed = canonical_observed_model_load_policy_v1()
    value = getattr(observed, field.name)
    if type(value) is bool:
        changed = not value
    elif type(value) is int:
        changed = value + 1
    elif type(value) is tuple:
        changed = value + ("unexpected==1",)
    else:
        changed = value + "-drift"
    return replace(observed, **{field.name: changed})


def test_canonical_policy_emits_deterministic_non_authorizing_receipt():
    observed = canonical_observed_model_load_policy_v1()
    first = validate_model_load_policy_gate_v1(observed=observed)
    assert first == validate_model_load_policy_gate_v1(observed=observed)
    receipt = json.loads(first)
    assert receipt["policy_gate_identity"] == POLICY_GATE_IDENTITY
    assert receipt["result"] == "POLICY_VALIDATED_SOURCE_ONLY"
    assert receipt["next_event_authorized"] is False
    assert receipt["model_load_started"] is False
    material = {key: value for key, value in receipt.items() if key != "receipt_identity"}
    canonical = (json.dumps(material, ensure_ascii=True, sort_keys=True,
                            separators=(",", ":")) + "\n").encode()
    assert hashlib.sha256(canonical).hexdigest() == receipt["receipt_identity"]


@pytest.mark.parametrize("field", fields(type(canonical_observed_model_load_policy_v1())), ids=lambda field: field.name)
def test_every_policy_mutation_fails_closed(field):
    with pytest.raises(ValueError, match="POLICY_MISMATCH"):
        validate_model_load_policy_gate_v1(observed=_mutation(field))


def test_wrong_type_fails_closed():
    with pytest.raises(TypeError, match="EXACT_TYPE_REQUIRED"):
        validate_model_load_policy_gate_v1(observed=object())


def test_source_has_validation_only_and_no_loading_or_execution_surface():
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        node.module for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not imported.intersection({"transformers", "torch", "peft", "subprocess", "importlib"})
    forbidden = (
        "from_pretrained", "BitsAndBytesConfig", ".generate(", "build_invocation",
        ".execute(", "MODEL_LOAD_STARTED", "AutoModel", "PeftModel",
    )
    assert all(term not in source for term in forbidden)


def test_artifact_identity_and_authority_are_sealed():
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    identity_fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(identity_fields).encode()).hexdigest() == artifact["canonical_identity"]
    assert artifact["canonical_identity"] == POLICY_GATE_IDENTITY
    assert artifact["authority"]["policy_validation"] is True
    assert all(value is False for key, value in artifact["authority"].items() if key != "policy_validation")
