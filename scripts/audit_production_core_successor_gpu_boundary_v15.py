"""Audit V15 successor GPU design without an execution or attempt path."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pastila_scout.production_core_isolated_gpu_boundary_v15 import audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal-root", type=Path, required=True)
    parser.add_argument("--rootfs", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.terminal_root, args.rootfs), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
