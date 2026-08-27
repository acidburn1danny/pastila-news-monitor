from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-creative-target-runner-executor-binding-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-creative-target-runner-executor-binding-v1-evidence/preflight.json"


def test_binding_identity_and_sources_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8")); ids = value["identities"]
    files = {"runner_sha256": "src/pastila_scout/experimental_core_v1_2_stage_p_creative_target_runner_v1.py",
        "executor_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_creative_target_durable_executor_v1.py",
        "tracker_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_creative_target_incremental_tracker_v1.py",
        "controller_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_creative_target_callback_controller_v1.py"}
    for key, relative in files.items(): assert ids[key] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    parts = [value["artifact_id"], value["approved_candidate_identity"],
        value["approved_dependency_repair_identity"], ids["runner_sha256"], ids["executor_sha256"],
        ids["tracker_sha256"], ids["controller_sha256"], "ZERO_INFERENCE", "CASE01_BLOCKED", "NO_STAGE_C"]
    assert value["binding_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_preflight_has_no_execution_authority_or_calls():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert evidence["result"] == "PASS" and evidence["case01_executed"] is False
    assert evidence["pydantic_loaded"] is evidence["transformers_loaded"] is evidence["peft_loaded"] is False
    for key in ("runner_calls", "tokenizer_loads", "model_loads", "provider_calls", "inference_calls", "stage_c_calls"):
        assert evidence[key] == 0
    assert all(flag is False for flag in value["authority"].values())
