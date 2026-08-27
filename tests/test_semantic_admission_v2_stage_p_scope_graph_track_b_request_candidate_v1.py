from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_scope_graph_track_b_prompt_v1 import (
    PROMPT_RELATIVE,
    StagePScopeGraphTrackBPromptContractV1,
)
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_track_b_request_candidate_v1 import (
    APPROVED_CONSTRAINT_IDENTITY,
    APPROVED_GRAMMAR_IDENTITY,
    APPROVED_PROMPT_IDENTITY,
    APPROVED_SCHEMA_IDENTITY,
    StagePScopeGraphTrackBRequestCandidateV1,
)


ROOT = Path(__file__).resolve().parents[1]
CASE_REQUEST = {
    "factual_summary": "Autoritatea confirmă exact faptele sursă.",
    "candidate": "Comentariul candidat păstrează domeniul cerut.",
}


def test_prompt_is_exact_unpadded_utf8_and_candidate_first():
    raw = (ROOT / PROMPT_RELATIVE).read_bytes()
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    contract = StagePScopeGraphTrackBPromptContractV1(ROOT)
    assert contract.prompt_identity == APPROVED_PROMPT_IDENTITY
    assert contract.template.index("{candidate}") < contract.template.index("{factual_summary}")
    assert "HMCV1-SASC-01" not in contract.template
    assert "Sarcasm" not in contract.template and "SARCASM" not in contract.template


def test_case01_render_preserves_exact_source_text_and_order():
    request = CASE_REQUEST
    rendered = StagePScopeGraphTrackBPromptContractV1(ROOT).render(
        factual_summary=request["factual_summary"], candidate=request["candidate"])
    assert rendered.count(request["candidate"]) == 1
    assert rendered.count(request["factual_summary"]) == 1
    assert rendered.index(request["candidate"]) < rendered.index(request["factual_summary"])
    assert "candidate-first" in rendered
    assert "authority_support is corroboration" in rendered


def test_request_candidate_preserves_schema_constraint_grammar_and_tokenizer():
    candidate = StagePScopeGraphTrackBRequestCandidateV1(project_root=ROOT)
    assert candidate.schema_identity == APPROVED_SCHEMA_IDENTITY
    assert candidate.constraint_identity == APPROVED_CONSTRAINT_IDENTITY
    assert candidate.grammar_identity == APPROVED_GRAMMAR_IDENTITY
    assert candidate.prompt_identity == APPROVED_PROMPT_IDENTITY
    assert len(candidate.candidate_identity) == 64


def test_authority_construction_uses_exact_rendered_prompt_without_execution():
    request = CASE_REQUEST
    candidate = StagePScopeGraphTrackBRequestCandidateV1(project_root=ROOT)
    authority = candidate.build_authority(request, requested_at=datetime(2026, 8, 26, tzinfo=UTC))
    unit = authority.request_envelope.request_units[0]
    joined = "\n\n".join(message.content for message in unit.messages)
    assert joined == candidate.render_prompt(request)
    assert request["candidate"] in joined and request["factual_summary"] in joined


@pytest.mark.parametrize("source", [None, {}, {"candidate": "x"}, {"factual_summary": "x"}])
def test_invalid_request_fails_before_authority_construction(source):
    candidate = StagePScopeGraphTrackBRequestCandidateV1(project_root=ROOT)
    with pytest.raises(ValueError):
        candidate.render_prompt(source)
