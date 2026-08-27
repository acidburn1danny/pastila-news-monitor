import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/".semantic-admission-v2-stage-p-runner-v3-preflight-evidence"
CANDIDATE=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-runner-v3-zero-inference-candidate.json"


def test_real_tokenizer_preflight_passes_without_inference() -> None:
    value=json.loads((EVIDENCE/"tokenizer-construction-equivalence.json").read_text("utf-8"))
    assert value["result"]=="PASS" and value["allowed_set_divergences"]==0
    assert value["prefixes_compared"]==18 and value["tracker_paths"]==["INCREMENTAL"]
    assert value["model_imported"] is value["model_load_started"] is value["inference_started"] is False
    assert value["model_calls"]==value["provider_calls"]==0


def test_incomplete_attempt_is_quarantined() -> None:
    value=json.loads((EVIDENCE/"attempt-1-interruption.json").read_text("utf-8"))
    assert value["lifecycle"]=="QUARANTINED_INCOMPLETE_PREFLIGHT"
    assert value["promoted_evidence"] is False and value["inference_started"] is False


def test_candidate_stops_before_probe_and_runtime_authority() -> None:
    value=json.loads(CANDIDATE.read_text("utf-8"))
    assert value["lifecycle"]=="ZERO_INFERENCE_RUNNER_CANDIDATE_READY_FOR_OWNER_REVIEW"
    assert value["real_tokenizer_preflight"]["allowed_set_divergences"]==0
    assert all(item is False for item in value["authority"].values())
    assert "exactly one evaluation-only Stage-P-only Case 01" in value["next_bounded_recommendation"]
