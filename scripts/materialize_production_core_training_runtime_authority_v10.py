"""Materialize the audited dual-successor V10 training authority."""

from __future__ import annotations

import json
from pathlib import Path

from pastila_scout.production_core_training_runtime_authority_v10 import build_authority, expected_observation

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-training-runtime-authority-v10.json"


def main() -> int:
    value = build_authority(expected_observation())
    raw = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
    if OUTPUT.exists() and (OUTPUT.is_symlink() or OUTPUT.read_bytes() != raw):
        raise SystemExit("published V10 training authority differs")
    if not OUTPUT.exists():
        OUTPUT.write_bytes(raw)
    print(value["training_runtime_authority_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
