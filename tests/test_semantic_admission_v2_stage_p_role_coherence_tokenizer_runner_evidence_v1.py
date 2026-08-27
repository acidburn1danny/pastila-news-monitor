import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-role-coherence-tokenizer-runner-binding-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-role-coherence-tokenizer-runner-binding-v1-evidence"


def test_real_tokenizer_evidence_is_zero_inference_and_complete() -> None:
    value = json.loads((EVIDENCE / "real-tokenizer-preflight.json").read_text("utf-8"))
    assert value["result"] == "PASS" and value["tokenizer_vocabulary_size"] == 131072
    assert sum(stream["tokens"] for stream in value["streams"]) == 391
    assert all(stream["decoded_exact"] and stream["terminal_state"] and stream["eos_only_after_terminal"] for stream in value["streams"])
    assert all(not stream["invalid_next_token_indices"] for stream in value["streams"])
    assert value["model_imported"] is False and value["model_load_started"] is False
    assert value["inference_started"] is False and value["model_calls"] == value["provider_calls"] == 0


def test_runner_and_dependency_hashes_are_exact() -> None:
    value = json.loads(CANDIDATE.read_text("utf-8"))["runner_binding"]
    paths = {
        "runner_sha256": "src/pastila_scout/experimental_core_v1_2_stage_p_role_coherence_runner_v1.py",
        "durable_base_runner_sha256": "src/pastila_scout/experimental_core_v1_2_stage_p_constrained_runner_v3.py",
        "constraint_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_role_coherence_constraint_v1.py",
        "trie_projector_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_trie_projector_v1.py",
        "incremental_tracker_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_role_coherence_incremental_tracker_v1.py",
        "callback_controller_sha256": "src/pastila_scout/semantic_admission_v2/stage_p_role_coherence_callback_controller_v1.py",
        "append_only_lifecycle_sha256": "src/pastila_scout/semantic_admission_v2/append_only_lifecycle_v1.py",
    }
    for key, relative in paths.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == value[key]


def test_binding_is_not_executable_or_authorized_yet() -> None:
    value = json.loads(CANDIDATE.read_text("utf-8"))
    assert value["runner_binding"]["execution_status"] == "NOT_EXECUTED"
    assert not any(value["authority"].values())
    assert value["zero_inference_receipt"]["runner_calls"] == 0
