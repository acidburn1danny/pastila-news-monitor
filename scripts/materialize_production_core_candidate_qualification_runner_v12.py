"""Materialize the V12 runner by replacing only stale V3 authority bindings."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/production_core_candidate_qualification_runner_v3.py"
SOURCE_SHA256 = "ad29f2820159a7f47199a572db6c3f9a42b8664e0f2e3959d618a06513ad695f"
CHANGES = {
    "ac58e53492c58f635defad01009769e948819f10733c1473ea11ecf8df29107c": "813131dc9cae57a66f216957475479e716594c46a67f77783122ff955aa7ee32",
    "a8c0f6778f6d218cfdec47b53f87eb8dfc4af2c55077f559983e4331876b3ab8": "8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f",
    "9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc": "91c84e9ab10cbecdfdd7e255b133c56263feb546d55d7e1ea01362f9be5567bb",
    "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17": "70e125c8fa6e58f3864419bec34f6685a95bcb7bbfb9455838aaf593d01fac36",
    "b7af3517a14e987efa344e9cd9c7bcbbdd9ddb3656cc9060e72fdca71ca7c8d2": "a2bfb6b3ed0f9d77bcc54ed7be0c11380b62b6df0863e2ef41302333f65688d7",
}


def build() -> bytes:
    raw = SOURCE.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA256:
        raise ValueError("V3 runner source drift")
    text = raw.decode("utf-8")
    for old, new in CHANGES.items():
        if text.count(old) != 1:
            raise ValueError(f"V12 runner projection witness mismatch: {old}")
        text = text.replace(old, new)
    return text.encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    raw = build()
    if options.output.exists() and (options.output.is_symlink() or options.output.read_bytes() != raw):
        raise SystemExit("published V12 runner differs")
    if not options.output.exists():
        options.output.write_bytes(raw)
    print(hashlib.sha256(raw).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
