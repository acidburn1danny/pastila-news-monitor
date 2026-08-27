import itertools
import json

import pytest

from pastila_scout.semantic_admission_v2.immutable_source_span_reference_v1 import (
    ImmutableUtf8SourceV1,
    SourceRoleV1,
)
from pastila_scout.semantic_admission_v2.stage_p_constraint_v1 import (
    StagePConstraintViolationV1,
)
from pastila_scout.semantic_admission_v2.stage_p_phase2_audit_contracts_v1 import (
    AuthorityReconciliationAuditResponseV1,
    CommitmentSpanAuditResponseV1,
)
from pastila_scout.semantic_admission_v2.stage_p_phase2_character_dfa_v1 import (
    AUTHORITY_DECISIONS,
    AXES,
    COMMITMENT_DECISIONS,
    COMMITMENT_REASONS,
    AuthorityReconciliationCharacterDfaV1,
    CommitmentSpanAuditCharacterDfaV1,
    Phase2IncrementalCharacterTrackerV1,
)
from pastila_scout.semantic_admission_v2.stage_p_source_reference_constraint_v1 import (
    ReferenceFieldV1,
    SourceReferenceConstraintContextV1,
    canonical_reference_json_v1,
)


def _context(candidate: bytes = b"ab", authority: bytes = b"cd"):
    return SourceReferenceConstraintContextV1.bind(
        candidate=ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.CANDIDATE, data=candidate
        ),
        factual_authority=ImmutableUtf8SourceV1.bind(
            role=SourceRoleV1.FACTUAL_AUTHORITY, data=authority
        ),
    )


def _commitment(records):
    body = []
    for entry_id, decision in records:
        body.append(
            '{"entry_id":"%s","decision":"%s",'
            '"assertion_checked":true,"presupposition_checked":true,'
            '"entailment_checked":true,"necessary_implication_checked":true,'
            '"reason_code":%s,"basis":"checked"}'
            % (entry_id, decision, COMMITMENT_REASONS[decision])
        )
    return (
        '{"schema_name":"pastila-semantic-admission-v2-stage-p-commitment-span-audit-response",'
        '"schema_version":"1.0.0-evaluation-candidate.1",'
        '"audit_kind":"COMMITMENT_SPAN_AUDIT","records":['
        + ",".join(body)
        + "]}"
    )


def _authority_record(entry_id, decision, axes, support, finding_ids=()):
    links = json.dumps(list(finding_ids), separators=(",", ":"))
    return (
        '{"entry_id":"%s","full_authority_compared":true,"decision":"%s",'
        '"authority_support_ref":%s,"event_axis":"%s","modality_axis":"%s",'
        '"timing_axis":"%s","unsupported_finding_ids":%s,"basis":"checked"}'
        % (entry_id, decision, support, *axes, links)
    )


def _finding(context, finding_id, entry_id, status="DECISIVE"):
    ref = canonical_reference_json_v1(
        context=context,
        field=ReferenceFieldV1.CANDIDATE_SPAN,
        start_utf8=0,
        end_utf8=1,
    )
    return (
        '{"finding_id":"%s","entry_id":"%s","candidate_proposition_ref":%s,'
        '"reason_code":"FSEM_UNSUPPORTED_CAUSALITY","reason_status":"%s",'
        '"basis":"checked"}' % (finding_id, entry_id, ref, status)
    )


def _authority(records, findings=()):
    return (
        '{"schema_name":"pastila-semantic-admission-v2-stage-p-authority-reconciliation-audit-response",'
        '"schema_version":"1.0.0-evaluation-candidate.1",'
        '"audit_kind":"AUTHORITY_RECONCILIATION_AUDIT","records":['
        + ",".join(records)
        + '],"unsupported_findings":['
        + ",".join(findings)
        + "]}"
    )


@pytest.mark.parametrize("decision", COMMITMENT_DECISIONS)
def test_commitment_dfa_accepts_each_decision_and_strict_contract(decision):
    text = _commitment((("P1", decision),))
    state = CommitmentSpanAuditCharacterDfaV1.for_entries(("P1",)).feed(text)
    assert state.terminal
    assert CommitmentSpanAuditResponseV1.model_validate_json(text).records[0].entry_id == "P1"


def test_commitment_dfa_is_request_bound_and_rejects_trailing_bytes():
    text = _commitment((("P1", COMMITMENT_DECISIONS[0]), ("P2", COMMITMENT_DECISIONS[1])))
    assert CommitmentSpanAuditCharacterDfaV1.for_entries(("P1", "P2")).feed(text).terminal
    with pytest.raises(StagePConstraintViolationV1):
        CommitmentSpanAuditCharacterDfaV1.for_entries(("P2", "P1")).feed(text)
    with pytest.raises(StagePConstraintViolationV1):
        CommitmentSpanAuditCharacterDfaV1.for_entries(("P1", "P2")).feed(text + " ")


