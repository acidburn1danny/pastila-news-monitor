from __future__ import annotations

import ast
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_application_request_v1 import build_construction_obligation_v2_application_request_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_host_wsl_payload_contract_v1 import (
    CONTRACT_IDENTITY,
    build_construction_obligation_v2_host_wsl_payload_v1,
    parse_construction_obligation_v2_host_wsl_payload_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_projector_binding_v1 import prepare_construction_obligation_v2_projector_binding_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_provider_execution_request_binding_v1 import bind_construction_obligation_v2_provider_execution_request_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_request_renderer_v1 import ConstructionObligationV2RequestRendererV1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_static_payload_binding_v1 import build_construction_obligation_v2_static_payload_v1


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_host_wsl_payload_contract_v1.py"
WHEN = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)


def _fixture(candidate: str = "Cerere și referință — «nouă»"):
    source = prepare_construction_obligation_v2_projector_binding_v1(
        candidate_utf8=candidate.encode(), factual_authority_utf8="Autoritate știre".encode())
    static = build_construction_obligation_v2_static_payload_v1(source_binding=source)
    rendered = ConstructionObligationV2RequestRendererV1(project_root=ROOT).render(
        canonical_static_payload=static)
    application = build_construction_obligation_v2_application_request_v1(
        rendered_request=rendered, requested_at=WHEN)
    execution = bind_construction_obligation_v2_provider_execution_request_v1(
        candidate=application)
    return execution, rendered, static


def test_canonical_round_trip_binds_all_request_and_context_identities() -> None:
    execution, rendered, static = _fixture()
    raw = build_construction_obligation_v2_host_wsl_payload_v1(
        execution_binding=execution, rendered_request=rendered,
        canonical_static_payload=static, max_output_tokens=731)
    parsed = parse_construction_obligation_v2_host_wsl_payload_v1(raw_payload=raw)
    assert json.loads(raw)["contract_identity"] == CONTRACT_IDENTITY
    assert parsed.application_request_identity == execution.application_request_identity
    assert parsed.provider_request_id == execution.provider_execution_request.context.request_id
    assert parsed.rendered_request_identity == rendered.request_identity
    assert parsed.static_payload == static
    assert parsed.max_output_tokens == 731


def test_payload_is_deterministic_and_request_isolated() -> None:
    first = _fixture("prima cerere"); second = _fixture("a doua cerere")
    raw = build_construction_obligation_v2_host_wsl_payload_v1(
        execution_binding=first[0], rendered_request=first[1], canonical_static_payload=first[2])
    repeated = build_construction_obligation_v2_host_wsl_payload_v1(
        execution_binding=first[0], rendered_request=first[1], canonical_static_payload=first[2])
    other = build_construction_obligation_v2_host_wsl_payload_v1(
        execution_binding=second[0], rendered_request=second[1], canonical_static_payload=second[2])
    assert raw == repeated
    assert raw != other
    with pytest.raises(ValueError, match="RENDERED_REQUEST_HASH_MISMATCH"):
        build_construction_obligation_v2_host_wsl_payload_v1(
            execution_binding=first[0], rendered_request=first[1], canonical_static_payload=second[2])


def test_mutation_noncanonical_and_token_ceiling_fail_closed() -> None:
    execution, rendered, static = _fixture()
    raw = build_construction_obligation_v2_host_wsl_payload_v1(
        execution_binding=execution, rendered_request=rendered, canonical_static_payload=static)
    value = json.loads(raw); value["source_context_identity"] = "0" * 64
    mutated = (json.dumps(value, ensure_ascii=True, sort_keys=True,
                          separators=(",", ":")) + "\n").encode()
    with pytest.raises(ValueError, match="CONTEXT_MISMATCH"):
        parse_construction_obligation_v2_host_wsl_payload_v1(raw_payload=mutated)
    with pytest.raises(ValueError, match="JSON_INVALID"):
        parse_construction_obligation_v2_host_wsl_payload_v1(raw_payload=b"{")
    with pytest.raises(ValueError, match="TOKEN_CEILING_INVALID"):
        build_construction_obligation_v2_host_wsl_payload_v1(
            execution_binding=execution, rendered_request=rendered,
            canonical_static_payload=static, max_output_tokens=3201)


def test_contract_has_no_execution_or_launch_surface() -> None:
    text = SOURCE.read_text("utf-8"); tree = ast.parse(text); imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom): imports.append(node.module or "")
    forbidden = ("experimental_core", "wsl_execution", "subprocess", "executor",
                 "runner", "probe", "transformers", "tokenizers", "torch")
    assert not any(any(word in name.lower() for word in forbidden) for name in imports)
    assert not any(word in text for word in (".execute(", "build_invocation", "Popen", "from_pretrained", "generate("))
