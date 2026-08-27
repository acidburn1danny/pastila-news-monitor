from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_2 import bind_static_projector_preflight_v1_2
from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_3 import bind_static_callback_preflight_v1_3
from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_4 import build_zero_execution_lifecycle_preamble_v1_4
from test_experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_2 import preflight


SOURCE = Path("src/pastila_scout/experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_4.py")
ARTIFACT = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-runner-lifecycle-preamble-v1-4.json")


def callback_preflight():
    return bind_static_callback_preflight_v1_3(
        projector_preflight=bind_static_projector_preflight_v1_2(preflight=preflight()))


def test_builds_exact_three_event_append_only_preamble():
    result = build_zero_execution_lifecycle_preamble_v1_4(
        callback_preflight=callback_preflight())
    values = [json.loads(raw) for raw in result.events]
    assert [value["event"] for value in values] == [
        "REQUEST_VALIDATED", "TOKENIZER_IDENTITY_VALIDATED", "PROJECTOR_CONSTRUCTED"]
    assert [value["sequence"] for value in values] == [0, 1, 2]
    assert values[0]["previous_event_identity"] is None
    assert values[1]["previous_event_identity"] == values[0]["event_identity"]
    assert values[2]["previous_event_identity"] == values[1]["event_identity"]
    assert result.terminal_event_identity == values[2]["event_identity"]
    assert all("MODEL_LOAD" not in value["event"] for value in values)


def test_wrong_type_fails_before_any_event():
    with pytest.raises(TypeError, match="PREFLIGHT_V1_3_REQUIRED"):
        build_zero_execution_lifecycle_preamble_v1_4(callback_preflight=object())


def test_source_stops_before_execution_and_artifact_is_sealed():
    source = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert not modules.intersection({"transformers", "torch", "peft", "subprocess", "importlib"})
    assert all(term not in source for term in ("from_pretrained", ".generate(", "MODEL_LOAD_STARTED", "if __name__"))
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    fields = artifact["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == artifact["canonical_identity"]
    assert all(value is False for value in artifact["authority"].values())
