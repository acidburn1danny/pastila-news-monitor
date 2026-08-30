"""Bind the verified Pilot 01 archive bytes directly into Git objects.

This avoids changing the restrictive ACL inherited during atomic publication.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / ".pilot01-git-object-staging"
PREFIX = "docs/artifacts/humor-mechanics-batch2-development-pilot01-ingestion-v1"
FILES = {
    "access-ledger-segment.json", "archive-receipt.json", "custodial-verification.json",
    "factual-authority-envelope.json", "ingestion-receipt.json", "rights-instrument.json",
    "source-package.json", "source.utf8.txt",
}


def main() -> None:
    if {x.name for x in FOLDER.iterdir() if x.name != ".keep"} != FILES:
        raise SystemExit("archive file set changed")
    for name in sorted(FILES):
        data = (FOLDER / name).read_bytes()
        oid = subprocess.check_output(["git", "hash-object", "-w", "--stdin"], cwd=ROOT, input=data).decode().strip()
        subprocess.run(["git", "update-index", "--add", "--cacheinfo", "100644", oid, f"{PREFIX}/{name}"], cwd=ROOT, check=True)
        print(f"{oid}  {PREFIX}/{name}")


if __name__ == "__main__":
    main()
