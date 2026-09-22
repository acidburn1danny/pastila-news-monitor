"""Read-only physical preflight for six distinct future A1/A2 outputs."""

from __future__ import annotations

import argparse
import json
import stat
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from audit_editor_core_bridge_development_causal_pilot import audit as audit_pilot
from build_editor_core_editorial_mechanics_bridge import canonical, sha
from preflight_editor_core_editorial_bridge import preflight as bridge_preflight
from launch_editor_core_v10_v12_targeted_r6_zero_step import output_snapshot, sha_file

SLUGS = ("a1-seed-271828", "a1-seed-314159", "a1-seed-161803",
         "a2-seed-271828", "a2-seed-314159", "a2-seed-161803")


def completed_output(path: Path, slug: str) -> tuple[int, int]:
    if path.is_symlink() or not path.is_dir():
        raise ValueError("completed output directory")
    if {p.name for p in path.iterdir()} != {"adapter", "checkpoint-000012", "training-receipt.json"}:
        raise ValueError("completed output top-level closure")
    receipt_path = path / "training-receipt.json"
    if receipt_path.is_symlink() or not receipt_path.is_file():
        raise ValueError("completed output receipt missing")
    receipt = json.loads(receipt_path.read_bytes())
    identity = receipt.pop("receipt_identity", None)
    arm, seed_text = slug.split("-seed-", 1)
    if (identity != sha(canonical(receipt)) or receipt.get("output_slug") != slug
            or receipt.get("arm") != arm.upper() or receipt.get("seed") != int(seed_text)
            or receipt.get("optimizer_steps") != 12 or receipt.get("holdout_used") is not False
            or receipt.get("parent_sha256") != "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"):
        raise ValueError("completed output identity or scope")
    checkpoint = path / "checkpoint-000012"
    if checkpoint.is_symlink() or not (checkpoint / "checkpoint.json").is_file() or not (path / "adapter").is_dir():
        raise ValueError("completed output checkpoint closure")
    checkpoint_record = json.loads((checkpoint / "checkpoint.json").read_bytes())
    checkpoint_identity = checkpoint_record.pop("checkpoint_identity", None)
    if (checkpoint_identity != sha(canonical(checkpoint_record))
            or receipt.get("checkpoint_identities") != [checkpoint_identity]
            or checkpoint_record.get("state_sha256") != sha_file(checkpoint / "training-state.pt")
            or checkpoint_record.get("output_slug") != slug):
        raise ValueError("completed checkpoint identity")
    return path.stat().st_dev, path.stat().st_ino


def inspect_outputs(root: Path, target_slug: str) -> tuple[tuple[int, int], ...]:
    if root.is_symlink() or not root.is_dir() or {p.name for p in root.iterdir()} != set(SLUGS):
        raise ValueError("six-run output root closure")
    if root.stat().st_uid != 0 or stat.S_IMODE(root.stat().st_mode) != 0o700:
        raise ValueError("output root ownership or permissions")
    if target_slug not in SLUGS:
        raise ValueError("target arm/seed")
    found = []
    for slug in SLUGS:
        path = root / slug
        if path.is_symlink() or not path.is_dir():
            raise ValueError("output directory substitution")
        if path.stat().st_uid != 0 or stat.S_IMODE(path.stat().st_mode) != 0o700:
            raise ValueError("output ownership or permissions")
        if slug == target_slug or not any(path.iterdir()):
            found.append(output_snapshot(path))
        else:
            found.append(completed_output(path, slug))
    snapshots = tuple(found)
    if len(set(snapshots)) != 6:
        raise ValueError("output physical identity overlap")
    return snapshots


def zero_step(model: Path, checkpoint: Path, rootfs: Path, snapshot: Path, outputs: Path,
              target_slug: str) -> dict:
    pilot = audit_pilot()
    before = inspect_outputs(outputs, target_slug)
    technical = bridge_preflight(model, checkpoint, rootfs, snapshot, outputs / target_slug)
    after = inspect_outputs(outputs, target_slug)
    if before != after or technical["status"] != "PASS_LOCAL_TECHNICAL_PREFLIGHT_ABLATIONS_STILL_BLOCKED":
        raise ValueError("physical zero-step drift")
    core = {"schema": "editor-core-bridge-causal-pilot-zero-step", "schema_version": 1,
            "status": "PASS_TECHNICAL_ZERO_STEP_REAL_RUN_AUTHORITY_STILL_BLOCKED",
            "pilot_gate_identity": pilot["fixture_gate_identity"],
            "base_boundary_identity": technical["boundary_identity"],
            "technical_receipt_identity": technical["receipt_identity"],
            "outputs": list(SLUGS), "target_slug": target_slug,
            "target_entries_before": 0, "target_entries_after": 0,
            "distinct_physical_outputs": 6, "model_loaded": False, "inference": False,
            "optimizer_created": False, "optimizer_steps": 0, "training_performed": False,
            "real_run_authorized": False}
    return {**core, "receipt_identity": sha(canonical(core)),
            "ephemeral_output_observations": [list(item) for item in before]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--parent-checkpoint", type=Path, required=True)
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--driver-snapshot", type=Path, required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--target-slug", choices=SLUGS, required=True)
    args = parser.parse_args()
    print(json.dumps(zero_step(args.model, args.parent_checkpoint, args.rootfs,
                               args.driver_snapshot, args.outputs, args.target_slug), sort_keys=True))
