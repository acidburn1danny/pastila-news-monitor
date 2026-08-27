import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-role-coherence-executor-probe-binding-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-role-coherence-executor-probe-binding-v1-evidence"


def test_preflight_matches_candidate_and_has_no_calls() -> None:
    candidate = json.loads(CANDIDATE.read_text("utf-8"))
    receipt = json.loads((EVIDENCE / "preflight.json").read_text("utf-8"))
    for key in ("case_id", "candidate_identity", "prompt_identity", "schema_identity", "grammar_identity", "model_identity"):
        assert candidate[key] == receipt[key]
    assert receipt["result"] == "PASS" and receipt["maximum_provider_calls"] == 1
    for key in ("durable_lifecycle_events", "wsl_calls", "model_calls", "provider_calls", "runner_calls"):
        assert receipt[key] == 0
    assert receipt["inference_executed"] is False


def test_bound_implementation_hashes_are_exact() -> None:
    value = json.loads(CANDIDATE.read_text("utf-8"))
    paths = {
        "executor_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_role_coherence_durable_executor_v1.py",
        "evaluator_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_role_coherence_evaluator_v1.py",
        "probe_runner_sha256": "src/pastila_scout/semantic_admission_v2/run_stage_p_role_coherence_case01_probe_v1.py",
    }
    for key, relative in paths.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == value[key]


def test_execution_remains_unauthorized() -> None:
    value = json.loads(CANDIDATE.read_text("utf-8"))
    assert not any(value["authority"].values())
    assert value["execution_boundaries"]["stage_c_constructed"] is False
    assert value["execution_boundaries"]["case10_edge"] is False
