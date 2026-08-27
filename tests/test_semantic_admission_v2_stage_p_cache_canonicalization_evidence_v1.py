import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/".semantic-admission-v2-stage-p-cache-canonicalization-v1-evidence"
CANDIDATE=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-cache-canonicalization-v1-candidate.json"


def test_real_tokenizer_candidate_has_zero_divergence_and_no_inference() -> None:
    result=json.loads((EVIDENCE/"real-tokenizer-cache-characterization.json").read_text("utf-8"))
    assert result["result"]=="PASS" and result["allowed_set_divergences"]==0
    assert result["model_imported"] is result["model_load_started"] is result["inference_started"] is False
    assert result["model_calls"]==result["provider_calls"]==0


def test_empty_state_is_preserved_and_nonempty_states_are_equivalent() -> None:
    result=json.loads((EVIDENCE/"real-tokenizer-cache-characterization.json").read_text("utf-8"))
    states=result["targeted_string_states"]
    assert [item["string_characters"] for item in states]==[0,1,2,8,64,256,400]
    assert all(item["same"] for item in states)
    assert states[0]["candidate_seconds"]>0.1
    assert max(item["candidate_seconds"] for item in states[1:])<0.001


def test_candidate_reports_bounded_speedup_without_runtime_claim() -> None:
    candidate=json.loads(CANDIDATE.read_text("utf-8"));real=candidate["real_tokenizer_evidence"]
    assert real["six_shape_speedup"]>1.8 and real["targeted_nonempty_speedup"]>70000
    assert "not a predicted end-to-end" in candidate["limitations"][0]
    assert candidate["runner_integration_authority"] is candidate["proof_rerun_authority"] is False
