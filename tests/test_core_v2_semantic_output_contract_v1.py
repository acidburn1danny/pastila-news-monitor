import hashlib
import json
from pathlib import Path

CONTRACT = (
    Path(__file__).resolve().parents[1]
    / "docs/artifacts/core-v2-semantic-output-contract-v1.json"
)
FRAMEWORK = CONTRACT.with_name("production-core-model-qualification-framework-v1.json")
PROFILE = CONTRACT.with_name("production-core-execution-profile-proposal-v1.json")


def test_owner_approved_semantic_limits_are_exact_and_separate() -> None:
    value = json.loads(CONTRACT.read_text(encoding="utf-8"))
    factual = value["factual_output"]
    assert factual["natural_structure"]["propositions"] == {
        "minimum": 2,
        "maximum": 3,
    }
    assert factual["natural_structure"]["sentences"] == {
        "minimum": 1,
        "maximum": 2,
    }
    assert factual["secondary_hard_maximum_unicode_characters"] == 650
    assert factual["overflow"] == "FAIL"
    assert factual["truncate"] is False

    commentary = value["commentary_output"]
    assert commentary["maximum_sentences"] == 3
    assert commentary["hard_maximum_unicode_characters"] == 1000
    assert commentary["complete_punchline_or_normal_construction_must_remain_possible"]
    assert commentary["overflow"] == "FAIL"
    assert commentary["truncate"] is False


def test_unresolved_structured_and_runtime_limits_stay_null() -> None:
    value = json.loads(CONTRACT.read_text(encoding="utf-8"))
    structured = value["structured_qualification_response"]
    assert structured["status"] == "OWNER_APPROVED"
    structured_contract = CONTRACT.with_name(
        "core-v2-structured-qualification-response-v1.json"
    )
    assert structured["contract_sha256"] == hashlib.sha256(
        structured_contract.read_bytes()
    ).hexdigest()
    assert structured["candidate_verdict_authority"] is False
    assert structured["evaluator_only_verdict_authority"] is True

    technical = value["technical_runtime_decisions"]
    assert technical["status"] == "PENDING_OWNER_APPROVAL"
    assert all(item is None for name, item in technical.items() if name != "status")


def test_framework_and_profile_bind_exact_semantic_contract_bytes() -> None:
    identity = hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    framework = json.loads(FRAMEWORK.read_text(encoding="utf-8"))
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    assert framework["thresholds"]["semantic_contract_output_ceiling"][
        "contract_sha256"
    ] == identity
    assert profile["semantic_output_authority"]["contract_sha256"] == identity
