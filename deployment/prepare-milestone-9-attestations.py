"""Create truthful attestation-only subjects from an offline-verified proof."""

from __future__ import annotations

import json
import os
import hashlib
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OBJECTS = ROOT / "deployment" / "milestone-9"
OUTPUT = ROOT / "milestone-9-output"


def write(name: str, value: dict[str, object]) -> None:
    (OUTPUT / name).write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8", newline="\n",
    )


def common() -> dict[str, object]:
    release = json.loads((OBJECTS / "release.json").read_bytes())
    proof = json.loads((OBJECTS / "proof.json").read_bytes())
    head = os.environ.get("GITHUB_SHA", "")
    if len(head) != 40 or any(c not in "0123456789abcdef" for c in head):
        raise ValueError("activation commit")
    return {
        "mode": "ATTESTATION_ONLY",
        "activation_commit": head,
        "release_identity": release["release_identity"],
        "rfc3161_proof_identity": proof["proof_identity"],
        "publisher_metadata_acquired": False,
        "registry_metadata_acquired": False,
        "push_to_registry": False,
    }


def prepare_initiation() -> None:
    if OUTPUT.exists():
        raise ValueError("attestation output already exists")
    OUTPUT.mkdir()
    value = common()
    write("initiation.json", {"schema": "PASTILA_MILESTONE_9_INITIATION_V1", **value})
    write("initiation-predicate.json", value)


def prepare_final(bundle_input: Path) -> None:
    if not OUTPUT.is_dir() or (OUTPUT / "final.json").exists():
        raise ValueError("attestation phase order")
    runner_temp = Path(os.environ.get("RUNNER_TEMP", "")).resolve(strict=True)
    if bundle_input.is_symlink():
        raise ValueError("initiation bundle containment")
    bundle = bundle_input.resolve(strict=True)
    if not bundle.is_file() or not bundle.is_relative_to(runner_temp):
        raise ValueError("initiation bundle containment")
    bundle_bytes = bundle.read_bytes()
    if not bundle_bytes:
        raise ValueError("initiation bundle empty")
    value = {
        **common(),
        "initiation_bundle_sha256": hashlib.sha256(bundle_bytes).hexdigest(),
        "initiation_bundle_length": len(bundle_bytes),
    }
    write("final.json", {"schema": "PASTILA_MILESTONE_9_FINAL_V1", **value})
    write("final-predicate.json", value)


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--prepare-initiation", action="store_true")
    modes.add_argument("--prepare-final", type=Path)
    args = parser.parse_args()
    if args.prepare_initiation:
        prepare_initiation()
    else:
        prepare_final(args.prepare_final)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
