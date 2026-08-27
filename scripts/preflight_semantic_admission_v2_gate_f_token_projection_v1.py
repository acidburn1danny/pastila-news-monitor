"""WSL-side exhaustive tokenizer-only projection and performance preflight."""
from __future__ import annotations

import json
import importlib.util
import sys
import time
from pathlib import Path

from transformers import AutoTokenizer

MODULE_PATH = Path("/mnt/c/Projects/pastila-news-monitor/src/pastila_scout/semantic_admission_v2/gate_f_constraint_v1.py")
SPEC = importlib.util.spec_from_file_location("gate_f_constraint_v1_standalone", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("constraint module cannot be loaded")
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
GateFConstraintStateV1 = MODULE.GateFConstraintStateV1
GateFTokenProjectorV1 = MODULE.GateFTokenProjectorV1

PASS = '{"gate_id":"FACTUAL_SEMANTIC","decision":"PASS","reason_records":[]}'
FAIL = '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"FSEM_UNSUPPORTED_CAUSALITY","status":"DECISIVE","candidate_span":"din cauza","authority_support":null,"unsupported_proposition":"cauzalitate nesustinuta","confidence":0.9}]}'


def main() -> None:
    target, model = Path(sys.argv[1]), Path(sys.argv[2])
    tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True)
    vocab_ids = tuple(range(len(tokenizer)))
    projector = GateFTokenProjectorV1(vocabulary_ids=vocab_ids, eos_token_id=tokenizer.eos_token_id, decode=lambda ids: tokenizer.decode(ids, skip_special_tokens=True))
    prefixes = {
        "root": "",
        "decision": '{"gate_id":"FACTUAL_SEMANTIC","decision":"',
        "reason_code": '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"',
        "free_string": '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"FSEM_UNSUPPORTED_CAUSALITY","status":"DECISIVE","candidate_span":"din',
        "confidence": '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"FSEM_UNSUPPORTED_CAUSALITY","status":"DECISIVE","candidate_span":"din cauza","authority_support":null,"unsupported_proposition":"x","confidence":',
    }
    rows = []
    for name, prefix in prefixes.items():
        ids = tokenizer.encode(prefix, add_special_tokens=False)
        decoded = tokenizer.decode(ids, skip_special_tokens=True)
        if decoded != prefix:
            raise RuntimeError(f"representative prefix does not round-trip: {name}")
        state = GateFConstraintStateV1().feed(prefix)
        started = time.perf_counter()
        allowed = projector.allowed_token_ids(ids, state)
        elapsed = time.perf_counter() - started
        pieces = [tokenizer.decode([item], skip_special_tokens=False) for item in allowed[:1000]]
        rows.append({
            "state": name,
            "prefix_token_count": len(ids),
            "allowed_token_count": len(allowed),
            "elapsed_seconds": round(elapsed, 6),
            "tokens_per_second": round(len(vocab_ids) / elapsed, 3),
            "eos_allowed": tokenizer.eos_token_id in allowed,
            "fence_start_allowed": any(piece.startswith("```") for piece in pieces),
            "allowed_ids_sha256_input": allowed,
        })
    terminal = GateFConstraintStateV1().feed(PASS)
    if projector.allowed_token_ids(tokenizer.encode(PASS, add_special_tokens=False), terminal) != (tokenizer.eos_token_id,):
        raise RuntimeError("terminal EOS projection failed")
    canonical_streams = {}
    for name, raw in {"pass": PASS, "fail": FAIL}.items():
        ids = tokenizer.encode(raw, add_special_tokens=False)
        state = GateFConstraintStateV1()
        prior = ""
        for offset in range(len(ids)):
            decoded = tokenizer.decode(ids[:offset + 1], skip_special_tokens=True)
            if not decoded.startswith(prior):
                raise RuntimeError("non-monotonic tokenizer decode")
            state = state.feed(decoded[len(prior):])
            prior = decoded
        canonical_streams[name] = {"token_count": len(ids), "decoded_exact": prior == raw, "terminal": state.can_eos}
    for row in rows:
        import hashlib
        row["allowed_ids_sha256"] = hashlib.sha256(json.dumps(row.pop("allowed_ids_sha256_input"), separators=(",", ":")).encode()).hexdigest()
    result = {
        "schema_name": "pastila-semantic-admission-v2-gate-f-token-projection-preflight",
        "schema_version": "1.0.0",
        "tokenizer_revision": model.name,
        "vocabulary_size": len(vocab_ids),
        "representative_states": rows,
        "canonical_streams": canonical_streams,
        "terminal_only_eos": True,
        "all_representative_states_exclude_eos": all(not row["eos_allowed"] for row in rows),
        "all_representative_states_exclude_fence_start": all(not row["fence_start_allowed"] for row in rows),
        "maximum_projection_seconds": max(row["elapsed_seconds"] for row in rows),
        "model_loaded": False,
        "model_calls": 0,
        "provider_calls": 0,
        "result": "PASS"
    }
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"states": len(rows), "max_seconds": result["maximum_projection_seconds"], "result": result["result"]}, indent=2))


if __name__ == "__main__":
    main()
