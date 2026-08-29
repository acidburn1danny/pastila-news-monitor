from __future__ import annotations

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_character_controller_v1 import StagePConstructionObligationCharacterControllerV1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_token_projector_v1 import StagePConstructionObligationV2TokenProjectorV1, StagePTokenProjectionFailureV1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_token_projector_v2 import StagePConstructionObligationV2TokenProjectorV2
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_request_bound_callback_adapter_v1_2_1 import _decode
from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import _case_context, _valid_text

TOKENIZER = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
DECODER = "decoder-bound-by-tokenizer-a91ae3f7"

def _pair(context, pieces):
    def make(kind):
        kwargs = dict(controller=StagePConstructionObligationCharacterControllerV1(
            context=context, decoder_identity=DECODER), token_pieces=pieces,
            eos_token_id=2, tokenizer_identity=TOKENIZER, decoder_identity=DECODER,
            request_context_identity=context.binding_identity,
            excluded_token_ids=(0, 1, 11))
        if kind is StagePConstructionObligationV2TokenProjectorV2:
            kwargs["request_authority_identity"] = "authority:test-case-01"
        return kind(**kwargs)
    return make(StagePConstructionObligationV2TokenProjectorV1), make(StagePConstructionObligationV2TokenProjectorV2)

def _outcome(projector, ids, decode):
    try:
        result = projector.allowed_token_ids(ids, decode)
        return "OK", result.token_ids, result.receipt
    except StagePTokenProjectionFailureV1 as exc:
        return "FAIL", (), exc.receipt


def test_generated_decode_uses_initial_piece_once_then_continuation_pieces():
    context, _, _ = _case_context()
    _, projector = _pair(context, {10: " word", 11: "!", 2: ""})
    projector._bound_initial_token_pieces = {10: "word", 11: "!", 2: ""}
    assert _decode(projector, (10, 10, 11)) == "word word!"

def test_indexed_projection_matches_oracle_across_every_reachable_prefix():
    context, _, _ = _case_context(candidate_text="Țară, știre — «nouă»")
    raw = _valid_text(context)
    pieces = {index + 20: piece for index, piece in enumerate(
        sorted(set(raw + '\\"/bfnrtu0123456789ABCDEFabcdef nulltruefalse')))}
    pieces.update({500: "schema_name", 501: "\\u0219", 502: "Țară", 503: "null", 504: "\ud800", 2: ""})
    oracle, indexed = _pair(context, pieces)
    for length in range(len(raw) + 1):
        decode = lambda ids, length=length: raw[:length]
        assert _outcome(oracle, range(length), decode) == _outcome(indexed, range(length), decode)

def test_terminal_dead_malformed_and_cache_domain_isolation():
    first, _, _ = _case_context(); second, _, _ = _case_context(candidate_text="other")
    raw = _valid_text(first)
    oracle, indexed = _pair(first, {10: "{", 12: "x", 2: ""})
    assert _outcome(oracle, range(len(raw)), lambda ids: raw[:len(ids)]) == _outcome(
        indexed, range(len(raw)), lambda ids: raw[:len(ids)])
    dead_oracle, dead_indexed = _pair(first, {10: "x", 2: ""})
    assert _outcome(dead_oracle, (), lambda _: "") == _outcome(dead_indexed, (), lambda _: "")
    with pytest.raises(StagePTokenProjectionFailureV1):
        indexed.allowed_token_ids((), lambda _: 42)
    _, other = _pair(second, {10: "{", 2: ""})
    assert indexed.cache_domain_identity != other.cache_domain_identity

def test_equivalent_state_cache_ignores_history_but_rejects_decode_mutation():
    context, _, _ = _case_context(); raw = _valid_text(context)
    _, indexed = _pair(context, {10: "a", 12: "\\n", 13: '"', 2: ""})
    marker = raw.index('"role_basis":"') + len('"role_basis":"')
    indexed.allowed_token_ids(range(marker), lambda ids: raw[:len(ids)])
    misses = indexed.statistics.cache_misses
    indexed.allowed_token_ids(range(marker), lambda ids: raw[:len(ids)])
    assert indexed.statistics.cache_hits == 1 and indexed.statistics.cache_misses == misses
    indexed.controller.tracker.state_for((999,), lambda _: raw[:marker])
    with pytest.raises(StagePTokenProjectionFailureV1):
        indexed.allowed_token_ids((999,), lambda _: raw[:marker + 1])
