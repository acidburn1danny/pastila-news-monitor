from __future__ import annotations

from dataclasses import replace

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_character_controller_v1 import (
    CharacterAllowanceKindV1, StagePCharacterLivenessErrorV1,
    StagePConstructionObligationCharacterControllerV1,
    canonical_character_liveness_receipt_bytes_v1,
)
from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import (
    _case_context, _valid_text,
)


def _decoder(characters):
    return lambda ids: "".join(characters[index] for index in ids)


def _result_for_prefix(context, raw, prefix_length):
    characters = list(raw)
    controller = StagePConstructionObligationCharacterControllerV1(
        context=context, decoder_identity="fake-character-v1")
    return controller.allowed(list(range(prefix_length)), _decoder(characters))


def test_every_case01_fixture_prefix_permits_exact_next_character_and_terminal():
    context, _, _ = _case_context(); raw = _valid_text(context); characters = list(raw)
    controller = StagePConstructionObligationCharacterControllerV1(
        context=context, decoder_identity="fake-character-v1")
    decode = _decoder(characters)
    for length, character in enumerate(characters):
        result = controller.allowed(list(range(length)), decode)
        assert result.allowance.permits(character)
        assert result.receipt.liveness == "LIVE"
        assert result.receipt.context_identity == context.binding_identity
    terminal = controller.allowed(list(range(len(characters))), decode)
    assert terminal.allowance.kind is CharacterAllowanceKindV1.TERMINAL
    assert terminal.receipt.dfa_mode == "TERMINAL"


def test_json_string_descriptor_distinguishes_empty_and_nonempty_closure():
    context, _, _ = _case_context(); raw = _valid_text(context)
    marker = '"role_basis":"'; start = raw.index(marker) + len(marker)
    empty = _result_for_prefix(context, raw, start)
    assert empty.allowance.kind is CharacterAllowanceKindV1.JSON_STRING_BODY
    assert empty.allowance.closing_quote_allowed is False
    assert empty.allowance.permits("a") and empty.allowance.permits("\\")
    assert not empty.allowance.permits('"') and not empty.allowance.permits("\n")
    assert not empty.allowance.permits("\ud800")
    nonempty = _result_for_prefix(context, raw, start + 1)
    assert nonempty.allowance.closing_quote_allowed is True
    assert nonempty.allowance.permits('"')


def test_reference_receipt_binds_field_submode_and_forces_object_start():
    context, _, _ = _case_context(); raw = _valid_text(context)
    marker = '"candidate_span_ref":'; position = raw.index(marker) + len(marker)
    result = _result_for_prefix(context, raw, position)
    assert result.allowance.kind is CharacterAllowanceKindV1.FINITE
    assert result.allowance.finite_characters == ("{",)
    assert result.receipt.reference_field == "candidate_span_ref"
    assert result.receipt.reference_mode == "INITIAL"


def test_semantically_invalid_early_entry_close_is_filtered_from_finite_set():
    context, _, _ = _case_context(); raw = _valid_text(context)
    separator = '},{"entry_id":"P2"'; position = raw.index(separator) + 1
    result = _result_for_prefix(context, raw, position)
    assert result.receipt.dfa_mode == "AFTER_ENTRY"
    assert result.allowance.permits(",")
    assert not result.allowance.permits("]")


def test_receipts_are_deterministic_for_same_context_decoder_and_prefix():
    context, _, _ = _case_context(); raw = _valid_text(context); position = 777
    first = _result_for_prefix(context, raw, position)
    second = _result_for_prefix(context, raw, position)
    assert first.allowance == second.allowance
    assert first.receipt == second.receipt
    first_bytes = canonical_character_liveness_receipt_bytes_v1(first.receipt)
    assert first_bytes == canonical_character_liveness_receipt_bytes_v1(second.receipt)
    assert first.prefix.decoded.encode("utf-8") not in first_bytes


def test_unknown_dead_state_emits_typed_fail_closed_liveness_receipt():
    context, _, _ = _case_context()
    controller = StagePConstructionObligationCharacterControllerV1(
        context=context, decoder_identity="fixture-v1")
    controller.tracker._last_state = replace(controller.tracker._last_state, mode="UNKNOWN")
    with pytest.raises(StagePCharacterLivenessErrorV1) as caught:
        controller.allowed([], lambda ids: "")
    receipt = caught.value.receipt
    assert receipt.liveness == "FAIL_CLOSED"
    assert receipt.reason_code == "STAGE_P_CHARACTER_ALLOWED_SET_EMPTY"
    assert receipt.finite_character_count == 0
