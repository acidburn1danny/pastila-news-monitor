import json
from pathlib import Path

CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "docs/artifacts/core-v2-structured-qualification-response-v1.json"
)


def _contract() -> dict[str, object]:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_exact_nine_field_candidate_output_contract() -> None:
    output = _contract()["candidate_output"]
    assert output["required_top_level_fields_in_order"] == [
        "schema",
        "schema_version",
        "case_id",
        "request_identity",
        "output_type",
        "outcome",
        "text",
        "claim_bindings",
        "abstention_code",
    ]
    assert output["optional_fields"] == []
    assert output["additional_fields_allowed"] is False
    fields = output["field_contracts"]
    assert fields["output_type"]["enum"] == ["FACTUAL", "COMMENTARY"]
    assert fields["outcome"]["enum"] == ["ANSWER", "ABSTAIN"]
    assert fields["claim_bindings"]["maximum_items"] == 3
    assert fields["claim_bindings"]["source_span_ids_maximum"] == 8
    assert fields["claim_bindings"]["aggregate_source_span_ids_maximum"] == 24


def test_exact_semantic_and_abstention_contract() -> None:
    value = _contract()
    invariants = value["combination_invariants"]
    assert invariants["FACTUAL_ANSWER"]["maximum_unicode_characters"] == 650
    assert invariants["COMMENTARY_ANSWER"]["maximum_sentences"] == 3
    assert invariants["COMMENTARY_ANSWER"]["maximum_unicode_characters"] == 1000
    assert invariants["COMMENTARY_ANSWER"]["factual_claims_allowed"] is False
    assert value["candidate_output"]["field_contracts"]["abstention_code"][
        "enum_when_string"
    ] == [
        "INSUFFICIENT_AUTHORITY",
        "CONFLICTING_AUTHORITY",
        "AMBIGUOUS_SCOPE",
        "UNRESOLVED_REFERENCE",
        "INSTRUCTION_AUTHORITY_CONFLICT",
        "CANNOT_SATISFY_OUTPUT_CONTRACT",
        "SAFETY_ENVELOPE_EXCEEDED",
    ]


def test_completion_failure_and_verdict_authority_are_fail_closed() -> None:
    value = _contract()
    completion = value["completion"]
    assert completion["terminal_object_close_followed_immediately_by_eof"] is True
    assert completion["trailing_output_allowed"] is False
    invalid = value["invalid_behavior"]
    assert invalid["result"] == "MALFORMED_RESPONSE_FAIL"
    assert invalid["reject_whole_response"] is True
    assert all(
        item is False
        for name, item in invalid.items()
        if name not in {"result", "reject_whole_response"}
    )
    separation = value["qualification_authority_separation"]
    assert separation["candidate_output_may_contain_verdict"] is False
    assert separation["candidate_output_may_determine_verdict"] is False
    assert separation["verdict_authority"] == "EVALUATOR_ONLY"


def test_technical_limits_remain_unset() -> None:
    technical = _contract()["technical_runtime_limits"]
    assert technical["status"] == "PENDING_OWNER_APPROVAL"
    assert all(item is None for name, item in technical.items() if name != "status")