@pytest.mark.parametrize(
    ("decision", "axes"),
    [
        ("GOVERNED_SUPPORTED", ("MATCH", "MATCH", "MATCH")),
        ("NOT_A_REAL_WORLD_COMMITMENT", ("NOT_APPLICABLE",) * 3),
    ]
    + [
        ("UNSUPPORTED_NEW_OR_MUTATED_PROPOSITION", values)
        for values in itertools.product(AXES[:3], repeat=3)
    ]
    + [
        ("UNRESOLVED_FAIL_CLOSED", values)
        for values in itertools.product(AXES, repeat=3)
        if "UNRESOLVED" in values
    ],
)
def test_authority_dfa_exhaustive_small_decision_axis_language(decision, axes):
    context = _context()
    if decision == "GOVERNED_SUPPORTED":
        support = canonical_reference_json_v1(
            context=context,
            field=ReferenceFieldV1.AUTHORITY_SUPPORT,
            start_utf8=0,
            end_utf8=1,
        )
        ids = ()
        findings = ()
    elif decision == "UNSUPPORTED_NEW_OR_MUTATED_PROPOSITION":
        support = "null"
        ids = ("F1",)
        findings = (_finding(context, "F1", "P1"),)
    else:
        support = "null"
        ids = ()
        findings = ()
    text = _authority(
        (_authority_record("P1", decision, axes, support, ids),), findings
    )
    state = AuthorityReconciliationCharacterDfaV1.for_request(
        entry_ids=("P1",), context=context
    ).feed(text)
    assert state.terminal
    assert AuthorityReconciliationAuditResponseV1.model_validate_json(text).records[0].entry_id == "P1"


def test_authority_dfa_accepts_exhaustive_valid_small_reference_ranges():
    context = _context(candidate="ăx".encode(), authority="îy".encode())
    source = context.factual_authority
    for start, end in itertools.combinations(source.utf8_boundaries, 2):
        support = canonical_reference_json_v1(
            context=context,
            field=ReferenceFieldV1.AUTHORITY_SUPPORT,
            start_utf8=start,
            end_utf8=end,
        )
        text = _authority((
            _authority_record("P1", "GOVERNED_SUPPORTED", ("MATCH",) * 3, support),
        ))
        assert AuthorityReconciliationCharacterDfaV1.for_request(
            entry_ids=("P1",), context=context
        ).feed(text).terminal


def test_authority_dfa_enforces_sequential_links_and_decisive_finding():
    context = _context()
    record = _authority_record(
        "P1", "UNSUPPORTED_NEW_OR_MUTATED_PROPOSITION", ("MATCH", "MUTATION", "MATCH"),
        "null", ("F1", "F2")
    )
    good = _authority(
        (record,),
        (_finding(context, "F1", "P1", "SUPPORTING"), _finding(context, "F2", "P1")),
    )
    assert AuthorityReconciliationCharacterDfaV1.for_request(
        entry_ids=("P1",), context=context
    ).feed(good).terminal
    AuthorityReconciliationAuditResponseV1.model_validate_json(good)

    bad = _authority(
        (record,),
        (_finding(context, "F1", "P1", "SUPPORTING"),
         _finding(context, "F2", "P1", "SUPPORTING")),
    )
    with pytest.raises(StagePConstraintViolationV1):
        AuthorityReconciliationCharacterDfaV1.for_request(
            entry_ids=("P1",), context=context
        ).feed(bad)


def test_authority_dfa_rejects_null_support_and_wrong_request_order():
    context = _context()
    null_supported = _authority((
        _authority_record("P1", "GOVERNED_SUPPORTED", ("MATCH",) * 3, "null"),
    ))
    with pytest.raises(StagePConstraintViolationV1):
        AuthorityReconciliationCharacterDfaV1.for_request(
            entry_ids=("P1",), context=context
        ).feed(null_supported)

    support = canonical_reference_json_v1(
        context=context, field=ReferenceFieldV1.AUTHORITY_SUPPORT,
        start_utf8=0, end_utf8=1
    )
    reversed_text = _authority((
        _authority_record("P2", "GOVERNED_SUPPORTED", ("MATCH",) * 3, support),
        _authority_record("P1", "GOVERNED_SUPPORTED", ("MATCH",) * 3, support),
    ))
    with pytest.raises(StagePConstraintViolationV1):
        AuthorityReconciliationCharacterDfaV1.for_request(
            entry_ids=("P1", "P2"), context=context
        ).feed(reversed_text)


@pytest.mark.parametrize("kind", ("commitment", "authority"))
def test_incremental_and_full_rebuild_paths_equal_full_character_rebuild(kind):
    context = _context()
    if kind == "commitment":
        text = _commitment((("P1", COMMITMENT_DECISIONS[0]),))
        factory = lambda: CommitmentSpanAuditCharacterDfaV1.for_entries(("P1",))
    else:
        support = canonical_reference_json_v1(
            context=context, field=ReferenceFieldV1.AUTHORITY_SUPPORT,
            start_utf8=0, end_utf8=1
        )
        text = _authority((
            _authority_record("P1", "GOVERNED_SUPPORTED", ("MATCH",) * 3, support),
        ))
        factory = lambda: AuthorityReconciliationCharacterDfaV1.for_request(
            entry_ids=("P1",), context=context
        )
    cut = len(text) // 2
    decoded = {(1,): text[:cut], (1, 2): text, (9,): text}
    tracker = Phase2IncrementalCharacterTrackerV1(factory)
    first = tracker.state_for((1,), lambda ids: decoded[tuple(ids)])
    second = tracker.state_for((1, 2), lambda ids: decoded[tuple(ids)])
    rebuilt = tracker.state_for((9,), lambda ids: decoded[tuple(ids)])
    expected = factory().feed(text)
    assert first.path == "INCREMENTAL"
    assert second.path == "INCREMENTAL"
    assert rebuilt.path == "FULL_REBUILD"
    assert second.state == expected == rebuilt.state
    assert second.decoded_sha256 == rebuilt.decoded_sha256


def test_candidate_names_cover_both_audit_languages():
    assert len(COMMITMENT_DECISIONS) == 5
    assert set(AUTHORITY_DECISIONS) == {
        "GOVERNED_SUPPORTED",
        "UNSUPPORTED_NEW_OR_MUTATED_PROPOSITION",
        "NOT_A_REAL_WORLD_COMMITMENT",
        "UNRESOLVED_FAIL_CLOSED",
    }
