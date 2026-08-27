"""WSL tokenizer-only feasibility checks for Gate-F constrained decoding."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from transformers import AutoTokenizer, PrefixConstrainedLogitsProcessor


def main() -> None:
    target, model = Path(sys.argv[1]), Path(sys.argv[2])
    tokenizer = AutoTokenizer.from_pretrained(model, local_files_only=True)
    samples = {
        "pass": '{"gate_id":"FACTUAL_SEMANTIC","decision":"PASS","reason_records":[]}',
        "fail": '{"gate_id":"FACTUAL_SEMANTIC","decision":"FAIL","reason_records":[{"code":"FSEM_UNSUPPORTED_CAUSALITY","status":"DECISIVE","candidate_span":"din cauza","authority_support":null,"unsupported_proposition":"cauzalitate nesustinuta","confidence":0.9}]}',
        "indeterminate": '{"gate_id":"FACTUAL_SEMANTIC","decision":"INDETERMINATE","reason_records":[{"code":"ADMISSION_INDETERMINATE","status":"DECISIVE","candidate_span":null,"authority_support":null,"unsupported_proposition":"autoritate insuficienta","confidence":0.5}]}',
    }
    encoded = {}
    for name, text in samples.items():
        ids = tokenizer.encode(text, add_special_tokens=False)
        decoded = tokenizer.decode(ids, skip_special_tokens=True)
        encoded[name] = {"token_count": len(ids), "round_trip_exact": decoded == text, "first_token_id": ids[0], "last_token_id": ids[-1]}
    vocab = tokenizer.get_vocab()
    opening = []
    fenced = []
    for token, token_id in vocab.items():
        piece = tokenizer.decode([token_id], skip_special_tokens=False)
        if piece.startswith("{"):
            opening.append(token_id)
        if piece.startswith("```"):
            fenced.append(token_id)
    result = {
        "schema_name": "pastila-semantic-admission-v2-gate-f-constraint-tokenizer-feasibility",
        "schema_version": "1.0.0",
        "transformers_native_prefix_constraint_available": PrefixConstrainedLogitsProcessor is not None,
        "tokenizer_revision": model.name,
        "chat_template_sha256": hashlib.sha256(tokenizer.chat_template.encode()).hexdigest(),
        "vocabulary_size": len(vocab),
        "opening_brace_token_ids": sorted(opening),
        "opening_brace_token_count": len(opening),
        "fence_token_ids": sorted(fenced),
        "fence_token_count": len(fenced),
        "first_step_can_exclude_all_fence_tokens": bool(opening) and not bool(set(opening) & set(fenced)),
        "canonical_samples": encoded,
        "all_canonical_samples_round_trip_exact": all(item["round_trip_exact"] for item in encoded.values()),
        "model_loaded": False,
        "model_calls": 0,
        "provider_calls": 0
    }
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("vocabulary_size", "opening_brace_token_count", "fence_token_count", "first_step_can_exclude_all_fence_tokens", "all_canonical_samples_round_trip_exact")}, indent=2))


if __name__ == "__main__":
    main()
