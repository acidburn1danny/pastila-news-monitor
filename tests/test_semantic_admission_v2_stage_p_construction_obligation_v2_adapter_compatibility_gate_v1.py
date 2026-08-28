from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_adapter_compatibility_gate_v1 import (
    ADAPTER_COMPATIBILITY_GATE_IDENTITY, AdapterCompatibilityObservationV1,
    canonical_adapter_compatibility_observation_v1, expected_language_adapter_keys_v1,
    expected_vision_missing_keys_v1, validate_adapter_compatibility_gate_v1,
)


ARTIFACT=Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-adapter-compatibility-gate-v1.json")


def test_exact_inventory_and_structural_no_op_receipt_are_deterministic():
    observed=canonical_adapter_compatibility_observation_v1()
    assert len(expected_language_adapter_keys_v1())==560
    assert len(expected_vision_missing_keys_v1())==336
    assert all("language_model" in key for key in observed.adapter_tensor_keys)
    assert all("vision_tower" in key for key in observed.missing_adapter_keys)
    first=validate_adapter_compatibility_gate_v1(observed=observed)
    assert first==validate_adapter_compatibility_gate_v1(observed=observed)
    value=json.loads(first)
    assert value["classification"]=="STRUCTURAL_NO_OP_VISION_TARGET_OVERMATCH"
    assert value["unexpected_missing_or_extra_key_count"]==0
    assert not any((value["model_load_authorized"],value["generation_authorized"],
                    value["runtime_or_production_authorized"]))
    identity=value.pop("receipt_identity")
    canonical=(json.dumps(value,sort_keys=True,separators=(",", ":"))+"\n").encode()
    assert identity==hashlib.sha256(canonical).hexdigest()


@pytest.mark.parametrize("field", [item.name for item in dataclasses.fields(AdapterCompatibilityObservationV1)])
def test_every_observation_mutation_fails_closed(field):
    observed=canonical_adapter_compatibility_observation_v1();value=getattr(observed,field)
    if type(value) is bool:mutation=not value
    elif type(value) is int:mutation=value+1
    elif type(value) is float:mutation=value+0.01
    elif type(value) is tuple:mutation=value+("unexpected",)
    else:mutation=value+"-drift"
    with pytest.raises(ValueError,match="COMPATIBILITY_MISMATCH"):
        validate_adapter_compatibility_gate_v1(observed=dataclasses.replace(observed,**{field:mutation}))


def test_wrong_type_and_source_authority_are_fail_closed():
    with pytest.raises(TypeError,match="EXACT_TYPE"):
        validate_adapter_compatibility_gate_v1(observed=object())
    source=Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_adapter_compatibility_gate_v1.py").read_text("utf-8")
    for forbidden in ("from_pretrained","import torch","from torch","import peft","from peft",
                      "import transformers","from transformers",".generate(","subprocess","wsl.exe"):
        assert forbidden not in source.lower()


def test_artifact_identity_rederives():
    artifact=json.loads(ARTIFACT.read_text("utf-8"))
    identity=hashlib.sha256("\n".join(artifact["identity_derivation"]["ordered_utf8_fields"]).encode()).hexdigest()
    assert identity==ADAPTER_COMPATIBILITY_GATE_IDENTITY==artifact["canonical_identity"]
