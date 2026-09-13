"""Seal byte-equal tokenizer observations from both V10 materializations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-v10-token-materialization-evidence.json"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build(first: Path, second: Path) -> dict[str, object]:
    if first.is_symlink() or second.is_symlink():
        raise ValueError("symlink observation rejected")
    first_raw, second_raw = first.read_bytes(), second.read_bytes()
    if first_raw != second_raw:
        raise ValueError("token observations differ across materializations")
    observed = json.loads(first_raw)
    core = {
        "schema": "pastila-production-core-v10-token-materialization-evidence",
        "schema_version": 1,
        "status": "TWO_MATERIALIZATIONS_BYTE_EXACT",
        "materializations": ["A", "B"],
        "observation_sha256": sha(first_raw),
        "observed": observed,
        "maximum_training_sequence_tokens": 3072,
        "model_loaded": False,
        "inference_performed": False,
        "training_performed": False,
    }
    return {**core, "evidence_identity": sha(canonical(core))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", type=Path, default=ROOT / ".audit-tmp/v10-token-summary-3072.json")
    parser.add_argument("--second", type=Path, default=ROOT / ".audit-tmp/v10-token-summary-3072-B.json")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    value = build(args.first, args.second)
    raw = json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n"
    if args.output.exists() and (args.output.is_symlink() or args.output.read_bytes() != raw):
        raise SystemExit("published materialization evidence differs")
    if not args.output.exists():
        args.output.write_bytes(raw)
    print(value["evidence_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
