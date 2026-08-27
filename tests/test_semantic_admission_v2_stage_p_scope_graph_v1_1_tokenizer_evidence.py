from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-v1-1-tokenizer-candidate.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-v1-1-tokenizer-evidence"


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def test_candidate_identity_and_manifest_are_exact():
    value = json.loads(CANDIDATE.read_text("utf-8"))
    expected = value.pop("candidate_identity")
    assert hashlib.sha256(_canonical(value)).hexdigest() == expected
    manifest = json.loads((EVIDENCE / "manifest.json").read_text("utf-8"))
    assert manifest["candidate_identity"] == expected


def test_real_tokenizer_profile_is_complete_and_blocks_invalid_path():
    profile = json.loads((EVIDENCE / "real-tokenizer-preflight.json").read_text("utf-8"))
    assert profile["result"] == "PASS" and profile["tokenizer_vocabulary_size"] == 131072
    assert sum(item["tokens"] for item in profile["streams"]) == profile["token_transitions_checked"] == 1406
    assert all(item["decoded_exact"] and not item["invalid_next_token_indices"] for item in profile["streams"])
    assert all(item["terminal_state"] and item["eos_only_after_terminal"] for item in profile["streams"])
    assert profile["invalid_null_support_governed_first_blocked_token_index"] == 75


def test_preflight_source_hash_and_zero_inference_are_bound():
    value = json.loads(CANDIDATE.read_text("utf-8"))
    profile = json.loads((EVIDENCE / "real-tokenizer-preflight.json").read_text("utf-8"))
    source = ROOT / "src/pastila_scout/experimental_core_v1_2_stage_p_scope_graph_v1_1_tokenizer_preflight.py"
    assert value["preflight_source_identity"] == "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
    assert not any(value["authority"].values())
    assert profile["model_imported"] is profile["model_load_started"] is profile["inference_started"] is False
    assert profile["model_calls"] == profile["provider_calls"] == profile["runner_calls"] == 0
