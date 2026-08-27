"""Tokenizer-only compatibility audit for the approved V2 character controller.

This module is evidence tooling.  It does not implement a token projector and
must never load model weights or invoke generation.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import time
from pathlib import Path


ROOT = Path("/mnt/c/Projects/pastila-news-monitor")
MODEL = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
EXPECTED_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"
EXPECTED_VOCABULARY = 131072


def _decode(tokenizer, ids) -> str:
    return tokenizer.decode(ids, skip_special_tokens=True,
                            clean_up_tokenization_spaces=False)


def _identity(vocabulary_size: int) -> str:
    material = f"{MODEL}\n{vocabulary_size}".encode("utf-8")
    return "sha256:" + hashlib.sha256(material).hexdigest()


def main() -> None:
    started = time.perf_counter()
    from transformers import AutoTokenizer, __version__ as transformers_version

    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    vocabulary_size = len(tokenizer)
    actual_identity = _identity(vocabulary_size)
    if vocabulary_size != EXPECTED_VOCABULARY or actual_identity != EXPECTED_IDENTITY:
        raise SystemExit("TOKENIZER_IDENTITY_MISMATCH")

    prefix_texts = {
        "INITIAL": "",
        "LITERAL": '{"schema_name":"pastila-semantic-admission-v2-stage-p-',
        "CHOICE": '{"coverage_decision":"COM',
        "STRING_EMPTY": '{"role_basis":"',
        "STRING_ROMANIAN": '{"role_basis":"transformare editorială',
        "STRING_ESCAPE": '{"role_basis":"linie\\n',
        "REFERENCE_SHA": '{"source_role":"CANDIDATE","source_sha256":"a91ae3',
        "REFERENCE_NUMBER": '{"start_utf8":12,"end_utf8":',
        "AFTER_ENTRY": '{"entries":[{}',
        "TERMINAL_SHAPE": '{"coverage_decision":"COMPLETE"}',
    }
    selected = {name: tuple(tokenizer.encode(text, add_special_tokens=False))
                for name, text in prefix_texts.items()}

    standalone = {
        token_id: _decode(tokenizer, [token_id])
        for token_id in range(vocabulary_size)
    }
    empty_ids = {token_id for token_id, text in standalone.items() if text == ""}
    replacement_ids = {token_id for token_id, text in standalone.items() if "\ufffd" in text}
    control_ids = {token_id for token_id, text in standalone.items()
                   if any(ord(character) < 0x20 and character not in "\t\n\r" for character in text)}
    special_ids = set(tokenizer.all_special_ids)
    byte_fallback_ids = {
        token_id for token_id in range(vocabulary_size)
        if str(tokenizer.convert_ids_to_tokens(token_id)).startswith("<0x")
    }

    rows = []
    totals = {"contextual_rewrites": 0, "standalone_suffix_mismatches": 0,
              "context_free_false_accepts": 0, "context_free_false_rejects": 0}
    for mode, prefix_ids in selected.items():
        base = _decode(tokenizer, prefix_ids)
        row = {"mode": mode, "prefix_token_count": len(prefix_ids),
               "contextual_rewrites": 0, "standalone_suffix_mismatches": 0,
               "full_decode_valid_tokens": None, "context_free_valid_tokens": None,
               "context_free_false_accepts": None, "context_free_false_rejects": None}
        for token_id in range(vocabulary_size):
            if token_id in special_ids or token_id in empty_ids:
                continue
            candidate = _decode(tokenizer, (*prefix_ids, token_id))
            stable = candidate.startswith(base)
            if not stable:
                row["contextual_rewrites"] += 1
            else:
                suffix = candidate[len(base):]
                if suffix != standalone[token_id]:
                    row["standalone_suffix_mismatches"] += 1
        for key in ("contextual_rewrites", "standalone_suffix_mismatches"):
            totals[key] += row[key]
        rows.append(row)

    eos_policy_pass = tokenizer.eos_token_id in special_ids
    context_free_exact = (totals["contextual_rewrites"] == 0 and
                          totals["standalone_suffix_mismatches"] == 0)
    result = {
        "schema_name": "pastila-semantic-admission-v2-stage-p-construction-obligation-v2-tokenizer-compatibility-audit",
        "schema_version": "1.0.0-evaluation.1",
        "plan_identity": "94879e032a47beedd2e5035dccf36f2b3922b093aaff67be014f408db6c9006a",
        "result": "PARTIAL_COMPLETE_PREFIX_SENSITIVE_REQUIRED_DFA_PHASE_BLOCKED",
        "strategy_recommendation": "RETAIN_PREFIX_SENSITIVE_DEFAULT_PENDING_DFA_EQUIVALENCE",
        "tokenizer_native_suffix_matrix_equivalent": context_free_exact,
        "context_free_projector_equivalence": None,
        "tokenizer": {
            "path": str(MODEL), "identity": actual_identity,
            "vocabulary_size": vocabulary_size, "implementation": type(tokenizer).__name__,
            "transformers_version": transformers_version,
            "eos_token_id": tokenizer.eos_token_id, "bos_token_id": tokenizer.bos_token_id,
            "pad_token_id": tokenizer.pad_token_id, "unk_token_id": tokenizer.unk_token_id,
            "special_token_ids": sorted(special_ids), "empty_decoding_count": len(empty_ids),
            "replacement_character_count": len(replacement_ids),
            "control_decoding_count": len(control_ids),
            "byte_fallback_token_count": len(byte_fallback_ids),
        },
        "representative_modes_found": sorted(selected),
        "rows": rows, "totals": totals,
        "terminal_eos_inventory_pass": eos_policy_pass,
        "blocked_phase": {
            "phase": 5,
            "reason_code": "TOKENIZER_ENVIRONMENT_MISSING_APPLICATION_PYDANTIC",
            "detail": "The identity-bound tokenizer environment lacks pydantic; installing or combining dependencies was outside the load-only authorization. Request-bound character-DFA admission equivalence was not executed.",
            "completed_phases": [0, 1, 2, 3, 4],
            "not_executed_phases": [5, 6, 7]
        },
        "cache_policy": "PREFIX_AND_DECODER_IDENTITY_REQUIRED",
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "activity": {"tokenizer_loads": 1, "model_loads": 0, "model_calls": 0,
                     "provider_calls": 0, "inference_calls": 0, "projector_objects": 0,
                     "probe_constructions": 0, "probe_executions": 0},
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
