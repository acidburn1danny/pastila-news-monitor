from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_projector_binding_v1 import prepare_construction_obligation_v2_projector_binding_v1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_request_renderer_v1 import (
    DATA_BEGIN,
    DATA_END,
    POLICY_BEGIN,
    POLICY_END,
    PROMPT_RELATIVE,
    PROMPT_SHA256,
    ConstructionObligationV2RequestRendererV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_static_payload_binding_v1 import build_construction_obligation_v2_static_payload_v1


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_request_renderer_v1.py"


def _payload(candidate: str = "Țară, știre — «nouă»") -> bytes:
    binding = prepare_construction_obligation_v2_projector_binding_v1(
        candidate_utf8=candidate.encode(),
        factual_authority_utf8="Autoritatea confirmă știrea.".encode())
    return build_construction_obligation_v2_static_payload_v1(source_binding=binding)


def test_prompt_identity_and_required_semantic_boundaries() -> None:
    prompt = (ROOT / PROMPT_RELATIVE).read_bytes()
    assert hashlib.sha256(prompt).hexdigest() == PROMPT_SHA256
    text = prompt.decode()
    for requirement in (
        "Produce exactly one JSON value", "candidate-first", "factual-authority source",
        "immutable UTF-8 source-span references", "Creative-Target", "Scope-Graph",
        "Do not retry", "Stage C"):
        assert requirement in text


def test_render_is_deterministic_identity_bound_and_unicode_preserving() -> None:
    payload = _payload(); renderer = ConstructionObligationV2RequestRendererV1(project_root=ROOT)
    first = renderer.render(canonical_static_payload=payload)
    second = renderer.render(canonical_static_payload=payload)
    assert first == second
    assert first.static_payload_sha256 == hashlib.sha256(payload).hexdigest()
    assert first.rendered_prompt_sha256 == hashlib.sha256(
        first.rendered_prompt.encode()).hexdigest()
    assert len(first.request_identity) == 64
    assert DATA_BEGIN.decode() in first.rendered_prompt
    assert DATA_END.decode() in first.rendered_prompt
    assert POLICY_BEGIN.decode() in first.rendered_prompt
    assert POLICY_END.decode() in first.rendered_prompt
    assert "Țară" not in first.rendered_prompt


def test_request_and_source_contexts_are_isolated() -> None:
    renderer = ConstructionObligationV2RequestRendererV1(project_root=ROOT)
    first = renderer.render(canonical_static_payload=_payload("prima cerere"))
    second = renderer.render(canonical_static_payload=_payload("a doua cerere"))
    assert first.static_payload_sha256 != second.static_payload_sha256
    assert first.request_identity != second.request_identity


def test_case01_request_exposes_the_exact_sealed_terminal_contract() -> None:
    request = json.loads((ROOT / "tests/fixtures/semantic_admission_v2/phase2_case01_request.json").read_bytes())
    binding = prepare_construction_obligation_v2_projector_binding_v1(
        candidate_utf8=request["candidate"].encode(),
        factual_authority_utf8=request["factual_summary"].encode())
    rendered = ConstructionObligationV2RequestRendererV1(project_root=ROOT).render(
        canonical_static_payload=build_construction_obligation_v2_static_payload_v1(
            source_binding=binding))
    policy_text = rendered.rendered_prompt.split(
        POLICY_BEGIN.decode() + "\n", 1)[1].split(POLICY_END.decode(), 1)[0]
    policy = json.loads(policy_text)
    assert policy["required_constructions"][0]["candidate_start_utf8"] == 0
    assert policy["required_constructions"][0]["candidate_end_utf8"] == len(
        request["candidate"].encode())
    assert policy["required_returns"][0]["entry_id"] == "P2"
    assert policy["qualifications"][0]["required_modality"] == "POSSIBLE"
    assert len(policy["identity"]) == 64


def test_malformed_or_noncanonical_payload_fails_before_rendering() -> None:
    renderer = ConstructionObligationV2RequestRendererV1(project_root=ROOT)
    with pytest.raises(ValueError, match="NOT_CANONICAL"):
        renderer.render(canonical_static_payload=b" " + _payload())
    with pytest.raises(ValueError, match="JSON_INVALID"):
        renderer.render(canonical_static_payload=b"{")


def test_renderer_has_no_application_or_execution_import_surface() -> None:
    text = SOURCE.read_text("utf-8"); tree = ast.parse(text); imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = ("subprocess", "transformers", "tokenizers", "provider", "executor",
                 "runner", "probe", "experimental_core", "torch", "application_request")
    assert not any(any(word in name.lower() for word in forbidden) for name in imports)
    assert not any(word in text for word in ("timeout_seconds", "requested_at",
                                             "ProviderChoice", "ApplicationProviderRequest"))
