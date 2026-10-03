from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


FILES = [
    "docs/artifacts/vnext-voice-owner-gold-pack02-v1-admission.jsonl",
    "docs/artifacts/vnext-voice-owner-gold-pack02-v1-admitted-records.jsonl",
    "docs/artifacts/vnext-voice-owner-gold-pack02-v1-train-successor.jsonl",
    "docs/artifacts/vnext-voice-owner-gold-pack02-v1-validation-successor.jsonl",
    "docs/artifacts/vnext-voice-owner-gold-pack02-v1-dataset-successor.json",
    "docs/artifacts/vnext-voice-owner-gold-pack02-v1-backlog.json",
    "docs/artifacts/vnext-voice-owner-gold-pack02-v1-audit.json",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(repo: Path) -> None:
    before = {name: digest(repo / name) for name in FILES}
    subprocess.run([sys.executable, str(repo / "scripts/build_vnext_voice_owner_gold_pack02_v1.py"), str(repo)], check=True, capture_output=True, text=True)
    after = {name: digest(repo / name) for name in FILES}
    assert before == after
    print("PASS deterministic rebuild: 7/7 generated artifacts byte-identical")


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
