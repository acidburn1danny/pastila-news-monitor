from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_creative_target_request_candidate_v1 import (
    StagePCreativeTargetRequestCandidateV1,
)


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-creative-target-candidate-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-creative-target-candidate-v1-evidence"


def test_artifact_identity_sources_and_request_candidate_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8")); ids = value["identities"]
    files = {"contract_source_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_creative_target_contract_v1.py",
        "constraint_source_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_creative_target_constraint_v1.py",
        "prompt_file_sha256": "docs/artifacts/semantic-admission-v2-stage-p-creative-target-prompt-v1.txt",
        "prompt_contract_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_creative_target_prompt_v1.py",
        "request_candidate_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_creative_target_request_candidate_v1.py",
        "zero_inference_verifier_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_creative_target_zero_inference_v1.py"}
    for key, relative in files.items(): assert ids[key] == hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    candidate = StagePCreativeTargetRequestCandidateV1(project_root=ROOT)
    assert ids["request_candidate_identity"] == candidate.candidate_identity
    parts = [value["artifact_id"], value["approved_design_identity"], ids["prompt_identity"],
        ids["schema_identity"], ids["constraint_identity"], ids["grammar_identity"],
        ids["tokenizer_identity"], ids["request_candidate_identity"], "ZERO_INFERENCE_PASS",
        "NO_MODEL", "NO_STAGE_C"]
    assert value["artifact_identity"] == hashlib.sha256("\n".join(parts).encode()).hexdigest()


def test_preflight_is_zero_inference_and_grants_no_execution_authority():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    preflight = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    tokenizer = json.loads((EVIDENCE / "real-tokenizer.json").read_text("utf-8"))
    assert preflight["result"] == tokenizer["result"] == "PASS"
    assert tokenizer["state_count"] == 7 and tokenizer["states"][-1]["can_eos"] is True
    for receipt in (preflight, tokenizer):
        for key in ("model_loads", "model_calls", "provider_calls", "inference_calls", "stage_c_calls"):
            assert receipt[key] == 0
        assert receipt["case01_rerun" if "case01_rerun" in receipt else "case01_executed"] is False
    assert all(flag is False for flag in value["authority"].values())
