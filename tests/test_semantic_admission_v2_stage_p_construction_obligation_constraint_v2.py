from __future__ import annotations

import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.immutable_source_span_reference_v1 import (
    ImmutableUtf8SourceV1, SourceRoleV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_constraint_v2 import (
    StagePConstructionObligationConstraintStateV2,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_contract_v2 import (
    ConstructionObligationLedgerV2, ProjectionStatusV1,
    build_source_projection_receipt_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_role_coherence_constraint_v1 import (
    StagePRoleCoherenceConstraintViolationV1,
)
from pastila_scout.semantic_admission_v2.stage_p_source_reference_constraint_v1 import (
    ReferenceFieldV1, SourceReferenceConstraintContextV1, canonical_reference_json_v1,
)


ROOT = Path(__file__).resolve().parents[1]
CASE01_REQUEST = ROOT / "tests/fixtures/semantic_admission_v2/phase2_case01_request.json"


def _case_context(candidate_text=None, authority_text=None):
    case = json.loads(CASE01_REQUEST.read_bytes())
    candidate_text = case["candidate"] if candidate_text is None else candidate_text
    authority_text = case["factual_summary"] if authority_text is None else authority_text
    candidate = ImmutableUtf8SourceV1.bind(
        role=SourceRoleV1.CANDIDATE, data=candidate_text.encode())
    authority = ImmutableUtf8SourceV1.bind(
        role=SourceRoleV1.FACTUAL_AUTHORITY, data=authority_text.encode())
    return SourceReferenceConstraintContextV1.bind(
        candidate=candidate, factual_authority=authority), candidate, authority


def _valid_text(context):
    candidate = context.candidate; authority = context.factual_authority
    c = canonical_reference_json_v1(
        context=context, field=ReferenceFieldV1.CANDIDATE_SPAN,
        start_utf8=0, end_utf8=candidate.byte_length)
    a = canonical_reference_json_v1(
        context=context, field=ReferenceFieldV1.AUTHORITY_SUPPORT,
        start_utf8=0, end_utf8=authority.byte_length)
    return (
        '{"schema_name":"pastila-semantic-admission-v2-stage-p-construction-obligation-ledger",'
        '"schema_version":"2.0.0-evaluation.1","stage_id":"PROPOSITION_LEDGER",'
        '"construction_role_audit":{"candidate_reviewed_as_construction":true,'
        '"overall_disposition":"ONE_OR_MORE_MATERIAL_CONSTRUCTIONS",'
        '"construction_records":[{"construction_id":"C1","candidate_span_ref":' + c +
        ',"construction_role":"MIXED_CREATIVE_AND_REAL_WORLD","role_basis":"basis",'
        '"creative_host_entry_id":"P1","literal_or_return_entry_ids":["P2"],'
        '"resolution":"MIXED_HOST_AND_RETURNS_REQUIRED"}],"literal_path_basis":null},'
        '"entries":[{"entry_id":"P1","entry_type":"CONTAINED_CREATIVE",'
        '"candidate_span_ref":' + c + ',"authority_support_ref":null,'
        '"commitment":"creative host","scope_basis":"CREATIVE_CONTAINED",'
        '"event_alignment":"CREATIVE_VEHICLE_ONLY","authority_modality":"NOT_APPLICABLE",'
        '"candidate_modality":"NOT_APPLICABLE","authority_timing":"NOT_APPLICABLE",'
        '"candidate_timing":"NOT_APPLICABLE","independence_group":"G1",'
        '"scope_relation":"CREATIVE_HOST","creative_host_entry_id":null,'
        '"factual_return_basis":"NOT_APPLICABLE"},{"entry_id":"P2",'
        '"entry_type":"REAL_WORLD_COMMITMENT","candidate_span_ref":' + c +
        ',"authority_support_ref":' + a + ',"commitment":"governed payment practice",'
        '"scope_basis":"NECESSARILY_IMPLIED","event_alignment":"GOVERNED_EVENT",'
        '"authority_modality":"CERTAIN_OR_ACTUAL","candidate_modality":"CERTAIN_OR_ACTUAL",'
        '"authority_timing":"PAST","candidate_timing":"PAST","independence_group":"G1",'
        '"scope_relation":"FACTUAL_RETURN_WITHIN_CREATIVE_HOST",'
        '"creative_host_entry_id":"P1","factual_return_basis":"NECESSARY_IMPLICATION_SURVIVES"}],'
        '"creative_target_audits":[{"audit_id":"T1","creative_host_entry_id":"P1",'
        '"vehicle_span_ref":' + c + ',"semantic_target":"governed payment practice",'
        '"target_class":"REAL_WORLD_PROPOSITION",'
        '"survival_basis":"NECESSARY_IMPLICATION_SURVIVES","proposition_entry_id":"P2",'
        '"resolution":"RECONCILED_TO_LEDGER"}],"coverage_receipt":{'
        '"candidate_reviewed_as_whole":true,"embedded_propositions_checked":true,'
        '"creative_scope_checked":true,"unresolved_scope_present":false,'
        '"overlapping_spans_reconciled":true,"integrated_creative_hosts_checked":true,'
        '"factual_return_tests_completed":true,"creative_targets_enumerated":true,'
        '"target_classes_reviewed":true,"target_to_ledger_reconciled":true,'
        '"construction_roles_reviewed":true,"construction_to_ledger_reconciled":true},'
        '"coverage_decision":"COMPLETE"}')


def test_complete_v2_mixed_construction_language_schema_and_projection_pass():
    context, candidate, authority = _case_context(); raw = _valid_text(context)
    state = StagePConstructionObligationConstraintStateV2.for_context(context).feed(raw)
    assert state.terminal and state.can_eos
    ledger = ConstructionObligationLedgerV2.model_validate_json(raw, strict=True)
    receipt = build_source_projection_receipt_v1(
        raw_response=raw.encode(), ledger=ledger, candidate_source=candidate,
        factual_authority_source=authority)
    assert receipt.projection_status is ProjectionStatusV1.PASS
    assert len(receipt.projection_records) == 5


def test_incremental_chunks_equal_full_rebuild_for_complete_ledger():
    context, _, _ = _case_context(); raw = _valid_text(context)
    state = StagePConstructionObligationConstraintStateV2.for_context(context)
    for offset in range(0, len(raw), 17):
        state = state.feed(raw[offset:offset + 17])
        rebuilt = StagePConstructionObligationConstraintStateV2.for_context(context).feed(
            raw[:offset + 17])
        assert state == rebuilt
    assert state.terminal


@pytest.mark.parametrize("mutation", [
    lambda raw, context: raw.replace(context.candidate.sha256, "0" * 64, 1),
    lambda raw, context: raw.replace('"candidate_span_ref":', '"candidate_span":', 1),
    lambda raw, context: raw.replace('"literal_or_return_entry_ids":["P2"]',
                                     '"literal_or_return_entry_ids":["P3"]', 1),
    lambda raw, context: raw.replace('"schema_version":"2.0.0-evaluation.1",', "", 1),
])
def test_wrong_reference_v1_field_missing_obligation_or_identity_fails(mutation):
    context, _, _ = _case_context(); invalid = mutation(_valid_text(context), context)
    with pytest.raises(StagePRoleCoherenceConstraintViolationV1):
        StagePConstructionObligationConstraintStateV2.for_context(context).feed(invalid)


def test_same_lengths_different_context_rejects_bound_output():
    context, _, _ = _case_context(); raw = _valid_text(context)
    replacement, _, _ = _case_context(
        candidate_text="x" * len(context.candidate.utf8_boundaries[:-1]),
        authority_text="y" * len(context.factual_authority.utf8_boundaries[:-1]))
    with pytest.raises(StagePRoleCoherenceConstraintViolationV1):
        StagePConstructionObligationConstraintStateV2.for_context(replacement).feed(raw)


def test_context_is_mandatory_and_no_zero_argument_state_exists():
    with pytest.raises(ValueError, match="SOURCE_REFERENCE_CONTEXT_REQUIRED"):
        StagePConstructionObligationConstraintStateV2()
