"""Read-only comparator for closed targeted holdout inference outputs."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

RESPONSE_KEYS = ["schema", "schema_version", "case_id", "request_identity", "output_type", "outcome", "text", "claim_bindings", "abstention_code"]


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def audit(output: Path, answer_key: Path) -> dict[str, object]:
    keys = {row["example_id"]: row for row in (json.loads(line) for line in answer_key.read_bytes().splitlines())}
    rows = [json.loads((output / f"{index:03d}.json").read_bytes()) for index in range(1, 33)]
    if len(keys) != 32 or len({row["example_id"] for row in rows}) != 32:
        raise ValueError("evaluation closure mismatch")
    counts: Counter[str] = Counter()
    exact = 0
    structural = 0
    failures: Counter[str] = Counter()
    for row in rows:
        key = keys[row["example_id"]]
        expected = key["assistant_target"]
        exact += row["response"] == expected
        try:
            parsed = json.loads(row["response"])
            canonical_json = json.dumps(parsed, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode() == row["response"].encode()
            shape = list(parsed) == RESPONSE_KEYS
            bound = parsed.get("case_id") == row["example_id"] and parsed.get("request_identity") == row["request_identity"]
            valid = canonical_json and shape and bound and row["terminal_eos"] and row["within_byte_ceiling"] and row["nfc"]
        except (ValueError, TypeError):
            valid = False
        structural += valid
        counts[key["failure_class"]] += 1
        if row["response"] != expected:
            failures[key["failure_class"]] += 1
    core = {
        "schema": "pastila-editor-core-targeted-holdout-audit",
        "schema_version": 1,
        "candidate": rows[0]["candidate"],
        "rows": 32,
        "structural_passed": structural,
        "exact_target_passed": exact,
        "failure_class_counts": dict(sorted(counts.items())),
        "failure_class_mismatches": dict(sorted(failures.items())),
        "answer_key_sha256": sha(answer_key.read_bytes()),
        "status": "PASS_COMPLETE" if structural == 32 else "FAIL_CLOSED",
        "training_performed": False,
    }
    return {**core, "audit_identity": sha(canonical(core))}
