from dataclasses import replace

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_character_controller_v1 import (
    StagePConstructionObligationCharacterControllerV1, _allowance_for_state)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generated_suffix_callback_v1 import (
    RequestBoundGeneratedSuffixCallbackV1)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_token_projector_v2 import (
    StagePConstructionObligationV2TokenProjectorV2)
from pastila_scout.semantic_admission_v2.stage_p_role_coherence_constraint_v1 import (
    StagePRoleCoherenceConstraintViolationV1)
from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import (
    _case_context, _valid_text)

TOKENIZER = "tokenizer:audit"
DECODER = "decoder:audit"


def _projector(context, pieces, *, authority="authority:a", tokenizer=TOKENIZER,
               decoder=DECODER, grammar="grammar:a", excluded=(0, 1)):
    return StagePConstructionObligationV2TokenProjectorV2(
        controller=StagePConstructionObligationCharacterControllerV1(
            context=context, decoder_identity=decoder),
        token_pieces=pieces, eos_token_id=2, tokenizer_identity=tokenizer,
        decoder_identity=decoder, request_context_identity=context.binding_identity,
        request_authority_identity=authority, grammar_identity=grammar,
        excluded_token_ids=excluded)


def test_ordinary_fast_path_is_exact_at_15998_15999_and_16000():
    context, _, _ = _case_context(); raw = _valid_text(context)
    marker = raw.index('"role_basis":"') + len('"role_basis":"')
    base = _projector(context, {10: "a", 11: "ab", 12: '"', 13: "\\n", 2: ""})
    base.controller.tracker.state_for(range(marker + 1), lambda ids: raw[:marker] + "x")
    string_state = base.controller.tracker._last_state
    pieces = base._all_terminals
    del pieces  # The audit compares against the unchanged feed semantics below.
    token_pieces = {10: "a", 11: "ab", 12: '"', 13: "\\n"}
    for characters in (15998, 15999, 16000):
        state = replace(string_state, characters=characters)
        expected = []
        for token_id, piece in token_pieces.items():
            try:
                state.feed(piece); expected.append(token_id)
            except StagePRoleCoherenceConstraintViolationV1:
                pass
        observed = base._project(
            state, _allowance_for_state(state), initial=False)
        assert observed == tuple(sorted(expected))


def test_every_semantic_cache_domain_dimension_isolated():
    first, _, _ = _case_context(); second, _, _ = _case_context(candidate_text="different")
    pieces = {10: "{", 11: "x", 2: ""}
    projectors = [
        _projector(first, pieces),
        _projector(first, pieces, authority="authority:b"),
        _projector(first, pieces, tokenizer="tokenizer:b"),
        _projector(first, pieces, decoder="decoder:b"),
        _projector(first, pieces, grammar="grammar:b"),
        _projector(first, pieces, excluded=(0, 1, 10)),
        _projector(second, pieces),
    ]
    domains = [item.cache_domain_identity for item in projectors]
    assert len(domains) == len(set(domains))


def test_equivalent_state_rebuild_matches_and_terminal_eos_is_exclusive():
    context, _, _ = _case_context(); raw = _valid_text(context)
    pieces = {10: "a", 11: "\\n", 12: '"', 2: ""}
    marker = raw.index('"role_basis":"') + len('"role_basis":"')
    left = _projector(context, pieces); right = _projector(context, pieces)
    left.allowed_token_ids(range(marker - 1), lambda ids: raw[:len(ids)])
    incremental = left.allowed_token_ids(range(marker), lambda ids: raw[:len(ids)])
    right.controller.tracker.state_for((999,), lambda _: raw[:marker])
    rebuilt = right.allowed_token_ids((), lambda _: raw[:marker])
    assert incremental == rebuilt
    terminal = _projector(context, pieces).allowed_token_ids(
        range(len(raw)), lambda ids: raw[:len(ids)])
    assert terminal.token_ids == (2,) and terminal.receipt.eos_allowed


def test_suffix_callback_rejects_all_history_and_identity_attacks():
    callback = RequestBoundGeneratedSuffixCallbackV1(
        request_identity="request:a", prompt_token_ids=(1, 2, 3),
        project=lambda ids: tuple(ids))
    callback.validate_prompt_once(request_identity="request:a", prompt_token_ids=(1, 2, 3))
    callback.project_generated_suffix(request_identity="request:a", generated_token_ids=(7, 8))
    for request, generated, code in [
        ("request:b", (7, 8), "CROSS_REQUEST"),
        ("request:a", (7,), "NONINCREMENTAL"),
        ("request:a", (7, 9), "NONINCREMENTAL"),
    ]:
        with pytest.raises(ValueError, match=code):
            callback.project_generated_suffix(
                request_identity=request, generated_token_ids=generated)
    with pytest.raises(ValueError, match="PROMPT_SUBSTITUTION"):
        callback.validate_prompt_once(
            request_identity="request:a", prompt_token_ids=(1, 2, 4))
    callback.close()
    with pytest.raises(ValueError, match="STALE_CALLBACK"):
        callback.project_generated_suffix(
            request_identity="request:a", generated_token_ids=(7, 8, 9))
