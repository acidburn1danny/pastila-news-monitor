from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


repo = Path(sys.argv[1]).resolve()
relative = [
    "docs/artifacts/vnext-voice-owner-gold-pack01-v1-admission.jsonl",
    "docs/artifacts/vnext-voice-owner-gold-pack01-v1-train-successor.jsonl",
    "docs/artifacts/vnext-voice-owner-gold-pack01-v1-validation-successor.jsonl",
    "docs/artifacts/vnext-voice-owner-gold-pack01-v1-dataset-successor.json",
    "docs/artifacts/vnext-voice-owner-gold-pack01-v1-backlog-delta.json",
    "docs/artifacts/vnext-voice-owner-gold-pack01-v1-audit.json",
]


def hashes() -> dict[str, str]:
    return {name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in relative}


before = hashes()
subprocess.run([sys.executable, str(repo / "scripts/build_vnext_voice_owner_gold_pack01_v1.py"), str(repo)], check=True, stdout=subprocess.DEVNULL)
after = hashes()
assert before == after
print("DETERMINISTIC_REBUILD=PASS")
for name, digest in after.items():
    print(f"{digest}  {name}")
