from __future__ import annotations

import hashlib

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_constraint_v2 import (
    StagePConstructionObligationConstraintStateV2,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_incremental_tracker_v2 import (
    StagePConstructionObligationIncrementalTrackerV2,
    StagePConstructionObligationTrackerViolationV2,
)
from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import (
    _case_context, _valid_text,
)


def _tokens(text, widths=(1, 2, 5, 3, 11)):
    values = []; offset = 0; index = 0
    while offset < len(text):
        width = widths[index % len(widths)]
        values.append(text[offset:offset + width]); offset += width; index += 1
    return values


def test_incremental_every_prefix_equals_context_bound_full_rebuild():
    context, _, _ = _case_context(); raw = _valid_text(context); pieces = _tokens(raw)
    tracker = StagePConstructionObligationIncrementalTrackerV2(
        context=context, decoder_identity="fake-character-chunks-v1")
    decode = lambda ids: "".join(pieces[item] for item in ids)
    ids = []
    for index in range(len(pieces)):
        ids.append(index)
        result = tracker.state_for(ids, decode)
        expected = StagePConstructionObligationConstraintStateV2.for_context(context).feed(
            decode(ids))
        assert result.state == expected
        assert result.path == "INCREMENTAL"
        assert result.context_identity == context.binding_identity
        assert result.decoder_identity == "fake-character-chunks-v1"
        assert result.decoded_sha256 == hashlib.sha256(result.decoded.encode()).hexdigest()
    assert result.state.terminal
    assert tracker.incremental_steps == len(pieces) and tracker.rebuild_steps == 0


def test_backtrack_and_divergent_token_prefix_take_full_rebuild_then_resume():
    context, _, _ = _case_context(); raw = _valid_text(context)
    tracker = StagePConstructionObligationIncrementalTrackerV2(
        context=context, decoder_identity="fake-v1")
    pieces = {0: raw[:7], 1: raw[7:14], 2: raw[7:14], 3: raw[14:21]}
    decode = lambda ids: "".join(pieces[item] for item in ids)
    tracker.state_for([0, 1, 3], decode)
    backtracked = tracker.state_for([0, 1], decode)
    assert backtracked.path == "FULL_REBUILD"
    divergent = tracker.state_for([0, 2], decode)
    assert divergent.path == "FULL_REBUILD"
    resumed = tracker.state_for([0, 2, 3], decode)
    assert resumed.path == "INCREMENTAL"
    assert tracker.rebuild_steps == 2


def test_prefix_unstable_decode_rebuilds_from_same_context():
    context, _, _ = _case_context(); raw = _valid_text(context)
    tracker = StagePConstructionObligationIncrementalTrackerV2(
        context=context, decoder_identity="prefix-unstable-fixture-v1")
    first = tracker.state_for([1], lambda ids: raw[:10])
    assert first.path == "INCREMENTAL"
    second = tracker.state_for([1, 2], lambda ids: raw[:10] if len(ids) == 1 else raw[:9])
    assert second.path == "FULL_REBUILD"
    assert second.state == StagePConstructionObligationConstraintStateV2.for_context(
        context).feed(raw[:9])


def test_identical_ids_decode_instability_and_non_string_fail_explicitly():
    context, _, _ = _case_context(); raw = _valid_text(context)
    tracker = StagePConstructionObligationIncrementalTrackerV2(
        context=context, decoder_identity="fixture-v1")
    tracker.state_for([1], lambda ids: raw[:10])
    with pytest.raises(StagePConstructionObligationTrackerViolationV2,
                       match="DECODE_INSTABILITY_FOR_IDENTICAL_TOKEN_IDS"):
        tracker.state_for([1], lambda ids: raw[:11])
    fresh = StagePConstructionObligationIncrementalTrackerV2(
        context=context, decoder_identity="fixture-v1")
    with pytest.raises(StagePConstructionObligationTrackerViolationV2,
                       match="DECODE_OUTPUT_NOT_STRING"):
        fresh.state_for([], lambda ids: b"not text")


def test_context_and_decoder_identity_are_mandatory_and_isolated():
    first, _, _ = _case_context()
    second, _, _ = _case_context(candidate_text="x" * 134, authority_text="y" * 122)
    with pytest.raises(ValueError, match="DECODER_IDENTITY_REQUIRED"):
        StagePConstructionObligationIncrementalTrackerV2(
            context=first, decoder_identity="")
    left = StagePConstructionObligationIncrementalTrackerV2(
        context=first, decoder_identity="same-decoder")
    right = StagePConstructionObligationIncrementalTrackerV2(
        context=second, decoder_identity="same-decoder")
    assert left.context.binding_identity != right.context.binding_identity
    assert left._last_state.context != right._last_state.context
