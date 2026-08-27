from __future__ import annotations

import pytest

from pastila_scout.semantic_admission_v2.immutable_source_span_reference_v1 import (
    ImmutableUtf8SourceV1,
    SourceRoleV1,
)
from pastila_scout.semantic_admission_v2.stage_p_constraint_v1 import (
    StagePConstraintViolationV1,
)
from pastila_scout.semantic_admission_v2.stage_p_phase2_character_controller_v1 import (
    Phase2AuditLaneV1,
    Phase2CharacterControllerV1,
)
from pastila_scout.semantic_admission_v2.stage_p_phase2_token_projector_v1 import (
    Phase2TokenProjectionLivenessErrorV1,
    Phase2TokenProjectorV1,
    canonical_phase2_token_projection_receipt_bytes_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_source_reference_constraint_v1 import (
    ReferenceFieldV1,
    SourceReferenceConstraintContextV1,
    canonical_reference_json_v1,
)

IDENTITY = "1" * 64
EOS = 999


def _context():
    return SourceReferenceConstraintContextV1.bind(
        candidate=ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.CANDIDATE, data="candidat ă".encode()),
        factual_authority=ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.FACTUAL_AUTHORITY, data="știre înghețată".encode()),
    )


def _commitment(basis="verificat ă"):
    return (
        '{"schema_name":"pastila-semantic-admission-v2-stage-p-commitment-span-audit-response",'
        '"schema_version":"1.0.0-evaluation-candidate.1",'
        '"audit_kind":"COMMITMENT_SPAN_AUDIT","records":['
        '{"entry_id":"P1","decision":"SPAN_SUPPORTS_COMPLETE_COMMITMENT",'
        '"assertion_checked":true,"presupposition_checked":true,'
        '"entailment_checked":true,"necessary_implication_checked":true,'
        f'"reason_code":null,"basis":"{basis}"}}]}}'
    )


def _authority(context):
    support = canonical_reference_json_v1(
        context=context, field=ReferenceFieldV1.AUTHORITY_SUPPORT,
        start_utf8=0, end_utf8=context.factual_authority.byte_length,
    )
    return (
        '{"schema_name":"pastila-semantic-admission-v2-stage-p-authority-reconciliation-audit-response",'
        '"schema_version":"1.0.0-evaluation-candidate.1",'
        '"audit_kind":"AUTHORITY_RECONCILIATION_AUDIT","records":['
        '{"entry_id":"P1","full_authority_compared":true,"decision":"GOVERNED_SUPPORTED",'
        f'"authority_support_ref":{support},"event_axis":"MATCH",'
        '"modality_axis":"MATCH","timing_axis":"MATCH",'
        '"unsupported_finding_ids":[],"basis":"verificat ș"}],"unsupported_findings":[]}'
    )


def _projector(lane, pieces, *, context=None, excluded=()):
    controller = Phase2CharacterControllerV1(
        lane=lane, expected_entry_ids=("P1",), decoder_identity=IDENTITY,
        source_context=context,
    )
    return Phase2TokenProjectorV1(
        controller=controller, token_pieces=pieces, eos_token_id=EOS,
        tokenizer_identity="sha256:synthetic-phase2-tokenizer-v1",
        decoder_identity=IDENTITY, excluded_token_ids=excluded,
    )


def _oracle(projector, prefix, pieces):
    state = projector.controller.tracker.factory().feed(prefix)
    allowed = []
    for token_id, piece in pieces.items():
        if token_id == EOS or not piece or "\ufffd" in piece:
            continue
        try:
            state.feed(piece)
        except StagePConstraintViolationV1:
            pass
        else:
            allowed.append(token_id)
    return (EOS,) if state.terminal else tuple(sorted(allowed))


@pytest.mark.parametrize("lane", list(Phase2AuditLaneV1))
def test_every_terminal_and_prefix_matches_full_rebuild_oracle(lane):
    context = _context()
    text = _commitment() if lane is Phase2AuditLaneV1.COMMITMENT_SPAN else _authority(context)
    # All terminals plus overlapping, Unicode, escaping, invalid, empty and multi-char pieces.
    alphabet = sorted(set(text))
    pieces = {index: piece for index, piece in enumerate(
        alphabet + ["ve", "ver", "ă", "ș", "\\n", '"', "", "\ufffd", "never-legal\x00"]
    )}
    projector = _projector(
        lane, pieces,
        context=context if lane is Phase2AuditLaneV1.AUTHORITY_RECONCILIATION else None,
    )
    decode = lambda ids: text[:len(ids)]
    # Exercise every character prefix, sequentially, which also proves every terminal edge.
    for length in range(len(text) + 1):
        actual = projector.allowed_token_ids(tuple(range(length)), decode)
        assert actual == _oracle(projector, text[:length], pieces)
        assert (EOS in actual) == (length == len(text))


