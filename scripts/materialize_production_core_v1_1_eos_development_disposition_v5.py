"""Reclassify durable V5 development observations against the published gate only."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True).encode()


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: disposition DEVELOPMENT_OUTPUT")
    root = Path(sys.argv[1]).resolve(strict=True)
    receipt = json.loads((root / "gate-receipt.json").read_bytes())
    rows = [json.loads((root / f"{index:03d}.json").read_bytes()) for index in range(1, 49)]
    if len(rows) != 48 or [row["index"] for row in rows] != list(range(1, 49)):
        raise SystemExit("development observation closure mismatch")
    passed = all(
        row["terminal_eos"]
        and row["canonical_json"]
        and row["repeated_8gram_ceiling"] <= 3
        for row in rows
    )
    inventory = [
        {"path": f"{index:03d}.json", "sha256": hashlib.sha256((root / f"{index:03d}.json").read_bytes()).hexdigest()}
        for index in range(1, 49)
    ]
    core = {
        "schema": "pastila-production-core-v1.1-eos-development-gate-disposition",
        "schema_version": 5,
        "materialization": receipt["materialization"],
        "superseded_gate_identity": receipt["gate_identity"],
        "adapter_sha256": receipt["adapter_sha256"],
        "development_sha256": receipt["development_sha256"],
        "observation_inventory": inventory,
        "terminal_eos_passed": sum(row["terminal_eos"] for row in rows),
        "canonical_json_passed": sum(row["canonical_json"] for row in rows),
        "anti_repetition_passed": sum(row["repeated_8gram_ceiling"] <= 3 for row in rows),
        "exact_target_diagnostic_only": sum(row["exact_target"] for row in rows),
        "status": "PASS" if passed else "FAIL_CLOSED",
        "qualification_attempt_consumed": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    value = {**core, "disposition_identity": hashlib.sha256(canonical(core)).hexdigest()}
    target = root / "gate-disposition.json"
    if target.exists() or target.is_symlink():
        raise SystemExit("development disposition collision")
    with target.open("xb") as handle:
        handle.write(canonical(value))
        handle.flush()
        __import__("os").fsync(handle.fileno())
    print(value["disposition_identity"])
    if not passed:
        raise SystemExit("development disposition failed closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
