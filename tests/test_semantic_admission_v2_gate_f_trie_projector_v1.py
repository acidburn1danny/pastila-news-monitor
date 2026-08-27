from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.gate_f_constraint_v1 import GateFConstraintStateV1
from pastila_scout.semantic_admission_v2.gate_f_trie_projector_v1 import GateFTokenTrieProjectorOptimizedV1

ROOT = Path(__file__).resolve().parents[1]
FAIL = '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"FSEM_UNSUPPORTED_CAUSALITY","status":"DECISIVE","candidate_span":"din cauza","authority_support":null,"unsupported_proposition":"x","confidence":0.9}]}'


def test_cache_normalizes_irrelevant_string_history_but_not_limit_proximity() -> None:
    pieces = {0: "<eos>", 1: "x", 2: 'x"', 3: "\\n"}
    trie = GateFTokenTrieProjectorOptimizedV1(token_pieces=pieces, eos_token_id=0)
    start = FAIL.index("din cauza")
    first = GateFConstraintStateV1().feed(FAIL[:start])
    second = first.feed("din")
    trie.prewarm([first])
    size = trie.cache_size
    assert trie.allowed_token_ids(second) == trie.allowed_token_ids(first)
    assert trie.cache_size == size
    with pytest.raises(ValueError, match="EMPTY_ALLOWED_TOKEN_SET"):
        trie.allowed_token_ids(replace(second, characters=8000))


def test_final_trie_preflight_is_oracle_equivalent_and_within_bounds() -> None:
    value = json.loads((ROOT / ".semantic-admission-v2-gate-f-trie-projection-v1-evidence/preflight-v4.json").read_text(encoding="utf-8"))
    assert value["result"] == "PASS"
    assert value["all_states_equivalent"] is True
    assert value["non_string_cold_performance_pass"] is True
    assert value["string_prewarm_pass"] is True
    assert value["cached_string_performance_pass"] is True
    assert all(item["equivalent"] and item["cache_reused"] for item in value["varied_string_histories"])
    assert value["model_calls"] == value["provider_calls"] == 0
