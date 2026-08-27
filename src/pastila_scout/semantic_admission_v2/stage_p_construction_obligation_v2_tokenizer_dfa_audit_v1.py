"""Phases 5-7 of the V2 tokenizer/DFA audit; zero inference, no projector."""
from __future__ import annotations

import hashlib
import json
import platform
import statistics
import sys
import time
import types
from pathlib import Path


ROOT = Path("/mnt/c/Projects/pastila-news-monitor")
MODEL = Path("/home/pastila/PastilaAcida-Model-Lab/experimental-0.1/model-cache/huggingface/models--mistralai--Ministral-3-14B-Instruct-2512-BF16/snapshots/3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
EXPECTED_IDENTITY = "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"


def _decode(tokenizer, ids) -> str:
    return tokenizer.decode(ids, skip_special_tokens=True,
                            clean_up_tokenization_spaces=False)


def _identity(size: int) -> str:
    return "sha256:" + hashlib.sha256(f"{MODEL}\n{size}".encode()).hexdigest()


def main() -> None:
    started = time.perf_counter()
    sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "tests"))
    if "pytest" not in sys.modules:
        stub = types.ModuleType("pytest")
        stub.mark = types.SimpleNamespace(
            parametrize=lambda *args, **kwargs: (lambda function: function))
        stub.raises = lambda *args, **kwargs: None
        sys.modules["pytest"] = stub
    from transformers import AutoTokenizer
    from test_semantic_admission_v2_stage_p_construction_obligation_constraint_v2 import (
        _case_context, _valid_text,
    )
    from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_constraint_v2 import (
        StagePConstructionObligationConstraintStateV2 as State,
    )
    from pastila_scout.semantic_admission_v2.stage_p_role_coherence_constraint_v1 import (
        StagePRoleCoherenceConstraintViolationV1,
    )

    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    if len(tokenizer) != 131072 or _identity(len(tokenizer)) != EXPECTED_IDENTITY:
        raise SystemExit("TOKENIZER_IDENTITY_MISMATCH")
    context, _, _ = _case_context(); raw = _valid_text(context)
    positions = {
        "INITIAL": 0,
        "LITERAL": 1,
        "CHOICE": raw.index('"overall_disposition":"') + len('"overall_disposition":"'),
        "STRING": raw.index('"role_basis":"') + len('"role_basis":"'),
        "V2_REFERENCE": raw.index('"candidate_span_ref":') + len('"candidate_span_ref":'),
        "AFTER_ENTRY": raw.index('},{"entry_id":"P2"') + 1,
        "TERMINAL": len(raw),
    }
    prefixes = {name: raw[:position] for name, position in positions.items()}
    special = set(tokenizer.all_special_ids); eos = tokenizer.eos_token_id
    pieces = {item: _decode(tokenizer, [item]) for item in range(len(tokenizer))}
    excluded = (special - {eos}) | {item for item, piece in pieces.items() if piece == ""}
    rows = []; callback_times = []; false_accepts = false_rejects = suffix_mismatches = 0
    for name, prefix in prefixes.items():
        prefix_ids = tuple(tokenizer.encode(prefix, add_special_tokens=False))
        decoded_prefix = _decode(tokenizer, prefix_ids)
        if decoded_prefix != prefix:
            raise SystemExit(f"PREFIX_ROUNDTRIP_MISMATCH:{name}")
        state = State.for_context(context).feed(prefix)
        expected_mode = "TERMINAL" if state.terminal else state.mode
        full_allowed = set(); context_free_allowed = set(); state_started = time.perf_counter()
        for token_id, piece in pieces.items():
            if token_id in excluded or token_id == eos:
                continue
            candidate = _decode(tokenizer, (*prefix_ids, token_id))
            if not candidate.startswith(prefix):
                suffix_mismatches += 1
                continue
            suffix = candidate[len(prefix):]
            if suffix != piece:
                suffix_mismatches += 1
            try:
                state.feed(suffix); full_allowed.add(token_id)
            except StagePRoleCoherenceConstraintViolationV1:
                pass
            try:
                state.feed(piece); context_free_allowed.add(token_id)
            except StagePRoleCoherenceConstraintViolationV1:
                pass
        if state.terminal:
            full_allowed.add(eos); context_free_allowed.add(eos)
        false_accepts += len(context_free_allowed - full_allowed)
        false_rejects += len(full_allowed - context_free_allowed)
        elapsed = time.perf_counter() - state_started; callback_times.append(elapsed)
        rows.append({"state": name, "dfa_mode": expected_mode,
                     "allowed_token_count": len(full_allowed),
                     "sets_equal": full_allowed == context_free_allowed,
                     "eos_allowed": eos in full_allowed,
                     "seconds": round(elapsed, 6)})
    passed = not false_accepts and not false_rejects and not suffix_mismatches
    result = {
        "schema_name": "pastila-semantic-admission-v2-stage-p-construction-obligation-v2-tokenizer-dfa-audit",
        "schema_version": "1.0.0-evaluation.1",
        "result": "PASS_CONTEXT_FREE_TOKEN_PIECES_EQUIVALENT_FOR_FROZEN_MATRIX" if passed else "FAIL_CLOSED",
        "plan_identity": "94879e032a47beedd2e5035dccf36f2b3922b093aaff67be014f408db6c9006a",
        "tokenizer_identity": EXPECTED_IDENTITY, "vocabulary_size": len(tokenizer),
        "states": rows, "state_count": len(rows),
        "false_accepts": false_accepts, "false_rejects": false_rejects,
        "contextual_suffix_mismatches": suffix_mismatches,
        "eos_only_at_terminal": all(row["eos_allowed"] == (row["state"] == "TERMINAL") for row in rows),
        "special_and_empty_tokens_excluded": True,
        "maximum_state_matrix_seconds": round(max(callback_times), 6),
        "median_state_matrix_seconds": round(statistics.median(callback_times), 6),
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "cache_characterization": "NO_PROJECTOR_OR_CACHE_OBJECT_CREATED; cache isolation remains a future implementation verification obligation",
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "pydantic": __import__("pydantic").__version__},
        "activity": {"tokenizer_loads": 1, "model_loads": 0, "model_calls": 0,
                     "provider_calls": 0, "inference_calls": 0, "projector_objects": 0,
                     "probe_constructions": 0, "probe_executions": 0},
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    if not passed or not result["eos_only_at_terminal"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
