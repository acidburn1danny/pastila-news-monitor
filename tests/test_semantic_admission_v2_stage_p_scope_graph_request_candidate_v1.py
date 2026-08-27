from __future__ import annotations

import hashlib
import inspect
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.application_request_authority_v1.canonical import application_request_seals, canonical_application_prompt
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_request_candidate_v1 import (
    APPROVED_GRAMMAR_IDENTITY,
    APPROVED_SCHEMA_IDENTITY,
    APPROVED_TOKENIZER_IDENTITY,
    StagePScopeGraphRequestCandidateV1,
)


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = "Compania a concediat 40 de oameni ieri."
COMMENTARY = "Compania, care a concediat 40 de oameni ieri, și-a pus empatia la păstrare."
AT = datetime(2026, 8, 26, 15, 0, tzinfo=UTC)


def _candidate():
    return StagePScopeGraphRequestCandidateV1(project_root=ROOT)


def test_exact_approved_dependency_tuple_is_bound():
    candidate = _candidate()
    assert candidate.schema_identity == APPROVED_SCHEMA_IDENTITY
    assert candidate.grammar_identity == APPROVED_GRAMMAR_IDENTITY
    assert candidate.tokenizer_identity == APPROVED_TOKENIZER_IDENTITY
    assert candidate.prompt_identity == "sha256:89b8cf92733a33ed0bb37353c918b56071295ca9d4388aa826fcb8c643fb233d"


def test_application_request_contains_exact_unpadded_rendered_prompt():
    candidate = _candidate()
    source = {"factual_summary": SUMMARY, "candidate": COMMENTARY}
    prompt = candidate.render_prompt(source)
    authority = candidate.build_authority(source, requested_at=AT)
    message = authority.request_envelope.request_units[0].messages[0]
    assert message.content == prompt and message.content == message.content.strip()
    assert authority.provider.provider_id == ProviderChoiceV1.OLLAMA.value
    assert authority.timeout_policy.timeout_seconds == 240.0
    assert authority.context.cancellation.cancellation_requested is False


def test_request_identity_is_deterministic_and_source_sensitive():
    candidate = _candidate()
    source = {"factual_summary": SUMMARY, "candidate": COMMENTARY}
    first = candidate.build_authority(source, requested_at=AT)
    second = candidate.build_authority(dict(source), requested_at=AT)
    changed = candidate.build_authority({**source, "candidate": COMMENTARY + " Altceva."}, requested_at=AT)
    assert first.context.request_id == second.context.request_id
    assert first.request_envelope.identity == second.request_envelope.identity
    assert changed.context.request_id != first.context.request_id


def test_candidate_identity_is_deterministic_and_timeout_bound():
    assert _candidate().candidate_identity == _candidate().candidate_identity
    assert StagePScopeGraphRequestCandidateV1(project_root=ROOT, timeout_seconds=120.0).candidate_identity != _candidate().candidate_identity


@pytest.mark.parametrize("source", [None, {}, {"factual_summary": SUMMARY}, {"candidate": COMMENTARY}])
def test_invalid_source_fails_before_authority_construction(source):
    with pytest.raises(ValueError, match="source|source text"):
        _candidate().build_authority(source, requested_at=AT)


@pytest.mark.parametrize("timeout", [0.0, -1.0, 240, "240"])
def test_invalid_timeout_fails_closed(timeout):
    with pytest.raises(ValueError, match="timeout invalid"):
        StagePScopeGraphRequestCandidateV1(project_root=ROOT, timeout_seconds=timeout)


def test_candidate_has_no_execution_surface():
    candidate = _candidate()
    assert not hasattr(candidate, "execute") and not hasattr(candidate, "run") and not hasattr(candidate, "__call__")
    source = inspect.getsource(StagePScopeGraphRequestCandidateV1)
    assert "ApplicationRequestAuthorityV1().build" in source
    assert ".execute(" not in source and ".run(" not in source


def test_request_reference_binds_rendered_prompt_hash_prefix():
    candidate = _candidate()
    source = {"factual_summary": SUMMARY, "candidate": COMMENTARY}
    prompt_hash = hashlib.sha256(candidate.render_prompt(source).encode()).hexdigest()
    authority = candidate.build_authority(source, requested_at=AT)
    unit = authority.request_intent.request_units[0]
    reference = f"semantic-admission-v2:stage-p-scope-graph-v1:{prompt_hash[:24]}"
    expected_unit = application_request_seals(reference, canonical_application_prompt(candidate.render_prompt(source)))[5]
    assert unit.source_request_reference == expected_unit
