import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-role-coherence-v1-candidate.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-role-coherence-v1-evidence"


def test_candidate_and_preflight_identities_agree() -> None:
    candidate = json.loads(CANDIDATE.read_text("utf-8"))
    preflight = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    for key in ("candidate_identity", "prompt_identity", "schema_identity", "constraint_source_identity", "grammar_identity", "model_identity"):
        assert candidate[key] == preflight[key]
    assert preflight["result"] == "PASS"


def test_preflight_is_zero_inference_and_candidate_has_no_authority() -> None:
    candidate = json.loads(CANDIDATE.read_text("utf-8"))
    preflight = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    assert not any(candidate["authority"].values())
    for key in ("wsl_calls", "model_loads", "model_calls", "provider_calls"):
        assert preflight[key] == 0
    assert preflight["inference_executed"] is False
    assert preflight["stage_c_constructed"] is False and preflight["stage_c_called"] is False


def test_prompt_and_constraint_hashes_match_bound_identities() -> None:
    candidate = json.loads(CANDIDATE.read_text("utf-8"))
    prompt = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-role-coherence-prompt-v1.txt"
    execution = prompt.read_bytes()[:-1]
    assert "sha256:" + hashlib.sha256(execution).hexdigest() == candidate["prompt_identity"]
    constraint = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_role_coherence_constraint_v1.py"
    assert "sha256:" + hashlib.sha256(constraint.read_bytes()).hexdigest() == candidate["constraint_source_identity"]
