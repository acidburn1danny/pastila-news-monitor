import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/production-core-model-qualification-framework-v1.json"
CALIBRATION = ROOT / "docs/artifacts/production-core-candidate-free-host-calibration-v1.json"
WSL_CALIBRATION = ROOT / "docs/artifacts/production-core-candidate-free-wsl-calibration-v1.json"
PROFILE = ROOT / "docs/artifacts/production-core-execution-profile-proposal-v1.json"


def test_framework_freezes_candidate_neutral_thresholds_without_results() -> None:
    value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert value["status"] == "PARTIALLY_OWNER_ACCEPTED_EXECUTION_PROFILE_PENDING"
    assert value["candidate_results_inspected"] is False
    assert value["production_authority"] == "NO_PRODUCTION_CORE_DESIGNATED"
    assert value["terminal_results"] == ["PASS", "FAIL", "NO_CANDIDATE_QUALIFIED"]
    assert value["promotion_requires_separate_owner_designation"] is True
    assert value["candidates"] == [
        "pastila-editor-core-v1.1-experimental",
        "pastila-editor-core-v1.2-experimental",
    ]
    thresholds = value["thresholds"]
    assert thresholds["semantic_hard_assertions_percent"] == 100
    assert thresholds["semantic_case_assertions_percent"] == 95
    assert thresholds["unsupported_or_changed_factual_atoms"] == 0
    assert thresholds["aggregate_compensation_allowed"] is False
    assert not ({"scores", "winner", "candidate_results"} & value.keys())


def test_framework_corpus_is_predeclared_and_nontrivial() -> None:
    value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    corpus = value["corpus"]
    assert corpus["content_addressed_before_evaluation"] is True
    assert corpus["exact_unique_case_ids"] == 200
    assert sum(corpus["primary_partitions"].values()) == 200
    assert corpus["minimum_true_holdout"] == 50
    assert corpus["clean_repetitions"] == 3


def test_host_probe_is_truthfully_non_authoritative_and_candidate_free() -> None:
    value = json.loads(CALIBRATION.read_text(encoding="utf-8"))
    assert value["authority_status"] == "NON_AUTHORITATIVE_HOST_SUPERVISOR_PROBE"
    assert value["candidate_model_loaded"] is False
    assert value["candidate_result_inspected"] is False
    assert value["predeclared_margin_results"]["technical_output_bytes"] is None
    assert value["predeclared_margin_results"]["technical_output_tokens"] is None
    assert value["limitations"]
    assert value["framework_sha256"] == hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()


def test_wsl_probe_does_not_claim_inference_runtime_authority() -> None:
    value = json.loads(WSL_CALIBRATION.read_text(encoding="utf-8"))
    assert value["authority_status"] == "NON_AUTHORITATIVE_WSL_SUPERVISOR_PROBE"
    assert value["candidate_model_loaded"] is False
    assert value["candidate_result_inspected"] is False
    assert value["predeclared_margin_results"]["technical_output_bytes"] is None
    assert any("not runtime authority" in item for item in value["limitations"])
    assert value["execution_profile_proposal_sha256"] == hashlib.sha256(
        PROFILE.read_bytes()
    ).hexdigest()


def test_execution_profile_is_proposal_not_authority() -> None:
    value = json.loads(PROFILE.read_text(encoding="utf-8"))
    assert value["status"] == (
        "OWNER_APPROVED_PROFILE_VALUES_RUNTIME_MATERIALIZATION_REQUIRED"
    )
    assert value["authority_effect"] == "QUALIFICATION_EXECUTION_PROFILE_V1_ONLY"
    assert value["scope"]["defines_global_core_v2_minimum_hardware"] is False
    assert value["scope"]["defines_core_v2_portability_policy"] is False
    assert value["runtime"]["local_mutable_wsl_install_is_authority"] is False
    assert value["runtime"]["rootfs_sha256"] is None
    assert value["loading"]["network"] == "DENY_ALL"
    assert value["decoding"]["context_tokens"] == 8192
    assert value["decoding"]["max_output_tokens"] is None
    assert value["decoding"]["semantic_output_contract_status"] == (
        "OWNER_APPROVED_AND_SEPARATELY_BOUND"
    )
    assert value["decoding"]["technical_output_limit_status"] == (
        "PENDING_OWNER_APPROVAL"
    )
