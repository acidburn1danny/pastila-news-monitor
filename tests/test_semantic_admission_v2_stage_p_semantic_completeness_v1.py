from __future__ import annotations

import json
import base64
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.immutable_source_span_reference_v1 import (
    ImmutableUtf8SourceV1, SourceRoleV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_character_controller_v1 import (
    StagePConstructionObligationCharacterControllerV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_semantic_completeness_v1 import (
    CoverageGapJustificationV1, SemanticCompletenessAdmissionV1,
    SemanticCompletenessFailureV1,
    SemanticCompletenessPolicyV1,
    SourceBoundInterpretationV1, UnresolvedJustificationV1,
    seal_semantic_completeness_policy_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_token_projector_v1 import (
    StagePTokenProjectionFailureV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_token_projector_v2 import (
    StagePConstructionObligationV2TokenProjectorV2,
)
from pastila_scout.semantic_admission_v2.stage_p_source_reference_constraint_v1 import (
    SourceReferenceConstraintContextV1,
)


ROOT = Path(__file__).resolve().parents[1]
REQUEST = ROOT / "tests/fixtures/semantic_admission_v2/phase2_case01_request.json"
LEDGER = ROOT / "tests/fixtures/semantic_admission_v2/phase2_case01_ledger.json"
FROZEN_RAW_SHA256 = "cc02c9fb69a516aca396256b9894b3e6fdb7b7cebafa1bd31f439b4066732935"
TOKEN_1800_EVIDENCE_COMMIT = "3be841593638c03248ebeee2e3c90f796688dbf7"
TOKEN_1800_RECEIPT_PATH = (
    ".semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-"
    "v1-2-1-construction-disposition-pruning-bound-evidence/linux-generation/"
    "no-legal-token-receipt.json")


def _sources():
    request = json.loads(REQUEST.read_bytes())
    candidate = ImmutableUtf8SourceV1.bind(
        role=SourceRoleV1.CANDIDATE, data=request["candidate"].encode())
    authority = ImmutableUtf8SourceV1.bind(
        role=SourceRoleV1.FACTUAL_AUTHORITY,
        data=request["factual_summary"].encode())
    return candidate, authority


def _policy():
    candidate, authority = _sources()
    return SemanticCompletenessPolicyV1.bind(
        candidate=candidate, factual_authority=authority)


def test_exact_token_1800_candidate_is_pruned_at_first_policy_incompatible_choice():
    frozen = subprocess.run(
        ["git", "show", f"{TOKEN_1800_EVIDENCE_COMMIT}:{TOKEN_1800_RECEIPT_PATH}"],
        cwd=ROOT, check=True, capture_output=True).stdout
    receipt = json.loads(frozen)
    candidate = base64.b64decode(receipt["terminal_candidate_utf8_base64"], validate=True)
    assert receipt["generated_token_count"] == 1800
    assert receipt["terminal_candidate_sha256"] == receipt["decoded_prefix_sha256"]

    source, authority = _sources()
    context = SourceReferenceConstraintContextV1.bind(
        candidate=source, factual_authority=authority)
    controller = StagePConstructionObligationCharacterControllerV1(
        context=context, decoder_identity="token-1800-regression",
        semantic_policy=_policy())
    incompatible = b'"overall_disposition":"U'
    offset = candidate.index(incompatible) + len(incompatible) - 1
    prefix = candidate[:offset].decode("utf-8")
    result = controller.allowed((1,), lambda _: prefix)
    assert result.allowance.finite_characters == ("O",)
    with pytest.raises(Exception, match="ENUM_MISMATCH"):
        controller.allowed((1, 2), lambda _: candidate[:offset + 1].decode("utf-8"))


def test_case01_policy_dfa_accepts_exact_topology_and_prunes_false_required_receipt():
    source, authority = _sources()
    context = SourceReferenceConstraintContextV1.bind(
        candidate=source, factual_authority=authority)
    raw = json.dumps(_positive_value(), ensure_ascii=False, separators=(",", ":"))
    controller = StagePConstructionObligationCharacterControllerV1(
        context=context, decoder_identity="case01-policy-positive",
        semantic_policy=_policy())
    result = controller.allowed((1,), lambda _: raw)
    assert result.prefix.state.terminal is True

    compatible = b'"overlapping_spans_reconciled":true'
    incompatible = b'"overlapping_spans_reconciled":false'
    encoded = raw.encode("utf-8").replace(compatible, incompatible)
    offset = encoded.index(incompatible) + len(incompatible) - len(b"false")
    controller = StagePConstructionObligationCharacterControllerV1(
        context=context, decoder_identity="case01-policy-negative",
        semantic_policy=_policy())
    prefix = encoded[:offset].decode("utf-8")
    assert controller.allowed((1,), lambda _: prefix).allowance.finite_characters == ("t",)
    with pytest.raises(Exception, match="ENUM_MISMATCH"):
        controller.allowed((1, 2), lambda _: encoded[:offset + 1].decode("utf-8"))


def _reference(role: str, sha256: str, start: int, end: int):
    return {"source_role": role, "source_sha256": sha256,
            "start_utf8": start, "end_utf8": end}


def _positive_value():
    candidate, authority = _sources()
    value = json.loads(LEDGER.read_bytes())
    full = _reference("CANDIDATE", candidate.sha256, 0, len(candidate.data))
    for record in value["construction_role_audit"]["construction_records"]:
        record["candidate_span_ref"] = full
    value["entries"][0]["candidate_span_ref"] = full
    value["creative_target_audits"][0]["vehicle_span_ref"] = full
    cue_start = candidate.data.index("pare că".encode())
    value["entries"][1]["candidate_span_ref"] = _reference(
        "CANDIDATE", candidate.sha256, cue_start, len(candidate.data))
    value["entries"][1]["authority_support_ref"] = _reference(
        "FACTUAL_AUTHORITY", authority.sha256, 0, len(authority.data))
    value["entries"][1]["event_alignment"] = "GOVERNED_EVENT"
    value["entries"][1]["authority_modality"] = "CERTAIN_OR_ACTUAL"
    value["entries"][1]["authority_timing"] = "PAST"
    value["entries"][1]["candidate_modality"] = "POSSIBLE"
    return value


def _frozen_value():
    candidate, _ = _sources()
    span = _reference("CANDIDATE", candidate.sha256, 0, 100)
    unresolved = {
        "entry_id": "P1", "entry_type": "UNRESOLVED_SCOPE",
        "candidate_span_ref": span, "authority_support_ref": None,
        "commitment": "UNRESOLVED", "scope_basis": "UNRESOLVED",
        "event_alignment": "UNRESOLVED", "authority_modality": "NOT_APPLICABLE",
        "candidate_modality": "NOT_APPLICABLE", "authority_timing": "NOT_APPLICABLE",
        "candidate_timing": "NOT_APPLICABLE", "independence_group": "G1",
        "scope_relation": "UNRESOLVED_RELATION", "creative_host_entry_id": None,
        "factual_return_basis": "UNRESOLVED"}
    return {
        "schema_name": "pastila-semantic-admission-v2-stage-p-construction-obligation-ledger",
        "schema_version": "2.0.0-evaluation.1", "stage_id": "PROPOSITION_LEDGER",
        "construction_role_audit": {
            "candidate_reviewed_as_construction": True,
            "overall_disposition": "UNRESOLVED_CONSTRUCTION_ROLE",
            "construction_records": [{
                "construction_id": "C1", "candidate_span_ref": span,
                "construction_role": "UNRESOLVED", "role_basis": "NO_MATCHING_ROLE",
                "creative_host_entry_id": None, "literal_or_return_entry_ids": [],
                "resolution": "FAIL_CLOSED_UNRESOLVED"}], "literal_path_basis": None},
        "entries": [unresolved, {**unresolved, "entry_id": "P2"}],
        "creative_target_audits": [],
        "coverage_receipt": {
            "candidate_reviewed_as_whole": True, "embedded_propositions_checked": False,
            "creative_scope_checked": False, "unresolved_scope_present": True,
            "overlapping_spans_reconciled": False,
            "integrated_creative_hosts_checked": False,
            "factual_return_tests_completed": False, "creative_targets_enumerated": False,
            "target_classes_reviewed": False, "target_to_ledger_reconciled": False,
            "construction_roles_reviewed": True,
            "construction_to_ledger_reconciled": True},
        "coverage_decision": "INDETERMINATE"}


def _raw(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def test_positive_case01_has_full_coverage_authority_creative_target_and_possible_modality():
    admission = SemanticCompletenessAdmissionV1(_policy())
    ledger = admission.validate_terminal(_raw(_positive_value()))
    assert ledger.entries[1].candidate_modality.value == "POSSIBLE"
    assert ledger.entries[1].authority_support_ref is not None
    assert ledger.creative_target_audits
    audits = admission.qualification_audits(ledger)
    assert len(audits) == 1
    assert audits[0].proposition_entry_id == "P2"
    assert audits[0].source_sha256 == _policy().candidate_sha256
    assert len(audits[0].audit_identity) == 64


def test_frozen_output_is_schema_valid_but_rejected_for_uncovered_bytes():
    raw = _raw(_frozen_value())
    import hashlib
    assert hashlib.sha256(raw.encode()).hexdigest() == FROZEN_RAW_SHA256
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_CONSTRUCTION_COVERAGE_INCOMPLETE"):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(raw)


def test_semantically_duplicate_entries_are_rejected_after_coverage_is_complete():
    value = _frozen_value(); candidate, _ = _sources()
    for record in value["construction_role_audit"]["construction_records"]:
        record["candidate_span_ref"]["end_utf8"] = len(candidate.data)
    for entry in value["entries"]:
        entry["candidate_span_ref"]["end_utf8"] = len(candidate.data)
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_DUPLICATE_ENTRY"):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(_raw(value))


def test_whole_review_cannot_coexist_with_false_applicable_receipts():
    value = _frozen_value(); candidate, _ = _sources()
    value["construction_role_audit"]["construction_records"][0]["candidate_span_ref"]["end_utf8"] = len(candidate.data)
    value["entries"] = [{**value["entries"][0], "candidate_span_ref": _reference(
        "CANDIDATE", candidate.sha256, 0, len(candidate.data))}]
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_WHOLE_REVIEW_INCONSISTENT"):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(_raw(value))


def test_blanket_unresolved_requires_exact_reason_and_two_interpretations():
    value = _frozen_value(); candidate, _ = _sources()
    value["construction_role_audit"]["construction_records"][0]["candidate_span_ref"]["end_utf8"] = len(candidate.data)
    value["entries"] = [{**value["entries"][0], "candidate_span_ref": _reference(
        "CANDIDATE", candidate.sha256, 0, len(candidate.data))}]
    for key in value["coverage_receipt"]:
        value["coverage_receipt"][key] = key != "unresolved_scope_present" or True
    policy = seal_semantic_completeness_policy_v1(replace(
        _policy(), creative_target_analysis_required=False,
        factual_authority_analysis_required=False, qualifications=(),
        required_returns=(), required_topology=None,
        required_constructions=(), required_creative=()))
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_UNRESOLVED_ID_SET_MISMATCH"):
        SemanticCompletenessAdmissionV1(policy).validate_terminal(_raw(value))


@pytest.mark.parametrize(("mutation", "reason"), [
    (lambda value: (value["entries"][1].update(
        authority_support_ref=None, event_alignment="NEW_UNSUPPORTED_EVENT",
        authority_modality="NOT_APPLICABLE", authority_timing="NOT_APPLICABLE")),
     "SEMANTIC_COMPLETENESS_FACTUAL_AUTHORITY_ANALYSIS_REQUIRED"),
    (lambda value: value["entries"][1].update(candidate_modality="CERTAIN_OR_ACTUAL"),
     "SEMANTIC_COMPLETENESS_REQUIRED_RETURN_SEMANTICS_MISMATCH"),
])
def test_required_case01_analyses_fail_closed(mutation, reason):
    value = _positive_value(); mutation(value)
    with pytest.raises(SemanticCompletenessFailureV1, match=reason):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(_raw(value))


def test_case01_creative_target_analysis_is_required_independently_of_declared_role():
    value = _frozen_value(); candidate, _ = _sources()
    value["construction_role_audit"]["construction_records"][0]["candidate_span_ref"]["end_utf8"] = len(candidate.data)
    value["entries"] = [{**value["entries"][0], "candidate_span_ref": _reference(
        "CANDIDATE", candidate.sha256, 0, len(candidate.data))}]
    for key in value["coverage_receipt"]:
        value["coverage_receipt"][key] = True
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_CREATIVE_TARGET_ANALYSIS_REQUIRED"):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(_raw(value))


def test_creative_vehicle_span_cannot_mask_construction_or_proposition_gap():
    value = _positive_value()
    for record in value["construction_role_audit"]["construction_records"]:
        record["candidate_span_ref"]["end_utf8"] = 100
    for entry in value["entries"]:
        entry["candidate_span_ref"]["end_utf8"] = 100
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_CONSTRUCTION_COVERAGE_INCOMPLETE"):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(_raw(value))


def test_authority_cannot_move_from_factual_return_to_creative_host():
    value = _positive_value()
    value["entries"][0]["authority_support_ref"] = value["entries"][1]["authority_support_ref"]
    value["entries"][1].update(
        authority_support_ref=None, event_alignment="NEW_UNSUPPORTED_EVENT",
        authority_modality="NOT_APPLICABLE", authority_timing="NOT_APPLICABLE")
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_AUTHORITY_ON_NONFACTUAL_ENTRY"):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(_raw(value))


def test_unbound_factual_carrier_cannot_satisfy_return_authority():
    value = _positive_value()
    authority = value["entries"][1]["authority_support_ref"]
    value["entries"][1].update(
        authority_support_ref=None, event_alignment="NEW_UNSUPPORTED_EVENT",
        authority_modality="NOT_APPLICABLE", authority_timing="NOT_APPLICABLE")
    extra = dict(value["entries"][1])
    extra.update(entry_id="P3", commitment="unrelated authority carrier",
                 authority_support_ref=authority, event_alignment="GOVERNED_EVENT",
                 authority_modality="CERTAIN_OR_ACTUAL", authority_timing="PAST")
    value["entries"].append(extra)
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_FACTUAL_AUTHORITY_ANALYSIS_REQUIRED"):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(_raw(value))


def test_required_p2_authority_cannot_be_split_across_expanded_returns():
    value = _positive_value(); _, authority_source = _sources()
    value["entries"][1]["authority_support_ref"]["end_utf8"] = 1
    extra = dict(value["entries"][1])
    extra.update(
        entry_id="P3", commitment="synthetic authority remainder",
        authority_support_ref=_reference(
            "FACTUAL_AUTHORITY", authority_source.sha256, 1,
            len(authority_source.data)))
    value["entries"].append(extra)
    value["construction_role_audit"]["construction_records"][0][
        "literal_or_return_entry_ids"] = ["P2", "P3"]
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_AUTHORITY_COVERAGE_INCOMPLETE"):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(_raw(value))


def test_case01_c1_cannot_append_an_unjustified_additional_return():
    value = _positive_value()
    extra = dict(value["entries"][1])
    extra.update(entry_id="P3", commitment="synthetic additional return")
    value["entries"].append(extra)
    value["construction_role_audit"]["construction_records"][0][
        "literal_or_return_entry_ids"] = ["P2", "P3"]
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_REQUIRED_RETURN_BINDING_MISMATCH"):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(_raw(value))


def test_case01_cannot_tunnel_an_additional_return_through_synthetic_c2():
    value = _positive_value()
    extra_entry = dict(value["entries"][1])
    extra_entry.update(entry_id="P3", commitment="synthetic return through C2")
    value["entries"].append(extra_entry)
    extra_construction = dict(
        value["construction_role_audit"]["construction_records"][0])
    extra_construction.update(
        construction_id="C2", literal_or_return_entry_ids=["P3"],
        role_basis="synthetic parallel construction")
    value["construction_role_audit"]["construction_records"].append(
        extra_construction)
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_REQUIRED_TOPOLOGY_MISMATCH"):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(_raw(value))


def test_relinked_synthetic_return_cannot_replace_bound_qualification_entry():
    value = _positive_value()
    value["entries"][1].update(
        authority_support_ref=None, event_alignment="NEW_UNSUPPORTED_EVENT",
        authority_modality="NOT_APPLICABLE", authority_timing="NOT_APPLICABLE",
        candidate_modality="CERTAIN_OR_ACTUAL")
    extra = dict(_positive_value()["entries"][1])
    extra.update(entry_id="P3", commitment="synthetic return",
                 candidate_modality="POSSIBLE")
    value["entries"].append(extra)
    value["construction_role_audit"]["construction_records"][0][
        "literal_or_return_entry_ids"] = ["P3"]
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_REQUIRED_AUTHORITY_RETURN_MISSING"):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(_raw(value))


def test_unrelated_possible_entry_cannot_discharge_qualification_audit():
    value = _positive_value()
    value["entries"][1]["candidate_modality"] = "CERTAIN_OR_ACTUAL"
    extra = dict(value["entries"][1])
    extra.update(entry_id="P3", commitment="unrelated qualifier carrier",
                 candidate_modality="POSSIBLE", authority_support_ref=None,
                 event_alignment="NEW_UNSUPPORTED_EVENT",
                 authority_modality="NOT_APPLICABLE",
                 authority_timing="NOT_APPLICABLE")
    value["entries"].append(extra)
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_REQUIRED_RETURN_SEMANTICS_MISMATCH"):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(_raw(value))


def test_gap_partition_requires_utf8_boundaries_and_closed_reason_codes():
    policy = _policy()
    invalid = seal_semantic_completeness_policy_v1(replace(
        policy, justified_gaps=(CoverageGapJustificationV1(1, 2, "free text"),)))
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_GAP_JUSTIFICATION_INVALID"):
        SemanticCompletenessAdmissionV1(invalid).validate_terminal(
            _raw(_positive_value()))


def test_mutated_policy_fields_cannot_reuse_original_policy_identity():
    forged = replace(_policy(), justified_gaps=(
        CoverageGapJustificationV1(100, 147, "NON_SEMANTIC_SEPARATOR"),))
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_POLICY_IDENTITY_MISMATCH"):
        SemanticCompletenessAdmissionV1(forged).validate_terminal(
            _raw(_positive_value()))


def test_unresolved_justification_ids_must_exactly_equal_observed_records():
    value = _frozen_value(); candidate, _ = _sources()
    span = _reference("CANDIDATE", candidate.sha256, 0, len(candidate.data))
    value["construction_role_audit"]["construction_records"][0].update(
        candidate_span_ref=span, role_basis="CONSTRUCTION_ROLE_AMBIGUITY")
    value["entries"] = [{**value["entries"][0], "candidate_span_ref": span}]
    for key in value["coverage_receipt"]:
        value["coverage_receipt"][key] = True
    interpretations = (
        SourceBoundInterpretationV1(
            "literal", candidate.sha256, 0, len(candidate.data)),
        SourceBoundInterpretationV1(
            "mixed", candidate.sha256, 0, len(candidate.data)))
    justification = UnresolvedJustificationV1(
        0, len(candidate.data), "CONSTRUCTION_ROLE_AMBIGUITY",
        ("C1", "C8"), ("P1", "P8"), interpretations)
    policy = seal_semantic_completeness_policy_v1(replace(
        _policy(), creative_target_analysis_required=False,
        factual_authority_analysis_required=False, qualifications=(), required_returns=(),
        required_topology=None,
        required_constructions=(), required_creative=(),
        unresolved_justifications=(justification,)))
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_UNRESOLVED_ID_SET_MISMATCH"):
        SemanticCompletenessAdmissionV1(policy).validate_terminal(_raw(value))


@pytest.mark.parametrize("justifications", ["duplicates", "wrong_span"])
def test_unresolved_justification_partition_rejects_duplicate_or_cross_span_ids(
    justifications,
):
    value = _frozen_value(); candidate, _ = _sources()
    span = _reference("CANDIDATE", candidate.sha256, 0, len(candidate.data))
    value["construction_role_audit"]["construction_records"][0].update(
        candidate_span_ref=span, role_basis="CONSTRUCTION_ROLE_AMBIGUITY")
    value["entries"] = [{**value["entries"][0], "candidate_span_ref": span}]
    for key in value["coverage_receipt"]:
        value["coverage_receipt"][key] = True
    interpretations = (
        SourceBoundInterpretationV1(
            "literal", candidate.sha256, 0, len(candidate.data)),
        SourceBoundInterpretationV1(
            "mixed", candidate.sha256, 0, len(candidate.data)))
    canonical = UnresolvedJustificationV1(
        0, len(candidate.data), "CONSTRUCTION_ROLE_AMBIGUITY",
        ("C1",), ("P1",), interpretations)
    if justifications == "duplicates":
        selected = (replace(
            canonical, construction_ids=("C1", "C1"),
            entry_ids=("P1", "P1")),)
    else:
        wrong = UnresolvedJustificationV1(
            1, len(candidate.data), "CONSTRUCTION_ROLE_AMBIGUITY",
            ("C1",), ("P1",), (
                SourceBoundInterpretationV1(
                    "literal", candidate.sha256, 1, len(candidate.data)),
                SourceBoundInterpretationV1(
                    "mixed", candidate.sha256, 1, len(candidate.data))))
        selected = (canonical, wrong)
    policy = seal_semantic_completeness_policy_v1(replace(
        _policy(), creative_target_analysis_required=False,
        factual_authority_analysis_required=False, qualifications=(), required_returns=(),
        required_topology=None,
        required_constructions=(), required_creative=(),
        unresolved_justifications=selected))
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_UNRESOLVED_ID_SET_MISMATCH"):
        SemanticCompletenessAdmissionV1(policy).validate_terminal(_raw(value))


@pytest.mark.parametrize("mutation", [
    lambda entry: entry.update(commitment="synthetic unrelated carrier"),
    lambda entry: entry.update(event_alignment="NEW_UNSUPPORTED_EVENT"),
    lambda entry: entry.update(scope_basis="ASSERTED"),
    lambda entry: entry.update(factual_return_basis="ENTAILMENT_SURVIVES"),
    lambda entry: entry.update(authority_modality="POSSIBLE"),
    lambda entry: entry.update(authority_timing="PRESENT"),
])
def test_case01_p2_semantics_are_request_bound(mutation):
    value = _positive_value(); mutation(value["entries"][1])
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_REQUIRED_RETURN_SEMANTICS_MISMATCH"):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(_raw(value))


@pytest.mark.parametrize("mutation", [
    lambda value: value["construction_role_audit"]["construction_records"][0].update(
        role_basis="synthetic unsupported construction basis"),
    lambda value: value["entries"][0].update(
        commitment="synthetic unrelated creative host"),
    lambda value: value["creative_target_audits"][0].update(
        semantic_target="synthetic unrelated target"),
    lambda value: value["entries"][0]["candidate_span_ref"].update(
        end_utf8=69),
    lambda value: value["creative_target_audits"][0]["vehicle_span_ref"].update(
        end_utf8=69),
])
def test_case01_construction_and_creative_semantics_are_request_bound(mutation):
    value = _positive_value(); mutation(value)
    with pytest.raises(SemanticCompletenessFailureV1, match=
                       "SEMANTIC_COMPLETENESS_(?:.*_SEMANTICS_MISMATCH|"
                       "CONSTRUCTION_COVERAGE_INCOMPLETE)"):
        SemanticCompletenessAdmissionV1(_policy()).validate_terminal(_raw(value))


def test_projector_withholds_eos_for_schema_terminal_semantically_incomplete_output():
    candidate, authority = _sources()
    context = SourceReferenceConstraintContextV1.bind(
        candidate=candidate, factual_authority=authority)
    controller = StagePConstructionObligationCharacterControllerV1(
        context=context, decoder_identity="decoder")
    raw = _raw(_frozen_value())
    token_pieces = {index: character for index, character in enumerate(sorted(set(raw)))}
    reverse = {character: index for index, character in token_pieces.items()}
    eos = len(token_pieces) + 1
    admission = SemanticCompletenessAdmissionV1(_policy())
    projector = StagePConstructionObligationV2TokenProjectorV2(
        controller=controller, token_pieces=token_pieces, eos_token_id=eos,
        tokenizer_identity="tokenizer", decoder_identity="decoder",
        request_context_identity=context.binding_identity,
        request_authority_identity="a" * 64,
        terminal_admission=admission.validate_terminal,
        terminal_admission_identity=admission.policy.identity)
    ids = tuple(reverse[character] for character in raw)
    decode = lambda values: "".join(token_pieces[item] for item in values)
    with pytest.raises(StagePTokenProjectionFailureV1) as failure:
        projector.allowed_token_ids(ids, decode)
    assert failure.value.receipt.reason_code == (
        "SEMANTIC_COMPLETENESS_CONSTRUCTION_COVERAGE_INCOMPLETE")
    assert not failure.value.receipt.eos_allowed
