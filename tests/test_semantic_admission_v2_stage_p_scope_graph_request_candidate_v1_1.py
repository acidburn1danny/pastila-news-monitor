from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.application_request_authority_v1.canonical import application_request_seals, canonical_application_prompt
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_request_candidate_v1_1 import (
    APPROVED_GRAMMAR_IDENTITY, APPROVED_SCHEMA_IDENTITY, APPROVED_TOKENIZER_IDENTITY,
    StagePScopeGraphRequestCandidateV1_1,
)


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = "Compania a concediat 40 de oameni ieri."
COMMENTARY = "Compania, care a concediat 40 de oameni ieri, și-a pus empatia la păstrare."
AT = datetime(2026, 8, 26, 16, 0, tzinfo=UTC)


def _candidate():
    return StagePScopeGraphRequestCandidateV1_1(project_root=ROOT)


def test_exact_v1_1_dependency_tuple_is_bound():
    value = _candidate()
    assert value.schema_identity == APPROVED_SCHEMA_IDENTITY
    assert value.grammar_identity == APPROVED_GRAMMAR_IDENTITY
    assert value.tokenizer_identity == APPROVED_TOKENIZER_IDENTITY
    assert value.prompt_identity == "sha256:202e42e727f80d161a6fde451982b7efbd2be41ab6bab6df53b0812b648ce083"


def test_application_authority_preserves_exact_unpadded_prompt_and_policy():
    value = _candidate(); source = {"factual_summary": SUMMARY, "candidate": COMMENTARY}
    prompt = value.render_prompt(source); authority = value.build_authority(source, requested_at=AT)
    assert authority.request_envelope.request_units[0].messages[0].content == prompt == prompt.strip()
    assert authority.provider.provider_id == ProviderChoiceV1.OLLAMA.value
    assert authority.timeout_policy.timeout_seconds == 240.0
    assert authority.context.cancellation.cancellation_requested is False


def test_request_identity_is_deterministic_source_sensitive_and_hash_bound():
    value = _candidate(); source = {"factual_summary": SUMMARY, "candidate": COMMENTARY}
    first = value.build_authority(source, requested_at=AT); second = value.build_authority(dict(source), requested_at=AT)
    changed = value.build_authority({**source, "candidate": COMMENTARY + " Altceva."}, requested_at=AT)
    assert first.context.request_id == second.context.request_id != changed.context.request_id
    prompt = value.render_prompt(source); prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    reference = f"semantic-admission-v2:stage-p-scope-graph-v1-1:{prompt_hash[:24]}"
    expected = application_request_seals(reference, canonical_application_prompt(prompt))[5]
    assert first.request_intent.request_units[0].source_request_reference == expected


def test_candidate_identity_binds_timeout_and_is_deterministic():
    assert _candidate().candidate_identity == _candidate().candidate_identity
    assert StagePScopeGraphRequestCandidateV1_1(project_root=ROOT, timeout_seconds=120.0).candidate_identity != _candidate().candidate_identity


@pytest.mark.parametrize("source", [None, {}, {"factual_summary": SUMMARY}, {"candidate": COMMENTARY}])
def test_invalid_source_fails_before_construction(source):
    with pytest.raises(ValueError, match="source"):
        _candidate().build_authority(source, requested_at=AT)


def test_candidate_has_no_execution_surface():
    value = _candidate()
    assert not hasattr(value, "execute") and not hasattr(value, "run") and not hasattr(value, "__call__")
