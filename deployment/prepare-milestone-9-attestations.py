"""Create truthful attestation-only subjects from an offline-verified proof."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OBJECTS = ROOT / "deployment" / "milestone-9"
OUTPUT = ROOT / "milestone-9-output"


def write(name: str, value: dict[str, object]) -> None:
    (OUTPUT / name).write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8", newline="\n",
    )


def main() -> int:
    if OUTPUT.exists():
        raise ValueError("attestation output already exists")
    release = json.loads((OBJECTS / "release.json").read_bytes())
    proof = json.loads((OBJECTS / "proof.json").read_bytes())
    head = os.environ.get("GITHUB_SHA", "")
    if len(head) != 40 or any(c not in "0123456789abcdef" for c in head):
        raise ValueError("activation commit")
    OUTPUT.mkdir()
    common = {
        "mode": "ATTESTATION_ONLY",
        "activation_commit": head,
        "release_identity": release["release_identity"],
        "rfc3161_proof_identity": proof["proof_identity"],
        "publisher_metadata_acquired": False,
        "registry_metadata_acquired": False,
        "push_to_registry": False,
    }
    write("initiation.json", {"schema": "PASTILA_MILESTONE_9_INITIATION_V1", **common})
    write("initiation-predicate.json", common)
    write("final.json", {"schema": "PASTILA_MILESTONE_9_FINAL_V1", **common})
    write("final-predicate.json", {**common, "initiation_required": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
