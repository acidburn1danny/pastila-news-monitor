from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_contract_v2 import ProjectionStatusV1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_projector_binding_v1 import prepare_construction_obligation_v2_projector_binding_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_static_payload_binding_v1 import (
    STATIC_EVALUATOR_IDENTITY,
    STATIC_PROJECTOR_BINDING_IDENTITY,
    build_construction_obligation_v2_static_payload_v1,
    parse_construction_obligation_v2_static_payload_v1,
)
from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import _case_context, _valid_text


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_static_payload_binding_v1.py"


def _fixture():
    context, candidate, authority = _case_context()
    binding = prepare_construction_obligation_v2_projector_binding_v1(
        candidate_utf8=candidate.data, factual_authority_utf8=authority.data)
    return context, binding, _valid_text(context).encode()


def test_canonical_payload_round_trip_binds_both_static_identities() -> None:
    _, binding, _ = _fixture()
    raw = build_construction_obligation_v2_static_payload_v1(source_binding=binding)
    parsed = parse_construction_obligation_v2_static_payload_v1(raw_payload=raw)
    value = json.loads(raw)
    assert value["static_projector_binding_identity"] == STATIC_PROJECTOR_BINDING_IDENTITY
    assert value["static_evaluator_identity"] == STATIC_EVALUATOR_IDENTITY
    assert parsed.payload_sha256 == hashlib.sha256(raw).hexdigest()
    assert parsed.source_binding == binding


def test_payload_exposes_only_injected_projector_and_evaluation_operations() -> None:
    _, binding, result_bytes = _fixture()
    parsed = parse_construction_obligation_v2_static_payload_v1(
        raw_payload=build_construction_obligation_v2_static_payload_v1(
            source_binding=binding))
    projector = parsed.bind_projector(token_pieces={2: "", 20: "{"})
    assert projector.allowed_token_ids([], lambda _: "").token_ids == (20,)
    evaluation = parsed.evaluate_injected_result(raw_result=result_bytes)
    assert evaluation.source_projection_receipt.projection_status is ProjectionStatusV1.PASS


def test_noncanonical_malformed_or_extra_payload_fails_closed() -> None:
    _, binding, _ = _fixture()
    raw = build_construction_obligation_v2_static_payload_v1(source_binding=binding)
    with pytest.raises(ValueError, match="NOT_CANONICAL"):
        parse_construction_obligation_v2_static_payload_v1(raw_payload=b" " + raw)
    value = json.loads(raw); value["unexpected"] = True
    with pytest.raises(ValueError, match="SHAPE_INVALID"):
        parse_construction_obligation_v2_static_payload_v1(
            raw_payload=(json.dumps(value) + "\n").encode())
    with pytest.raises(ValueError, match="JSON_INVALID"):
        parse_construction_obligation_v2_static_payload_v1(raw_payload=b"{")


def test_stale_nested_or_top_level_identity_fails_closed() -> None:
    _, binding, _ = _fixture()
    with pytest.raises(ValueError, match="SOURCE_IDENTITY_MISMATCH"):
        build_construction_obligation_v2_static_payload_v1(
            source_binding=replace(binding, decoder_identity="stale"))
    value = json.loads(build_construction_obligation_v2_static_payload_v1(
        source_binding=binding))
    value["static_evaluator_identity"] = "0" * 64
    raw = (json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":")) + "\n").encode()
    with pytest.raises(ValueError, match="IDENTITY_MISMATCH"):
        parse_construction_obligation_v2_static_payload_v1(raw_payload=raw)


def test_static_payload_has_no_execution_or_prompt_surface() -> None:
    text = SOURCE.read_text("utf-8"); tree = ast.parse(text); imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = ("subprocess", "transformers", "tokenizers", "provider", "executor",
                 "runner", "probe", "experimental_core", "torch", "prompt")
    assert not any(any(word in name.lower() for word in forbidden) for name in imports)
    assert not any(word in text for word in ("command", "timeout_seconds", "max_new_tokens",
                                             "requested_at", "model_identity"))
