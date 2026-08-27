from __future__ import annotations

import ast
import hashlib
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_contract_v2 import (
    ProjectionStatusV1,
    canonical_projection_receipt_bytes_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_projector_binding_v1 import (
    prepare_construction_obligation_v2_projector_binding_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_static_evaluator_v1 import (
    STATIC_PROJECTOR_BINDING_IDENTITY,
    evaluate_injected_construction_obligation_v2_result_v1,
)
from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import (
    _case_context,
    _valid_text,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_static_evaluator_v1.py"


def _fixture():
    context, candidate, authority = _case_context()
    binding = prepare_construction_obligation_v2_projector_binding_v1(
        candidate_utf8=candidate.data, factual_authority_utf8=authority.data)
    return context, candidate, authority, binding, _valid_text(context).encode()


def test_injected_valid_result_returns_existing_projection_pass_receipt() -> None:
    context, _, _, binding, raw = _fixture()
    result = evaluate_injected_construction_obligation_v2_result_v1(
        raw_result=raw, source_binding=binding)
    assert result.static_projector_binding_identity == STATIC_PROJECTOR_BINDING_IDENTITY
    assert result.source_context_identity == context.binding_identity
    assert result.raw_result_sha256 == hashlib.sha256(raw).hexdigest()
    assert result.source_projection_receipt.projection_status is ProjectionStatusV1.PASS
    assert len(result.evaluation_identity) == 64


def test_evaluation_is_deterministic_for_identical_injected_bytes() -> None:
    _, _, _, binding, raw = _fixture()
    first = evaluate_injected_construction_obligation_v2_result_v1(
        raw_result=raw, source_binding=binding)
    second = evaluate_injected_construction_obligation_v2_result_v1(
        raw_result=raw, source_binding=binding)
    assert first == second
    assert canonical_projection_receipt_bytes_v1(first.source_projection_receipt) == (
        canonical_projection_receipt_bytes_v1(second.source_projection_receipt))


def test_invalid_schema_propagates_existing_validation_failure() -> None:
    _, _, _, binding, _ = _fixture()
    with pytest.raises(ValidationError):
        evaluate_injected_construction_obligation_v2_result_v1(
            raw_result=b'{"schema_name":"wrong"}', source_binding=binding)
    with pytest.raises(ValueError, match="INJECTED_RESULT_BYTES_REQUIRED"):
        evaluate_injected_construction_obligation_v2_result_v1(
            raw_result=b"", source_binding=binding)


def test_source_projection_failure_remains_existing_fail_receipt() -> None:
    _, candidate, _, binding, raw = _fixture()
    tampered = raw.replace(candidate.sha256.encode(), b"0" * 64)
    result = evaluate_injected_construction_obligation_v2_result_v1(
        raw_result=tampered, source_binding=binding)
    assert result.source_projection_receipt.projection_status is ProjectionStatusV1.FAIL
    assert result.source_projection_receipt.reason_code == "STAGE_P_SOURCE_REFERENCE_IDENTITY_DRIFT"


def test_stale_binding_identity_fails_before_result_evaluation() -> None:
    _, _, _, binding, raw = _fixture()
    with pytest.raises(ValueError, match="SOURCE_BINDING_IDENTITY_MISMATCH"):
        evaluate_injected_construction_obligation_v2_result_v1(
            raw_result=raw,
            source_binding=replace(binding, projector_freeze_identity="0" * 64))


def test_module_has_no_execution_transport_or_selection_imports() -> None:
    tree = ast.parse(SOURCE.read_text("utf-8")); imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = ("subprocess", "transformers", "tokenizers", "provider", "executor",
                 "runner", "probe", "experimental_core", "torch", "selection", "retry")
    assert not any(any(word in name.lower() for word in forbidden) for name in imports)
