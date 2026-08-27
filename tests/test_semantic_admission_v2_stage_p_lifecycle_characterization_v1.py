import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/".semantic-admission-v2-stage-p-lifecycle-characterization-v1-evidence"
CANDIDATE=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-lifecycle-characterization-v1-candidate.json"


def test_final_characterization_is_zero_inference_and_equivalent() -> None:
    result=json.loads((EVIDENCE/"tokenizer-callback-characterization-final.json").read_text("utf-8"))
    assert result["result"]=="PASS" and result["allowed_set_divergences"]==0
    assert result["all_terminal"] and result["all_invalid_failures_identical"]
    assert result["model_imported"] is result["model_load_started"] is result["inference_started"] is False
    assert result["provider_calls"]==0


def test_projection_is_measured_dominant_cost_and_timeout_not_changed() -> None:
    candidate=json.loads(CANDIDATE.read_text("utf-8"));data=candidate["tokenizer_characterization"]
    assert data["token_projection_seconds_total"] > 20*data["full_replay_seconds_total"]
    assert data["projection_share_of_measured_callback_seconds"] > 0.95
    assert candidate["diagnostic_revision"]["timeout_increase_recommended"] is False


def test_all_incomplete_attempts_are_quarantined_not_promoted() -> None:
    for attempt in (1,2,3):
        value=json.loads((EVIDENCE/f"attempt-{attempt}-interruption.json").read_text("utf-8"))
        assert value["output_evidence_produced"] is False
        assert value["provider_calls"]==0
    assert "only accepted" in json.loads(CANDIDATE.read_text("utf-8"))["attempt_history"][3]


def test_next_step_is_zero_inference_cache_equivalence_not_proof_rerun() -> None:
    candidate=json.loads(CANDIDATE.read_text("utf-8"))
    assert "trie-cache canonicalization" in candidate["next_bounded_recommendation"]
    assert candidate["proof_rerun_authority"] is candidate["runtime_authority"] is False