def test_incremental_and_full_rebuild_projection_are_identical():
    text = _commitment()
    pieces = {index: piece for index, piece in enumerate(sorted(set(text)) + ["ver", "ă"])}
    incremental = _projector(Phase2AuditLaneV1.COMMITMENT_SPAN, pieces)
    decode = lambda ids: text[:len(ids)]
    for length in (0, 1, 17, len(text) // 2, len(text)):
        left = incremental.project(tuple(range(length)), decode)
        rebuilt = _projector(Phase2AuditLaneV1.COMMITMENT_SPAN, pieces)
        # Seed an incompatible token prefix so the target must take FULL_REBUILD.
        rebuilt.controller.tracker._last_ids = (100_000,)
        rebuilt.controller.tracker._last_decoded = ""
        right = rebuilt.project(tuple(range(length)), decode)
        assert left.allowed_token_ids == right.allowed_token_ids
        assert left.receipt.allowed_token_set_sha256 == right.receipt.allowed_token_set_sha256


def test_request_bound_reference_context_changes_identity_and_legal_coordinates():
    short = _context()
    long = SourceReferenceConstraintContextV1.bind(
        candidate=ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.CANDIDATE, data="candidat ă".encode()),
        factual_authority=ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.FACTUAL_AUTHORITY, data=("ș" * 15).encode()),
    )
    pieces = {number: str(number) for number in range(10)} | {
        20: ",", 21: "}", 22: str(short.factual_authority.byte_length),
        23: str(long.factual_authority.byte_length),
    }
    left = _projector(Phase2AuditLaneV1.AUTHORITY_RECONCILIATION, pieces, context=short)
    right = _projector(Phase2AuditLaneV1.AUTHORITY_RECONCILIATION, pieces, context=long)
    assert left.controller.request_context_identity != right.controller.request_context_identity
    left_prefix = _authority(short).split('"end_utf8":', 1)[0] + '"end_utf8":'
    right_prefix = _authority(long).split('"end_utf8":', 1)[0] + '"end_utf8":'
    assert left.allowed_token_ids(tuple(range(len(left_prefix))), lambda _: left_prefix) != ()
    assert right.allowed_token_ids(tuple(range(len(right_prefix))), lambda _: right_prefix) != ()


def test_fail_closed_no_legal_token_has_canonical_identity_bound_receipt():
    projector = _projector(Phase2AuditLaneV1.COMMITMENT_SPAN, {0: "!", 1: "", 2: "\ufffd"})
    with pytest.raises(Phase2TokenProjectionLivenessErrorV1) as raised:
        projector.project((), lambda _: "")
    receipt = raised.value.receipt
    assert receipt.liveness == "TOKENIZATION_DEAD_NO_VALID_TOKEN"
    assert receipt.reason_code == "PHASE2_TOKEN_ALLOWED_SET_EMPTY"
    assert receipt.allowed_token_count == 0
    assert receipt.eos_disposition == "REJECTED_NONTERMINAL"
    assert receipt.tokenizer_identity == "sha256:synthetic-phase2-tokenizer-v1"
    assert canonical_phase2_token_projection_receipt_bytes_v1(receipt).endswith(b"\n")


def test_identity_and_exclusion_boundaries_fail_closed():
    with pytest.raises(ValueError, match="TOKENIZER_IDENTITY"):
        _projector(Phase2AuditLaneV1.COMMITMENT_SPAN, {0: "{"}).__class__(
            controller=_projector(Phase2AuditLaneV1.COMMITMENT_SPAN, {0: "{"}).controller,
            token_pieces={0: "{"}, eos_token_id=EOS, tokenizer_identity="",
            decoder_identity=IDENTITY,
        )
    projector = _projector(Phase2AuditLaneV1.COMMITMENT_SPAN, {0: "{", 1: "{"}, excluded=(1,))
    assert projector.allowed_token_ids((), lambda _: "") == (0,)
