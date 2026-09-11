"""Materialize the audited V5 successor training-runtime authority."""

from __future__ import annotations

import json
from pathlib import Path

from pastila_scout.production_core_training_runtime_authority_v5 import (
    build_authority,
    expected_observation,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs/artifacts/production-core-training-runtime-authority-v5.json"


def main() -> int:
    value = build_authority(expected_observation())
    OUTPUT.write_bytes(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n")
    print(value["training_runtime_authority_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
