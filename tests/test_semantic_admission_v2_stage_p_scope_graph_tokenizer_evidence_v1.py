from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-scope-graph-tokenizer-v1-candidate.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-tokenizer-v1-evidence"


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def test_candidate_identity_and_manifest_are_exact():
    candidate = json.loads(CANDIDATE.read_text("utf-8"))
    expected = candidate.pop("candidate_identity")
    assert hashlib.sha256(_canonical(candidate)).hexdigest() == expected
    manifest = json.loads((EVIDENCE / "manifest.json").read_text("utf-8"))
    assert manifest["candidate_identity"] == expected
    for key in ("grammar_identity", "tokenizer_identity", "preflight_source_identity"):
        assert manifest[key] == candidate[key]


def test_real_tokenizer_profile_is_complete_and_zero_inference():
    profile = json.loads((EVIDENCE / "real-tokenizer-preflight.json").read_text("utf-8"))
    assert profile["result"] == "PASS" and profile["tokenizer_vocabulary_size"] == 131072
    assert sum(stream["tokens"] for stream in profile["streams"]) == profile["token_transitions_checked"] == 1160
    assert all(stream["decoded_exact"] and not stream["invalid_next_token_indices"] for stream in profile["streams"])
    assert all(stream["terminal_state"] and stream["eos_only_after_terminal"] for stream in profile["streams"])
    assert profile["model_imported"] is profile["model_load_started"] is profile["inference_started"] is False
    assert profile["model_calls"] == profile["provider_calls"] == profile["runner_calls"] == 0


def test_bound_source_and_projector_hashes_are_current():
    candidate = json.loads(CANDIDATE.read_text("utf-8"))
    paths = {"preflight_source_identity": "src/pastila_scout/experimental_core_v1_2_stage_p_scope_graph_tokenizer_preflight.py",
             "trie_projector_identity": "src/pastila_scout/semantic_admission_v2/stage_p_trie_projector_v1.py",
             "base_trie_projector_identity": "src/pastila_scout/semantic_admission_v2/gate_f_trie_projector_v1.py"}
    for key, relative in paths.items():
        assert candidate[key] == "sha256:" + hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def test_candidate_grants_no_downstream_authority():
    candidate = json.loads(CANDIDATE.read_text("utf-8"))
    assert not any(candidate["authority"].values())
