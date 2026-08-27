from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runner_protocol_contract_v1 import (
    RUNNER_PROTOCOL_IDENTITY, SCHEMA_IDENTITIES, canonical_schema_bytes, schema_value)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_runner_protocol_contract_v1.py"
NAMES = ("request", "result", "lifecycle", "no_legal_token")


def test_all_schema_bytes_and_composite_identity_are_deterministic() -> None:
    first = {name: canonical_schema_bytes(name) for name in NAMES}
    second = {name: canonical_schema_bytes(name) for name in NAMES}
    assert first == second
    assert all(value.endswith(b"\n") for value in first.values())
    assert {name: hashlib.sha256(value).hexdigest() for name, value in first.items()} == SCHEMA_IDENTITIES
    assert len(RUNNER_PROTOCOL_IDENTITY) == 64


def test_schema_copies_cannot_mutate_frozen_module_state() -> None:
    value = schema_value("request"); value["properties"].clear()
    assert schema_value("request")["properties"]
    with pytest.raises(ValueError, match="SCHEMA_NAME_INVALID"):
        canonical_schema_bytes("unknown")


def test_request_binds_payload_context_and_bounded_ceiling() -> None:
    schema = schema_value("request"); properties = schema["properties"]
    assert schema["additionalProperties"] is False
    assert properties["max_output_tokens"] == {"type": "integer", "minimum": 1, "maximum": 3200}
    assert {"host_payload_sha256", "provider_request_id", "source_context_identity"} <= set(schema["required"])


def test_no_legal_token_receipt_is_nonterminal_zero_admission() -> None:
    properties = schema_value("no_legal_token")["properties"]
    assert properties["terminal"] == {"const": False}
    assert properties["allowed_token_count"] == {"const": 0}
    assert properties["failure_code"] == {"const": "NO_LEGAL_TOKEN_NONTERMINAL"}
    assert properties["dfa_mode"] == {"enum": ["PREFIX", "DEAD"]}


def test_result_separates_terminal_constraint_and_execution_outcomes() -> None:
    schema = schema_value("result")
    statuses = schema["properties"]["status"]["enum"]
    assert statuses == ["TERMINAL_OUTPUT", "CONSTRAINT_LIVENESS_FAILURE", "EXECUTION_FAILURE"]
    branches = schema["oneOf"]
    assert branches[0]["properties"]["terminal_eos"] == {"const": True}
    assert branches[1]["properties"]["output_utf8_base64"] == {"type": "null"}
    assert branches[2]["properties"]["no_legal_token_receipt_identity"] == {"type": "null"}


def test_lifecycle_is_identity_chained_and_source_has_no_execution_surface() -> None:
    schema = schema_value("lifecycle")
    assert {"sequence", "previous_event_identity", "event_identity"} <= set(schema["required"])
    text = SOURCE.read_text("utf-8"); tree = ast.parse(text); imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom): imports.append(node.module or "")
    forbidden = ("wsl", "subprocess", "executor", "runner", "probe", "transformers", "tokenizers", "torch")
    assert not any(any(word in name.lower() for word in forbidden) for name in imports)
    assert not any(word in text for word in (".execute(", "build_invocation", "Popen", "generate("))
