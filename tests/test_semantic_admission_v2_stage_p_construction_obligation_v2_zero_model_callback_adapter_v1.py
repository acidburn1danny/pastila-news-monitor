from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_projector_binding_v1 import prepare_construction_obligation_v2_projector_binding_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_zero_model_callback_adapter_v1 import (
    ADAPTER_IDENTITY, ConstructionObligationV2ZeroModelCallbackAdapterV1,
    ZeroModelCallbackFailureV1)
from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import _case_context, _valid_text


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_zero_model_callback_adapter_v1.py"


def _adapter(pieces, candidate="candidat"):
    binding = prepare_construction_obligation_v2_projector_binding_v1(
        candidate_utf8=candidate.encode(), factual_authority_utf8="autoritate".encode())
    return ConstructionObligationV2ZeroModelCallbackAdapterV1(
        source_binding=binding, token_pieces=pieces)


def test_prefix_and_terminal_decisions_are_rebuild_equivalent() -> None:
    context, candidate, authority = _case_context(); raw = _valid_text(context)
    binding = prepare_construction_obligation_v2_projector_binding_v1(
        candidate_utf8=candidate.data, factual_authority_utf8=authority.data)
    adapter = ConstructionObligationV2ZeroModelCallbackAdapterV1(
        source_binding=binding, token_pieces={10: "{", 12: "x", 2: ""})
    prefix = adapter.project(generated_token_ids=(), decode=lambda _: "")
    assert prefix.allowed_token_ids == (10,)
    terminal_ids = tuple(range(len(raw)))
    terminal = adapter.project(generated_token_ids=terminal_ids,
                               decode=lambda ids: raw[:len(ids)])
    assert terminal.allowed_token_ids == (2,)
    assert terminal.projection_receipt.terminal is True
    assert ADAPTER_IDENTITY


def test_no_legal_token_emits_identity_bound_protocol_receipt() -> None:
    adapter = _adapter({10: "x", 2: ""})
    decision = adapter.project(generated_token_ids=(), decode=lambda _: "")
    assert decision.allowed_token_ids == ()
    value = json.loads(decision.no_legal_token_receipt)
    assert value["failure_code"] == "NO_LEGAL_TOKEN_NONTERMINAL"
    assert value["allowed_token_count"] == 0
    assert value["terminal"] is False
    assert len(value["receipt_identity"]) == 64


def test_nonincremental_or_invalid_decode_fails_closed() -> None:
    adapter = _adapter({10: "{", 2: ""})
    adapter.project(generated_token_ids=(1,), decode=lambda _: "{")
    with pytest.raises(ValueError, match="PREFIX_NOT_INCREMENTAL"):
        adapter.project(generated_token_ids=(), decode=lambda _: "")
    invalid = _adapter({10: "{", 2: ""})
    with pytest.raises(ZeroModelCallbackFailureV1):
        invalid.project(generated_token_ids=(), decode=lambda _: 42)


def test_source_has_no_runtime_callback_or_execution_import() -> None:
    text = SOURCE.read_text("utf-8"); tree = ast.parse(text); imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom): imports.append(node.module or "")
    forbidden = ("transformers", "tokenizers", "torch", "wsl_execution", "subprocess",
                 "experimental_core", "durable_executor", "probe")
    assert not any(any(word in name.lower() for word in forbidden) for name in imports)
    assert not any(word in text for word in ("prefix_allowed_tokens_fn", ".generate(",
                                             ".execute(", "build_invocation", "Popen"))
