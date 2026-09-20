"""Read-only closure and comparison audit for R3 holdout outputs."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

EXPECTED_ROWS = 12
RESPONSE_KEYS = ["schema", "schema_version", "case_id", "request_identity", "output_type", "outcome", "text", "claim_bindings", "abstention_code"]
SEMANTIC_MARKERS = {
    "ATTRIBUTION_DENIAL_FINALITY": (("suspiciun",), ("ar fi",), ("neag",), ("hotărâre finală",)),
    "PRELIMINARY_CONTEST_PENDING": (("provizori",), ("ar fi",), ("obiec",), ("nesoluționat", "nesoluționată")),
}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def semantic_case_passes(key: dict[str, object], parsed: dict[str, object]) -> bool:
    pattern = key.get("diagnostic_pattern")
    groups = SEMANTIC_MARKERS.get(pattern)
    text = parsed.get("text")
    if groups is None or not isinstance(text, str):
        raise ValueError("unsupported semantic evaluation contract")
    lowered = text.casefold()
    return all(any(marker in lowered for marker in alternatives) for alternatives in groups)


def audit(output: Path, answer_key: Path, candidate: str, adapter_sha256: str, requests_sha256: str, runner_sha256: str) -> dict[str, object]:
    expected_files = {f"{index:03d}.json" for index in range(1, EXPECTED_ROWS + 1)} | {"inference-receipt.json"}
    if {path.name for path in output.iterdir()} != expected_files or any(path.is_symlink() for path in output.iterdir()):
        raise ValueError("output file closure mismatch")
    keys = {row["example_id"]: row for row in (json.loads(line) for line in answer_key.read_bytes().splitlines())}
    rows = [json.loads((output / f"{index:03d}.json").read_bytes()) for index in range(1, EXPECTED_ROWS + 1)]
    receipt = json.loads((output / "inference-receipt.json").read_bytes())
    receipt_core = {key: value for key, value in receipt.items() if key != "receipt_identity"}
    if receipt.get("receipt_identity") != sha(canonical(receipt_core)):
        raise ValueError("inference receipt identity mismatch")
    expected_receipt = {"candidate": candidate, "adapter_sha256": adapter_sha256, "requests_sha256": requests_sha256, "runner_sha256": runner_sha256, "rows": EXPECTED_ROWS, "answer_key_accessed": False, "training_performed": False, "optimizer_activity": False}
    if any(receipt.get(key) != value for key, value in expected_receipt.items()):
        raise ValueError("inference receipt binding mismatch")
    if len(keys) != EXPECTED_ROWS or len({row["example_id"] for row in rows}) != EXPECTED_ROWS:
        raise ValueError("evaluation closure mismatch")
    exact = structural = semantic = 0
    counts: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    field_matches: Counter[str] = Counter()
    exact_by_class: Counter[str] = Counter()
    semantic_by_pattern: Counter[str] = Counter()
    semantic_failures: list[str] = []
    for index, row in enumerate(rows, 1):
        if row.get("index") != index or row.get("candidate") != candidate or row.get("response_sha256") != sha(row.get("response", "").encode()):
            raise ValueError("observation binding mismatch")
        key = keys.get(row["example_id"])
        if key is None or key.get("request_identity") != row.get("request_identity"):
            raise ValueError("answer-key binding mismatch")
        expected = key["assistant_target"]
        exact += row["response"] == expected
        parsed: dict[str, object] = {}
        expected_parsed: dict[str, object] = json.loads(expected)
        try:
            parsed = json.loads(row["response"])
            valid = (json.dumps(parsed, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode() == row["response"].encode()
                     and list(parsed) == RESPONSE_KEYS and parsed.get("case_id") == row["example_id"]
                     and parsed.get("request_identity") == row["request_identity"] and row["terminal_eos"]
                     and row["within_byte_ceiling"] and row["nfc"])
        except (ValueError, TypeError):
            valid = False
        structural += valid
        semantic_pass = valid and semantic_case_passes(key, parsed)
        semantic += semantic_pass
        semantic_by_pattern[key["diagnostic_pattern"]] += semantic_pass
        if not semantic_pass:
            semantic_failures.append(row["example_id"])
        counts[key["failure_class"]] += 1
        if row["response"] == expected:
            exact_by_class[key["failure_class"]] += 1
        for field in RESPONSE_KEYS:
            field_matches[field] += parsed.get(field) == expected_parsed.get(field)
        if row["response"] != expected:
            failures[key["failure_class"]] += 1
    core = {
        "schema": "pastila-editor-core-targeted-r3-holdout-audit", "schema_version": 1,
        "candidate": candidate, "rows": EXPECTED_ROWS, "structural_passed": structural,
        "exact_target_passed": exact, "semantic_passed": semantic,
        "semantic_passed_by_pattern": dict(sorted(semantic_by_pattern.items())),
        "semantic_failure_cases": semantic_failures,
        "failure_class_counts": dict(sorted(counts.items())),
        "exact_target_by_failure_class": {name: exact_by_class[name] for name in sorted(counts)},
        "failure_class_mismatches": dict(sorted(failures.items())), "answer_key_sha256": sha(answer_key.read_bytes()),
        "field_matches": dict(sorted(field_matches.items())),
        "inference_receipt_identity": receipt["receipt_identity"],
        "status": "PASS_COMPLETE" if structural == EXPECTED_ROWS else "FAIL_CLOSED", "training_performed": False,
    }
    return {**core, "audit_identity": sha(canonical(core))}


def compare(left: Path, right: Path, answer_key: Path) -> dict[str, object]:
    keys = [json.loads(line) for line in answer_key.read_bytes().splitlines()]
    same_by_class: Counter[str] = Counter()
    changed_by_class: Counter[str] = Counter()
    changed_cases: list[str] = []
    semantic_regressions: list[str] = []
    semantic_improvements: list[str] = []
    for index, key in enumerate(keys, 1):
        left_row = json.loads((left / f"{index:03d}.json").read_bytes())
        right_row = json.loads((right / f"{index:03d}.json").read_bytes())
        if left_row["example_id"] != key["example_id"] or right_row["example_id"] != key["example_id"]:
            raise ValueError("cross-output case binding mismatch")
        bucket = same_by_class if left_row["response"] == right_row["response"] else changed_by_class
        bucket[key["failure_class"]] += 1
        if left_row["response"] != right_row["response"]:
            changed_cases.append(key["example_id"])
        left_semantic = semantic_case_passes(key, json.loads(left_row["response"]))
        right_semantic = semantic_case_passes(key, json.loads(right_row["response"]))
        if left_semantic and not right_semantic:
            semantic_regressions.append(key["example_id"])
        if right_semantic and not left_semantic:
            semantic_improvements.append(key["example_id"])
    core = {
        "schema": "pastila-editor-core-targeted-r3-holdout-comparison", "schema_version": 1,
        "rows": len(keys), "response_equal": sum(same_by_class.values()),
        "response_changed": sum(changed_by_class.values()),
        "equal_by_failure_class": {name: same_by_class[name] for name in sorted(set(same_by_class) | set(changed_by_class))},
        "changed_by_failure_class": {name: changed_by_class[name] for name in sorted(set(same_by_class) | set(changed_by_class))},
        "changed_cases": changed_cases, "semantic_verdict_emitted": False,
        "semantic_regressions": semantic_regressions, "semantic_improvements": semantic_improvements,
    }
    return {**core, "comparison_identity": sha(canonical(core))}


def main() -> int:
    if len(sys.argv) == 5 and sys.argv[1] == "--compare":
        print(json.dumps(compare(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0
    if len(sys.argv) != 7:
        raise SystemExit("usage: auditor OUTPUT ANSWER_KEY CANDIDATE ADAPTER_SHA256 REQUESTS_SHA256 RUNNER_SHA256")
    result = audit(Path(sys.argv[1]), Path(sys.argv[2]), *sys.argv[3:])
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
