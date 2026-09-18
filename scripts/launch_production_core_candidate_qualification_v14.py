"""Executable V14 launch gate with a read-only pre-consumption mode."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from preflight_production_core_candidate_qualification_v14 import preflight


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recovery-root", type=Path, required=True)
    parser.add_argument("--private-root", type=Path, required=True)
    parser.add_argument("--backup-root", type=Path, required=True)
    parser.add_argument("--terminal-root", type=Path, required=True)
    parser.add_argument("--unicode-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--consume-attempt", action="store_true")
    args = parser.parse_args()
    result = preflight(args.recovery_root, args.private_root, args.backup_root, args.terminal_root, args.unicode_root, args.output)
    print(json.dumps(result, sort_keys=True))
    if args.consume_attempt:
        subprocess.run([
            sys.executable, str(Path(__file__).with_name("execute_production_core_candidate_qualification_v14.py")),
            "--resolution", str(args.recovery_root / "v12-executor-resolution.json"),
            "--secret", str(args.private_root / "candidate-alias-secret-v13.json"),
            "--unicode-authority-root", str(args.unicode_root),
            "--output", str(args.output),
        ], check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
