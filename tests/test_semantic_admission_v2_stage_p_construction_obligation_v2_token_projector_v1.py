from __future__ import annotations

import json

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_character_controller_v1 import StagePConstructionObligationCharacterControllerV1
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_token_projector_v1 import (
    StagePConstructionObligationV2TokenProjectorV1,
    StagePTokenProjectionFailureV1,
    canonical_token_projection_receipt_bytes_v1,
)
from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import _case_context, _valid_text


TOKENIZER = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
DECODER = "decoder-bound-by-tokenizer-a91ae3f7"


def _projector(context, pieces):
    controller = StagePConstructionObligationCharacterControllerV1(
        context=context, decoder_identity=DECODER)
    return StagePConstructionObligationV2TokenProjectorV1(
        controller=controller, token_pieces=pieces, eos_token_id=2,
        tokenizer_identity=TOKENIZER, decoder_identity=DECODER,
        request_context_identity=context.binding_identity,
        excluded_token_ids=(0, 1, 11))


def test_prefix_unicode_romanian_punctuation_and_json_escaping() -> None:
    context, _, _ = _case_context(candidate_text="Țară, știre — «nouă»")
    raw = _valid_text(context)
    marker = '"role_basis":"'
    prefix = raw[:raw.index(marker) + len(marker)]
    pieces = {10: "țară", 12: "ă, — «»", 13: "\\n", 14: '"', 15: "\ud800", 2: ""}
    projector = _projector(context, pieces)
    result = projector.allowed_token_ids(range(len(prefix)), lambda ids: prefix[:len(ids)])
    assert result.token_ids == (10, 12, 13)
    assert result.receipt.result == "TOKENIZATION_CONTINUABLE"
    assert json.loads(canonical_token_projection_receipt_bytes_v1(result.receipt))[
        "request_context_identity"] == context.binding_identity


def test_terminal_admits_only_eos_and_prefix_never_admits_eos() -> None:
    context, _, _ = _case_context(); raw = _valid_text(context)
    projector = _projector(context, {10: "{", 12: "x", 2: ""})
    prefix = projector.allowed_token_ids([], lambda _: "")
    assert 2 not in prefix.token_ids
    terminal = projector.allowed_token_ids(range(len(raw)), lambda ids: raw[:len(ids)])
    assert terminal.token_ids == (2,)
    assert terminal.receipt.eos_allowed is True


def test_incremental_and_full_rebuild_projection_are_equivalent() -> None:
    context, _, _ = _case_context(); raw = _valid_text(context)
    split = raw.index('"role_basis":"') + len('"role_basis":"')
    pieces = {10: "a", 12: "\\u0219", 13: '"', 2: ""}
    incremental = _projector(context, pieces)
    incremental.allowed_token_ids(range(split - 1), lambda ids: raw[:len(ids)])
    left = incremental.allowed_token_ids(range(split), lambda ids: raw[:len(ids)])
    rebuilt = _projector(context, pieces)
    rebuilt.allowed_token_ids((999,), lambda _: raw[:split])
    right = rebuilt.allowed_token_ids((), lambda _: raw[:split])
    assert left.token_ids == right.token_ids
    assert left.receipt.dfa_mode == right.receipt.dfa_mode


def test_context_decoder_and_cache_identity_are_exact_and_isolated() -> None:
    first, _, _ = _case_context(candidate_text="prima cerere")
    second, _, _ = _case_context(candidate_text="a doua cerere")
    with pytest.raises(ValueError, match="REQUEST_CONTEXT_IDENTITY_MISMATCH"):
        StagePConstructionObligationV2TokenProjectorV1(
            controller=StagePConstructionObligationCharacterControllerV1(
                context=first, decoder_identity=DECODER), token_pieces={10: "{"},
            eos_token_id=2, tokenizer_identity=TOKENIZER, decoder_identity=DECODER,
            request_context_identity=second.binding_identity)
    one = _projector(first, {10: "{"}); two = _projector(second, {10: "{"})
    one.allowed_token_ids([], lambda _: ""); two.allowed_token_ids([], lambda _: "")
    assert next(iter(one._cache))[0] == first.binding_identity
    assert next(iter(two._cache))[0] == second.binding_identity
    assert next(iter(one._cache)) != next(iter(two._cache))


def test_dead_malformed_conflicting_or_identity_unbound_inputs_fail_closed() -> None:
    context, _, _ = _case_context()
    projector = _projector(context, {10: "x", 11: "", 2: ""})
    with pytest.raises(StagePTokenProjectionFailureV1) as dead:
        projector.allowed_token_ids([], lambda _: "")
    assert dead.value.receipt.reason_code == "TOKENIZATION_DEAD_NO_VALID_TOKEN"
    assert dead.value.receipt.legal_token_count == 0
    with pytest.raises(StagePTokenProjectionFailureV1) as malformed:
        projector.allowed_token_ids([], lambda _: 42)
    assert malformed.value.receipt.result == "FAIL_CLOSED"
    projector.allowed_token_ids([], lambda _: "") if False else None
    projector.controller.tracker.state_for((5,), lambda _: "{")
    with pytest.raises(StagePTokenProjectionFailureV1):
        projector.allowed_token_ids((5,), lambda _: "[")
