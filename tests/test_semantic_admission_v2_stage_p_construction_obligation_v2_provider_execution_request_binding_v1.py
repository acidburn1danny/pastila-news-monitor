from __future__ import annotations

import ast
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.provider_execution_v2 import ProviderExecutionRequestV2
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_application_request_v1 import (
    build_construction_obligation_v2_application_request_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_projector_binding_v1 import (
    prepare_construction_obligation_v2_projector_binding_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_provider_execution_request_binding_v1 import (
    BINDING_IDENTITY,
    OLLAMA_ADAPTER_IDENTITY,
    OLLAMA_DESCRIPTOR_FINGERPRINT,
    OLLAMA_DESCRIPTOR_IDENTITY,
    bind_construction_obligation_v2_provider_execution_request_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_request_renderer_v1 import (
    ConstructionObligationV2RequestRendererV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_static_payload_binding_v1 import (
    build_construction_obligation_v2_static_payload_v1,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_provider_execution_request_binding_v1.py"
WHEN = datetime(2026, 8, 28, 12, 0, tzinfo=UTC)


def _candidate(text: str = "Cerere și referință — «nouă»"):
    source = prepare_construction_obligation_v2_projector_binding_v1(
        candidate_utf8=text.encode(), factual_authority_utf8="Autoritate știre".encode()
    )
    payload = build_construction_obligation_v2_static_payload_v1(source_binding=source)
    rendered = ConstructionObligationV2RequestRendererV1(project_root=ROOT).render(
        canonical_static_payload=payload
    )
    return build_construction_obligation_v2_application_request_v1(
        rendered_request=rendered, requested_at=WHEN
    )


def test_binds_exact_provider_execution_request_without_execution(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        del args, kwargs
        raise AssertionError("runtime launch forbidden")

    monkeypatch.setattr("subprocess.Popen", forbidden)
    binding = bind_construction_obligation_v2_provider_execution_request_v1(
        candidate=_candidate()
    )
    request = binding.provider_execution_request
    assert binding.binding_identity == BINDING_IDENTITY
    assert type(request) is ProviderExecutionRequestV2
    assert request.provider.identity == OLLAMA_DESCRIPTOR_IDENTITY
    assert request.provider.fingerprint == OLLAMA_DESCRIPTOR_FINGERPRINT
    assert request.provider.adapter_identity == OLLAMA_ADAPTER_IDENTITY
    assert request.provider.provider_id == "ollama"
    assert tuple(str(item) for item in request.provider.capabilities) == ("metadata",)
    assert request.timeout_policy.timeout_seconds == 240.0
    assert request.context.cancellation.cancellation_requested is False


def test_binding_is_deterministic_and_request_isolated() -> None:
    first = bind_construction_obligation_v2_provider_execution_request_v1(
        candidate=_candidate("prima cerere")
    )
    repeated = bind_construction_obligation_v2_provider_execution_request_v1(
        candidate=_candidate("prima cerere")
    )
    second = bind_construction_obligation_v2_provider_execution_request_v1(
        candidate=_candidate("a doua cerere")
    )
    assert first == repeated
    assert first.application_request_identity != second.application_request_identity
    assert first.provider_execution_request != second.provider_execution_request


def test_forged_candidate_identity_fails_before_authority_build(monkeypatch) -> None:
    candidate = replace(_candidate(), application_request_identity="0" * 64)
    calls = []

    def forbidden_build(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("authority build must not be reached")

    monkeypatch.setattr(
        "pastila_scout.semantic_admission_v2."
        "stage_p_construction_obligation_v2_provider_execution_request_binding_v1."
        "ApplicationRequestAuthorityV1.build",
        forbidden_build,
    )
    with pytest.raises(ValueError, match="CANDIDATE_IDENTITY_MISMATCH"):
        bind_construction_obligation_v2_provider_execution_request_v1(candidate=candidate)
    assert calls == []


def test_source_stops_before_runtime_authority() -> None:
    text = SOURCE.read_text("utf-8")
    tree = ast.parse(text)
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = (
        "provider_execution_ollama_v1",
        "experimental_core",
        "subprocess",
        "transformers",
        "tokenizers",
        "executor",
        "runner",
        "probe",
        "torch",
        "wsl",
    )
    assert not any(any(word in name.lower() for word in forbidden) for name in imports)
    assert ".execute(" not in text
