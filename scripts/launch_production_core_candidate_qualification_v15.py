"""Single explicit V15 entry; consumption is delegated to signed executor."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("recovery", "private", "backup", "v13-terminal", "terminal", "rootfs", "snapshot", "unicode-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--consume-attempt", action="store_true")
    args = parser.parse_args()
    target = ("preflight_production_core_candidate_qualification_v15.py" if args.preflight_only
              else "execute_production_core_candidate_qualification_v15.py")
    forwarded = [sys.executable, str(Path(__file__).with_name(target))]
    for name in ("recovery", "private", "backup", "v13_terminal", "terminal", "rootfs", "snapshot", "unicode_root", "output"):
        forwarded.extend(("--" + name.replace("_", "-"), str(getattr(args, name))))
    if args.consume_attempt:
        forwarded.append("--consume-attempt")
    return subprocess.run(forwarded, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
