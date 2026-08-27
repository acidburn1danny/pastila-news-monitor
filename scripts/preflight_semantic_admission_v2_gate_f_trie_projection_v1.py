"""Tokenizer-only equivalence and performance preflight for trie projection."""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

from transformers import AutoTokenizer

MODULE_PATH = Path("/mnt/c/Projects/pastila-news-monitor/src/pastila_scout/semantic_admission_v2/gate_f_constraint_v1.py")
SPEC = importlib.util.spec_from_file_location("gate_f_constraint_v1_trie", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("constraint module cannot be loaded")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
State = MODULE.GateFConstraintStateV1
Oracle = MODULE.GateFTokenProjectorV1
OPTIMIZED_PATH = Path("/mnt/c/Projects/pastila-news-monitor/src/pastila_scout/semantic_admission_v2/gate_f_trie_projector_v1.py")
OPTIMIZED_SPEC = importlib.util.spec_from_file_location("gate_f_trie_projector_v1_standalone", OPTIMIZED_PATH)
if OPTIMIZED_SPEC is None or OPTIMIZED_SPEC.loader is None:
    raise RuntimeError("optimized trie module cannot be loaded")
OPTIMIZED = importlib.util.module_from_spec(OPTIMIZED_SPEC)
sys.modules[OPTIMIZED_SPEC.name] = OPTIMIZED
OPTIMIZED_SPEC.loader.exec_module(OPTIMIZED)
Trie = OPTIMIZED.GateFTokenTrieProjectorOptimizedV1


def main() -> None:
    target, model = Path(sys.argv[1]), Path(sys.argv[2])
    tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True)
    ids = tuple(range(len(tokenizer)))
    special = frozenset(tokenizer.all_special_ids)
    pieces = {item: tokenizer.decode([item], skip_special_tokens=True) for item in ids}
    build_started = time.perf_counter()
    trie = Trie(token_pieces=pieces, eos_token_id=tokenizer.eos_token_id, excluded_token_ids=special - {tokenizer.eos_token_id})
    build_seconds = time.perf_counter() - build_started
    oracle = Oracle(vocabulary_ids=ids, eos_token_id=tokenizer.eos_token_id, decode=lambda values: tokenizer.decode(values, skip_special_tokens=True))
    prefixes = {
        "root": "",
        "decision": '{"gate_id":"FACTUAL_SEMANTIC","decision":"',
        "reason_code": '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"',
        "free_string": '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"FSEM_UNSUPPORTED_CAUSALITY","status":"DECISIVE","candidate_span":"din',
        "confidence": '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"FSEM_UNSUPPORTED_CAUSALITY","status":"DECISIVE","candidate_span":"din cauza","authority_support":null,"unsupported_proposition":"x","confidence":',
    }
    rows = []
    cached_string_continuation = None
    varied_string_rows = []
    for name, prefix in prefixes.items():
        prefix_ids = tokenizer.encode(prefix, add_special_tokens=False)
        if tokenizer.decode(prefix_ids, skip_special_tokens=True) != prefix:
            raise RuntimeError(f"prefix round-trip drift: {name}")
        state = State().feed(prefix)
        oracle_started = time.perf_counter(); expected = set(oracle.allowed_token_ids(prefix_ids, state)); oracle_seconds = time.perf_counter() - oracle_started
        cold_started = time.perf_counter(); actual = set(trie.allowed_token_ids(state)); cold_seconds = time.perf_counter() - cold_started
        warm_started = time.perf_counter(); warm = set(trie.allowed_token_ids(state)); warm_seconds = time.perf_counter() - warm_started
        rows.append({
            "state": name,
            "oracle_count": len(expected),
            "trie_count": len(actual),
            "missing_count": len(expected - actual),
            "extra_count": len(actual - expected),
            "equivalent": actual == expected == warm,
            "oracle_seconds": round(oracle_seconds, 6),
            "trie_cold_seconds": round(cold_seconds, 6),
            "trie_warm_seconds": round(warm_seconds, 9),
        })
        if name == "free_string":
            advanced_state = state.feed("abc")
            advanced_prefix = prefix + "abc"
            advanced_ids = tokenizer.encode(advanced_prefix, add_special_tokens=False)
            advanced_expected = set(oracle.allowed_token_ids(advanced_ids, advanced_state))
            advanced_started = time.perf_counter(); advanced_actual = set(trie.allowed_token_ids(advanced_state)); advanced_seconds = time.perf_counter() - advanced_started
            cached_string_continuation = {
                "oracle_count": len(advanced_expected),
                "trie_count": len(advanced_actual),
                "equivalent": advanced_actual == advanced_expected,
                "seconds": round(advanced_seconds, 9),
                "cache_reused": trie.cache_size == len(rows),
            }
            for label, addition in (("ascii", "abc"), ("spaces_unicode", " cu spații"), ("embedded_backticks", "``` interior"), ("escaped_newline", "\\n")):
                varied_state = state.feed(addition)
                varied_prefix = prefix + addition
                varied_ids = tokenizer.encode(varied_prefix, add_special_tokens=False)
                if tokenizer.decode(varied_ids, skip_special_tokens=True) != varied_prefix:
                    raise RuntimeError(f"varied prefix round-trip drift: {label}")
                varied_expected = set(oracle.allowed_token_ids(varied_ids, varied_state))
                varied_started = time.perf_counter(); varied_actual = set(trie.allowed_token_ids(varied_state)); varied_seconds = time.perf_counter() - varied_started
                varied_string_rows.append({"case": label, "equivalent": varied_actual == varied_expected, "seconds": round(varied_seconds, 9), "cache_reused": trie.cache_size == len(rows)})
    result = {
        "schema_name": "pastila-semantic-admission-v2-gate-f-trie-projection-preflight",
        "schema_version": "1.0.0",
        "tokenizer_revision": model.name,
        "vocabulary_size": len(ids),
        "trie_node_count": trie.trie_node_count,
        "trie_build_seconds": round(build_seconds, 6),
        "states": rows,
        "cached_string_continuation": cached_string_continuation,
        "varied_string_histories": varied_string_rows,
        "all_states_equivalent": all(row["equivalent"] for row in rows) and bool(cached_string_continuation and cached_string_continuation["equivalent"]) and all(row["equivalent"] for row in varied_string_rows),
        "maximum_cold_seconds": max(row["trie_cold_seconds"] for row in rows),
        "maximum_warm_seconds": max(row["trie_warm_seconds"] for row in rows),
        "performance_threshold_seconds": 0.25,
        "non_string_cold_performance_pass": max(row["trie_cold_seconds"] for row in rows if row["state"] != "free_string") <= 0.25,
        "string_prewarm_seconds": next(row["trie_cold_seconds"] for row in rows if row["state"] == "free_string"),
        "string_prewarm_budget_seconds": 2.0,
        "string_prewarm_pass": next(row["trie_cold_seconds"] for row in rows if row["state"] == "free_string") <= 2.0,
        "cached_string_performance_pass": bool(cached_string_continuation and cached_string_continuation["seconds"] <= 0.01 and cached_string_continuation["cache_reused"] and all(row["seconds"] <= 0.01 and row["cache_reused"] for row in varied_string_rows)),
        "warm_performance_pass": max(row["trie_warm_seconds"] for row in rows) <= 0.01,
        "cache_size": trie.cache_size,
        "model_loaded": False,
        "model_calls": 0,
        "provider_calls": 0,
    }
    result["result"] = "PASS" if all((result["all_states_equivalent"], result["non_string_cold_performance_pass"], result["string_prewarm_pass"], result["cached_string_performance_pass"], result["warm_performance_pass"])) else "FAIL"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("all_states_equivalent", "maximum_cold_seconds", "maximum_warm_seconds", "result")}, indent=2))


if __name__ == "__main__":
    main()
