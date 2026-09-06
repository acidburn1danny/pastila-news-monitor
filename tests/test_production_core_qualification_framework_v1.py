import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/production-core-model-qualification-framework-v1.json"
CALIBRATION = ROOT / "docs/artifacts/production-core-candidate-free-host-calibration-v1.json"
WSL_CALIBRATION = ROOT / "docs/artifacts/production-core-candidate-free-wsl-calibration-v1.json"
PROFILE = ROOT / "docs/artifacts/production-core-execution-profile-proposal-v1.json"
TECHNICAL_MECHANISM = (
    ROOT / "docs/artifacts/production-core-technical-output-envelope-mechanism-v1.json"
)
TECHNICAL_QUALIFICATION = (
    ROOT / "docs/artifacts/production-core-technical-output-envelope-qualification-v1.json"
)


def test_framework_freezes_candidate_neutral_thresholds_without_results() -> None:
    value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert value["status"] == (
        "OWNER_ACCEPTED_PROFILE_V1_RESOURCE_ENVELOPES"
    )
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
    assert thresholds["cancellation_deadline_seconds"] is None
    assert thresholds["wall_time_seconds_per_case_max"] == 600
    assert thresholds["peak_rss_bytes_per_case_max"] == 15 * 1024**3
    assert thresholds["technical_output_bytes_max"] == 6268
    assert thresholds["technical_output_tokens_max"] == 6268
    assert thresholds["technical_output_bytes_classification"] == "EXACT_CANONICAL_MAXIMUM"
    assert thresholds["technical_output_tokens_classification"] == (
        "CONSERVATIVE_BYTE_TIGHT_TOKEN_CEILING"
    )
    mechanism = thresholds["technical_output_envelope_mechanism"]
    assert mechanism["status"] == "OWNER_APPROVED_PRODUCTION_VALUES_OFFLINE_QUALIFIED"
    assert mechanism["sha256"] == hashlib.sha256(TECHNICAL_MECHANISM.read_bytes()).hexdigest()
    assert mechanism["qualification_sha256"] == hashlib.sha256(
        TECHNICAL_QUALIFICATION.read_bytes()
    ).hexdigest()
    assert mechanism["candidate_execution_authorized"] is False
    assert mechanism["candidate_results_inspected"] is False
    assert mechanism["defines_inference_wall_time_or_rss"] is False
    assert thresholds["qualification_execution_profile_v1_structural_supervisor_envelopes"] == {
        "authority_status": "OWNER_APPROVED",
        "evidence_sha256": hashlib.sha256(
            (
                ROOT
                / "docs/artifacts/production-core-content-addressed-runtime-calibration-v1.json"
            ).read_bytes()
        ).hexdigest(),
        "cancellation_deadline_seconds": 0.5,
        "structural_wall_time_seconds": 1,
        "structural_peak_rss_bytes": 64 * 1024 * 1024,
        "defines_model_inference_limits": False,
        "defines_global_core_v2_policy": False,
    }
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
    assert value["framework_sha256"] == "a16188e1eb479b870a6e33ed619874477d6b232c1a46bdb1e352efd788b73d8e"


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
