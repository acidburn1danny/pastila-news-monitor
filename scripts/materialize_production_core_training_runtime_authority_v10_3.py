"""Materialize the V10.3 training authority."""

import json
from pathlib import Path

from pastila_scout.production_core_training_runtime_authority_v10_3 import build_authority, expected_observation

OUTPUT = Path(__file__).resolve().parents[1] / "docs/artifacts/production-core-training-runtime-authority-v10-3.json"


def main() -> int:
    value = build_authority(expected_observation())
    raw = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
    if OUTPUT.exists() and OUTPUT.read_bytes() != raw:
        raise SystemExit("published V10.3 training authority differs")
    OUTPUT.write_bytes(raw)
    print(value["training_runtime_authority_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
