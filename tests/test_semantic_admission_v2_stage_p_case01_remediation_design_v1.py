import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
DESIGN=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-case01-failure-remediation-design-v1.json"


def _load():
    return json.loads(DESIGN.read_text("utf-8"))


def test_design_binds_probe_and_separates_three_tracks() -> None:
    value=_load()
    assert value["source_probe_identity"]=="ae450b09f4a63c8fc8c342d13039d609466a813fc69b80f016c1bd7b2c6a7dc1"
    assert value["scope"]=="DESIGN_ONLY_NO_PROMPT_CONTRACT_RUNNER_RUNTIME_OR_MODEL_CHANGE"
    assert all(key in value for key in ("track_a_source_role_and_membership","track_b_evidence_receipt_separation","track_c_trace_lifecycle_reconciliation"))


def test_source_roles_preserve_valid_p2_and_reject_factual_p1() -> None:
    value=_load();contract=value["acceptance_contract"]
    assert "P2" in contract["frozen_positive_reference"]
    assert "P1" in contract["frozen_negative_reference"] and "authority_support" in contract["frozen_negative_reference"]
    option=value["track_a_source_role_and_membership"]["defense_in_depth_candidate"]
    assert "All exact non-empty substrings" in option["must_preserve"][0]
    assert any("Do not silently substitute" in item for item in option["must_not_do"])


def test_receipts_distinguish_transport_raw_schema_and_membership() -> None:
    expected=_load()["track_b_evidence_receipt_separation"]["required_case01_classification"]
    assert expected=={"transport":"SUCCESS","raw_persistence":"SUCCESS","schema_validation":"PASS",
        "source_membership":"FAIL","reason_code":"STAGE_P_CANDIDATE_SPAN_SOURCE_MEMBERSHIP_FAILURE","final":"ABSTAIN_FAIL_CLOSED"}


def test_lifecycle_is_authoritative_and_absence_is_not_false() -> None:
    track=_load()["track_c_trace_lifecycle_reconciliation"]
    assert "append-only durable lifecycle remains authoritative" in track["authority_rule"]
    assert track["required_status_values"]==["OBSERVED","NOT_OBSERVED_BEFORE_TERMINAL_EVENT","LIFECYCLE_UNAVAILABLE","NOT_APPLICABLE"]


def test_design_stops_before_every_mutating_authority() -> None:
    value=_load()
    assert all(item is False for item in value["authority"].values())
    assert value["acceptance_contract"]["stage_c_calls"]==0
    assert value["acceptance_contract"]["model_or_provider_calls_during_implementation_preflight"]==0
