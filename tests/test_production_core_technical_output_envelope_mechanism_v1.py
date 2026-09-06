import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MECHANISM = ROOT / "docs/artifacts/production-core-technical-output-envelope-mechanism-v1.json"
QUALIFICATION = (
    ROOT / "docs/artifacts/production-core-technical-output-envelope-qualification-v1.json"
)
IMPLEMENTATION = (
    ROOT / "src/pastila_scout/production_core_technical_output_envelope_v1.py"
)
IMPLEMENTATION_TEST = ROOT / "tests/test_production_core_technical_output_envelope_v1.py"
QUALIFICATION_TEST = Path(__file__).resolve()
SEMANTIC = ROOT / "docs/artifacts/core-v2-semantic-output-contract-v1.json"
STRUCTURED = ROOT / "docs/artifacts/core-v2-structured-qualification-response-v1.json"
PROFILE = ROOT / "docs/artifacts/production-core-execution-profile-proposal-v1.json"


def _value() -> dict[str, object]:
    return json.loads(MECHANISM.read_text(encoding="utf-8"))


def test_mechanism_binds_existing_authority_without_values() -> None:
    value = _value()
    frozen = value["frozen_inputs"]
    assert frozen["semantic_output_contract_sha256"] == hashlib.sha256(
        SEMANTIC.read_bytes()
    ).hexdigest()
    assert frozen["structured_qualification_response_contract_sha256"] == hashlib.sha256(
        STRUCTURED.read_bytes()
    ).hexdigest()
    assert frozen["execution_profile_sha256"] == hashlib.sha256(PROFILE.read_bytes()).hexdigest()
    assert value["byte_envelope_derivation"]["value_bytes"] is None
    assert value["token_envelope_derivation"]["value_tokens"] is None
    assert value["derived_values_authority"] == "PENDING_SEPARATE_OWNER_APPROVAL"


def test_mechanism_is_candidate_neutral_and_does_not_authorize_inference() -> None:
    value = _value()
    scope = value["scope"]
    assert scope["executes_candidate_model"] is False
    assert scope["inspects_candidate_results"] is False
    assert scope["defines_inference_wall_time_or_rss"] is False
    assert scope["defines_global_core_v2_policy"] is False
    token = value["token_envelope_derivation"]
    assert token["model_weights_or_inference_required"] is False
    assert token["network"] == "DENY_ALL"
    assert token["host_or_fallback_tokenizer_allowed"] is False
    assert value["candidate_evaluation_authorized"] is False


def test_owner_decisions_are_closed_but_values_remain_unset() -> None:
    value = _value()
    assert value["pending_owner_decisions"] == []
    assert value["canonical_serialization"]["unicode_normalization"] == (
        "NFC_BEFORE_LIMIT_BINDING_AND_SERIALIZATION"
    )
    assert value["source_span_id_authority"]["pattern"] == (
        "^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$"
    )
    assert value["margin_policy"]["byte_margin"] == 0
    assert value["margin_policy"]["token_margin"] == 0
    failures = value["fail_closed_conditions"]
    assert "unbounded response field" in failures
    assert "missing or ambiguous canonical serializer" in failures
    assert "candidate model weights are loaded or candidate output is inspected" in failures


def test_receipt_requires_two_clean_identical_derivations() -> None:
    receipt = _value()["required_proof_receipt"]
    assert receipt["clean_repetitions_required"] == 2
    assert receipt["byte_and_token_results_must_match"] is True
    assert receipt["candidate_output_or_score_allowed"] is False
    assert receipt["failure_result"] == "NO_TECHNICAL_OUTPUT_ENVELOPE_AUTHORITY"


def test_qualification_evidence_binds_rules_implementation_and_tests() -> None:
    value = json.loads(QUALIFICATION.read_text(encoding="utf-8"))
    assert value["verdict"] == "PASS_SYNTHETIC_OFFLINE_NO_PRODUCTION_VALUES"
    assert value["identities"] == {
        "mechanism_sha256": hashlib.sha256(MECHANISM.read_bytes()).hexdigest(),
        "implementation_sha256": hashlib.sha256(IMPLEMENTATION.read_bytes()).hexdigest(),
        "implementation_test_sha256": hashlib.sha256(
            IMPLEMENTATION_TEST.read_bytes()
        ).hexdigest(),
        "qualification_test_sha256": hashlib.sha256(QUALIFICATION_TEST.read_bytes()).hexdigest(),
    }
    assert value["production_values_emitted"] is False
    assert value["candidate_model_executed"] is False
    assert value["candidate_results_inspected"] is False
    assert value["network_activity"] is False
    assert value["inference_wall_time_or_rss_calibration"] is False
    reproduction = value["synthetic_reproduction"]
    assert reproduction["clean_run_receipt_sha256"] == [
        reproduction["expected_receipt_sha256"],
        reproduction["expected_receipt_sha256"],
    ]
    assert reproduction["production_value_authority"] is False
