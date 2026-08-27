import dataclasses
import hashlib

import pytest

from pastila_scout.semantic_admission_v2.immutable_source_span_reference_v1 import (
    ImmutableUtf8SourceV1,
    SourceRoleV1,
)
from pastila_scout.semantic_admission_v2.stage_p_phase2_character_controller_v1 import (
    AUTHORITY_DFA_IDENTITY,
    COMMITMENT_DFA_IDENTITY,
    CharacterAllowanceKindV1,
    Phase2AuditLaneV1,
    Phase2CharacterControllerV1,
    Phase2CharacterLivenessErrorV1,
    _allowance_for_state,
    canonical_phase2_liveness_receipt_bytes_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_phase2_character_dfa_v1 import (
    AuthorityReconciliationCharacterDfaV1,
    CommitmentSpanAuditCharacterDfaV1,
)
from pastila_scout.semantic_admission_v2.stage_p_source_reference_constraint_v1 import (
    ReferenceFieldV1,
    SourceReferenceConstraintContextV1,
    canonical_reference_json_v1,
)


DECODER_ID = "d" * 64


def _context():
    return SourceReferenceConstraintContextV1.bind(
        candidate=ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.CANDIDATE, data="candidat ă".encode()
        ),
        factual_authority=ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.FACTUAL_AUTHORITY, data="autoritate î".encode()
        ),
    )


def _commitment_text():
    return (
        '{"schema_name":"pastila-semantic-admission-v2-stage-p-commitment-span-audit-response",'
        '"schema_version":"1.0.0-evaluation-candidate.1",'
        '"audit_kind":"COMMITMENT_SPAN_AUDIT","records":['
        '{"entry_id":"P1","decision":"SPAN_SUPPORTS_COMPLETE_COMMITMENT",'
        '"assertion_checked":true,"presupposition_checked":true,'
        '"entailment_checked":true,"necessary_implication_checked":true,'
        '"reason_code":null,"basis":"verificat ă"}]}'
    )


def _authority_text(context, *, unsupported=False):
    if not unsupported:
        ref = canonical_reference_json_v1(
            context=context, field=ReferenceFieldV1.AUTHORITY_SUPPORT,
            start_utf8=0, end_utf8=1
        )
        record = (
            '{"entry_id":"P1","full_authority_compared":true,'
            '"decision":"GOVERNED_SUPPORTED","authority_support_ref":%s,'
            '"event_axis":"MATCH","modality_axis":"MATCH","timing_axis":"MATCH",'
            '"unsupported_finding_ids":[],"basis":"verificat"}' % ref
        )
        findings = ""
    else:
        ref = canonical_reference_json_v1(
            context=context, field=ReferenceFieldV1.CANDIDATE_SPAN,
            start_utf8=0, end_utf8=1
        )
        record = (
            '{"entry_id":"P1","full_authority_compared":true,'
            '"decision":"UNSUPPORTED_NEW_OR_MUTATED_PROPOSITION",'
            '"authority_support_ref":null,"event_axis":"MATCH",'
            '"modality_axis":"MUTATION","timing_axis":"MATCH",'
            '"unsupported_finding_ids":["F1"],"basis":"verificat"}'
        )
        findings = (
            '{"finding_id":"F1","entry_id":"P1","candidate_proposition_ref":%s,'
            '"reason_code":"FSEM_UNSUPPORTED_CAUSALITY","reason_status":"DECISIVE",'
            '"basis":"verificat"}' % ref
        )
    return (
        '{"schema_name":"pastila-semantic-admission-v2-stage-p-authority-reconciliation-audit-response",'
        '"schema_version":"1.0.0-evaluation-candidate.1",'
        '"audit_kind":"AUTHORITY_RECONCILIATION_AUDIT","records":[' + record
        + '],"unsupported_findings":[' + findings + "]}"
    )


@pytest.mark.parametrize("kind", ("commitment", "supported", "unsupported"))
def test_character_allowance_keeps_every_canonical_character_live(kind):
    context = _context()
    if kind == "commitment":
        state = CommitmentSpanAuditCharacterDfaV1.for_entries(("P1",))
        text = _commitment_text()
    else:
        state = AuthorityReconciliationCharacterDfaV1.for_request(
            entry_ids=("P1",), context=context
        )
        text = _authority_text(context, unsupported=kind == "unsupported")
    for character in text:
        allowance = _allowance_for_state(state)
        assert allowance.permits(character), (state.mode, character, state.remaining)
        state = state.feed(character)
    assert state.terminal
    assert _allowance_for_state(state).kind is CharacterAllowanceKindV1.TERMINAL


