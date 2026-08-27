from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.wsl_execution_v1 import WslExecutionProfileV1, canonical_model_profile_v1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_application_request_v1 import build_construction_obligation_v2_application_request_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_host_wsl_payload_contract_v1 import build_construction_obligation_v2_host_wsl_payload_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_projector_binding_v1 import prepare_construction_obligation_v2_projector_binding_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_provider_execution_request_binding_v1 import bind_construction_obligation_v2_provider_execution_request_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_request_renderer_v1 import ConstructionObligationV2RequestRendererV1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_static_executor_binding_v1 import (
    STATIC_BINDING_IDENTITY,
    bind_construction_obligation_v2_static_executor_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_static_payload_binding_v1 import build_construction_obligation_v2_static_payload_v1


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_static_executor_binding_v1.py"
WHEN = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)


def _payload(candidate: str = "Cerere și referință") -> bytes:
    source = prepare_construction_obligation_v2_projector_binding_v1(
        candidate_utf8=candidate.encode(), factual_authority_utf8="Autoritate știre".encode())
    static = build_construction_obligation_v2_static_payload_v1(source_binding=source)
    rendered = ConstructionObligationV2RequestRendererV1(project_root=ROOT).render(
        canonical_static_payload=static)
    application = build_construction_obligation_v2_application_request_v1(
        rendered_request=rendered, requested_at=WHEN)
    execution = bind_construction_obligation_v2_provider_execution_request_v1(
        candidate=application)
    return build_construction_obligation_v2_host_wsl_payload_v1(
        execution_binding=execution, rendered_request=rendered,
        canonical_static_payload=static, max_output_tokens=731)


def test_static_binding_constructs_without_invocation_or_execution(monkeypatch) -> None:
    calls = []
    def forbidden(*args, **kwargs):
        calls.append((args, kwargs)); raise AssertionError("WSL activity forbidden")
    monkeypatch.setattr(WslExecutionBoundaryV1_1, "build_invocation", forbidden)
    monkeypatch.setattr(WslExecutionBoundaryV1_1, "execute", forbidden)
    boundary = WslExecutionBoundaryV1_1(canonical_model_profile_v1())
    binding = bind_construction_obligation_v2_static_executor_v1(
        project_root=ROOT, raw_host_payload=_payload(), wsl_boundary=boundary)
    assert binding.static_binding_identity == STATIC_BINDING_IDENTITY
    assert binding.model_identity == "pastila-editor-core-v1.2-experimental"
    assert binding.max_output_tokens == 731
    assert binding._wsl_boundary is boundary
    assert calls == []


def test_binding_is_deterministic_and_request_isolated() -> None:
    boundary = WslExecutionBoundaryV1_1(canonical_model_profile_v1())
    first = bind_construction_obligation_v2_static_executor_v1(
        project_root=ROOT, raw_host_payload=_payload("prima"), wsl_boundary=boundary)
    repeated = bind_construction_obligation_v2_static_executor_v1(
        project_root=ROOT, raw_host_payload=_payload("prima"), wsl_boundary=boundary)
    second = bind_construction_obligation_v2_static_executor_v1(
        project_root=ROOT, raw_host_payload=_payload("a doua"), wsl_boundary=boundary)
    assert first.binding_identity == repeated.binding_identity
    assert first.binding_identity != second.binding_identity


def test_wrong_boundary_or_profile_fails_closed() -> None:
    with pytest.raises(TypeError, match="BOUNDARY_V1_1_EXACT_TYPE_REQUIRED"):
        bind_construction_obligation_v2_static_executor_v1(
            project_root=ROOT, raw_host_payload=_payload(), wsl_boundary=object())
    wrong = WslExecutionBoundaryV1_1(WslExecutionProfileV1(
        "wrong-profile", "Ubuntu-24.04", "/bin/false"))
    with pytest.raises(ValueError, match="WSL_PROFILE_IDENTITY_MISMATCH"):
        bind_construction_obligation_v2_static_executor_v1(
            project_root=ROOT, raw_host_payload=_payload(), wsl_boundary=wrong)


def test_source_exposes_no_invocation_execution_or_runner_surface() -> None:
    text = SOURCE.read_text("utf-8"); tree = ast.parse(text); imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom): imports.append(node.module or "")
    forbidden = ("experimental_core_v1_2", "runner", "probe", "transformers",
                 "tokenizers", "torch")
    assert not any(any(word in name.lower() for word in forbidden) for name in imports)
    assert not any(word in text for word in (".execute(", "build_invocation(",
                                             "Popen", "from_pretrained", "generate("))
