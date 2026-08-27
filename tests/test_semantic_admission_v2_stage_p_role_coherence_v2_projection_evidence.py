import hashlib
import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-role-coherence-v2-projection-candidate.json"
EVIDENCE=ROOT/".semantic-admission-v2-stage-p-role-coherence-v2-projection-evidence"


def test_real_tokenizer_v2_has_all_legal_paths_and_blocks_observed_bad_path() -> None:
    value=json.loads((EVIDENCE/"real-tokenizer-preflight.json").read_text("utf-8"))
    assert value["result"]=="PASS" and sum(x["tokens"] for x in value["streams"])==747
    assert all(x["decoded_exact"] and not x["invalid_next_token_indices"] and x["terminal"] and x["eos_only"] for x in value["streams"])
    assert value["observed_invalid_real_first_blocked_token_index"]==97
    assert value["model_imported"] is False and value["model_load_started"] is False
    assert value["inference_started"] is False and value["model_calls"]==value["provider_calls"]==0


def test_candidate_identities_and_sources_are_exact() -> None:
    value=json.loads(CANDIDATE.read_text("utf-8"))
    constraint=ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_role_coherence_constraint_v2.py"
    assert "sha256:"+hashlib.sha256(constraint.read_bytes()).hexdigest()==value["constraint_identity"]
    assert value["prompt_identity"]=="sha256:dd9f26782347ea2a8901135fc8bb671587d020a794798de404dc274e699fa4f8"
    assert value["schema_identity"]=="sha256:a47603e257ee5e315b77993891f0079e30e6c63a150b6b04e6889a98a4613ac9"


def test_no_further_execution_authority() -> None:
    value=json.loads(CANDIDATE.read_text("utf-8"))
    assert not any(value["authority"].values())
    assert value["observed_failure_regression"]["late_dead_end_eliminated"] is True
