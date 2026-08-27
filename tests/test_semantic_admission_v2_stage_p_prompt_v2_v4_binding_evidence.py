import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/".semantic-admission-v2-stage-p-prompt-v2-v4-binding-evidence"
CANDIDATE=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-prompt-v2-v4-binding-candidate.json"


def test_construction_receipt_is_exact_and_zero_call() -> None:
    value=json.loads((EVIDENCE/"construction-preflight.json").read_text("utf-8"))
    assert value["result"]=="PASS" and value["rendered_prompt_unpadded"] and value["lower_prompt_exact"]
    assert value["prompt_identity"]=="sha256:fb40f0bf2be0d34ee333828cd2f5516a3edc5cede1cb355d861b54c3807d2950"
    assert value["source_bound_projector_bound"] is value["stage_c_constructed"] is value["stage_c_called"] is False
    assert value["durable_events_created"]==value["model_calls"]==value["provider_calls"]==0


def test_preparation_failure_is_not_promoted() -> None:
    value=json.loads((EVIDENCE/"attempt-1-preparation-failure.json").read_text("utf-8"))
    assert value["lifecycle"]=="QUARANTINED_ZERO_CALL_PREPARATION_FAILURE"
    assert value["promoted_evidence"] is False and value["provider_calls"]==0


def test_candidate_requires_fresh_authority_and_stops_before_inference() -> None:
    value=json.loads(CANDIDATE.read_text("utf-8"))
    assert value["lifecycle"]=="ZERO_INFERENCE_PROMPT_ONLY_PATH_READY_FOR_OWNER_REVIEW"
    assert value["one_shot_boundaries"]["maximum_provider_calls"]==1
    assert value["one_shot_boundaries"]["source_bound_projector_bound"] is False
    assert all(item is False for item in value["authority"].values())
