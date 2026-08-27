from __future__ import annotations

import ast
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.application_request_authority_v1 import ApplicationProviderRequestV1
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_application_request_v1 import build_construction_obligation_v2_application_request_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_projector_binding_v1 import prepare_construction_obligation_v2_projector_binding_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_request_renderer_v1 import ConstructionObligationV2RequestRendererV1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_static_payload_binding_v1 import build_construction_obligation_v2_static_payload_v1


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_application_request_v1.py"
WHEN = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)


def _rendered(candidate: str = "Țară, știre — «nouă»"):
    binding = prepare_construction_obligation_v2_projector_binding_v1(
        candidate_utf8=candidate.encode(), factual_authority_utf8="Autoritate știre".encode())
    payload = build_construction_obligation_v2_static_payload_v1(source_binding=binding)
    return ConstructionObligationV2RequestRendererV1(project_root=ROOT).render(
        canonical_static_payload=payload)


def test_builds_exact_immutable_application_request_without_authority() -> None:
    rendered = _rendered()
    candidate = build_construction_obligation_v2_application_request_v1(
        rendered_request=rendered, requested_at=WHEN)
    request = candidate.application_request
    assert type(request) is ApplicationProviderRequestV1
    assert request.provider is ProviderChoiceV1.OLLAMA
    assert request.prompt == rendered.rendered_prompt
    assert request.timeout_policy.timeout_seconds == 240.0
    assert request.cancellation.cancellation_requested is False
    assert request.requested_at == WHEN
    assert request.request_reference.endswith(rendered.request_identity[:24])


def test_application_request_identity_is_deterministic_and_request_isolated() -> None:
    first = build_construction_obligation_v2_application_request_v1(
        rendered_request=_rendered("prima cerere"), requested_at=WHEN)
    repeated = build_construction_obligation_v2_application_request_v1(
        rendered_request=_rendered("prima cerere"), requested_at=WHEN)
    second = build_construction_obligation_v2_application_request_v1(
        rendered_request=_rendered("a doua cerere"), requested_at=WHEN)
    assert first.application_request_identity == repeated.application_request_identity
    assert first.application_request_identity != second.application_request_identity


def test_naive_timestamp_or_forged_rendered_request_fails_closed() -> None:
    rendered = _rendered()
    with pytest.raises(ValueError, match="REQUESTED_AT_AWARE_REQUIRED"):
        build_construction_obligation_v2_application_request_v1(
            rendered_request=rendered, requested_at=datetime(2026, 8, 28))
    with pytest.raises(ValueError, match="RENDERED_PROMPT_BYTES_MISMATCH"):
        build_construction_obligation_v2_application_request_v1(
            rendered_request=replace(rendered, rendered_prompt=rendered.rendered_prompt + "x"),
            requested_at=WHEN)
    with pytest.raises(ValueError, match="RENDERED_REQUEST_IDENTITY_MISMATCH"):
        build_construction_obligation_v2_application_request_v1(
            rendered_request=replace(rendered, request_identity="0" * 64), requested_at=WHEN)


def test_builder_has_no_authority_builder_or_execution_import() -> None:
    text = SOURCE.read_text("utf-8"); tree = ast.parse(text); imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = ("authority.authority", "ApplicationRequestAuthorityV1", "subprocess",
                 "transformers", "tokenizers", "executor", "runner", "probe", "torch")
    assert not any(any(word.lower() in name.lower() for word in forbidden) for name in imports)
    assert "ApplicationRequestAuthorityV1" not in text