@pytest.mark.parametrize("lane", tuple(Phase2AuditLaneV1))
def test_controller_receipt_is_deterministic_identity_bound_and_canonical(lane):
    context = _context()
    text = _commitment_text() if lane is Phase2AuditLaneV1.COMMITMENT_SPAN else _authority_text(context)
    kwargs = dict(
        lane=lane, expected_entry_ids=("P1",), decoder_identity=DECODER_ID,
        source_context=context if lane is Phase2AuditLaneV1.AUTHORITY_RECONCILIATION else None,
    )
    first = Phase2CharacterControllerV1(**kwargs)
    second = Phase2CharacterControllerV1(**kwargs)
    decoded = {(1,): text[:20], (1, 2): text}
    first.allowed((1,), lambda ids: decoded[tuple(ids)])
    result = first.allowed((1, 2), lambda ids: decoded[tuple(ids)])
    duplicate = second.allowed((1, 2), lambda ids: decoded[tuple(ids)])
    expected_grammar = (
        COMMITMENT_DFA_IDENTITY if lane is Phase2AuditLaneV1.COMMITMENT_SPAN
        else AUTHORITY_DFA_IDENTITY
    )
    assert result.receipt.grammar_identity == expected_grammar
    assert result.receipt.request_context_identity == duplicate.receipt.request_context_identity
    assert result.receipt.tracker_path == "INCREMENTAL"
    assert result.receipt.liveness == "LIVE"
    assert result.allowance.kind is CharacterAllowanceKindV1.TERMINAL
    assert canonical_phase2_liveness_receipt_bytes_v1(result.receipt).endswith(b"\n")
    assert canonical_phase2_liveness_receipt_bytes_v1(result.receipt) == (
        canonical_phase2_liveness_receipt_bytes_v1(result.receipt)
    )


def test_controller_records_full_rebuild_path_without_tokenizer_assumptions():
    text = _commitment_text()
    controller = Phase2CharacterControllerV1(
        lane=Phase2AuditLaneV1.COMMITMENT_SPAN,
        expected_entry_ids=("P1",), decoder_identity=DECODER_ID,
    )
    values = {(1,): text[:10], (9,): text}
    controller.allowed((1,), lambda ids: values[tuple(ids)])
    rebuilt = controller.allowed((9,), lambda ids: values[tuple(ids)])
    assert rebuilt.receipt.tracker_path == "FULL_REBUILD"
    assert rebuilt.receipt.decoded_sha256 == hashlib.sha256(text.encode()).hexdigest()


def test_unknown_state_fails_closed_with_typed_receipt():
    controller = Phase2CharacterControllerV1(
        lane=Phase2AuditLaneV1.COMMITMENT_SPAN,
        expected_entry_ids=("P1",), decoder_identity=DECODER_ID,
    )
    controller.tracker._last_state = dataclasses.replace(
        controller.tracker._last_state, mode="UNKNOWN", remaining=""
    )
    controller.tracker._last_ids = (1,)
    controller.tracker._last_decoded = "x"
    with pytest.raises(Phase2CharacterLivenessErrorV1) as failure:
        controller.allowed((1,), lambda _: "x")
    assert failure.value.receipt.liveness == "FAIL_CLOSED"
    assert failure.value.receipt.reason_code == "PHASE2_CHARACTER_ALLOWED_SET_EMPTY"


def test_lane_context_and_decoder_invariants_are_fail_closed():
    context = _context()
    with pytest.raises(ValueError, match="SOURCE_CONTEXT_FORBIDDEN"):
        Phase2CharacterControllerV1(
            lane=Phase2AuditLaneV1.COMMITMENT_SPAN, expected_entry_ids=("P1",),
            decoder_identity=DECODER_ID, source_context=context
        )
    with pytest.raises(ValueError, match="SOURCE_CONTEXT_REQUIRED"):
        Phase2CharacterControllerV1(
            lane=Phase2AuditLaneV1.AUTHORITY_RECONCILIATION,
            expected_entry_ids=("P1",), decoder_identity=DECODER_ID
        )
    with pytest.raises(ValueError, match="DECODER_IDENTITY_INVALID"):
        Phase2CharacterControllerV1(
            lane=Phase2AuditLaneV1.COMMITMENT_SPAN,
            expected_entry_ids=("P1",), decoder_identity="not-a-hash"
        )
