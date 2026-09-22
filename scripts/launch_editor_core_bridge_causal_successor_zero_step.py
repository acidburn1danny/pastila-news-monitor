"""Combine published execution authority with technical preflight, without loading a model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from build_editor_core_editorial_mechanics_bridge import canonical, sha
from launch_editor_core_bridge_causal_zero_step import SLUGS, zero_step
from verify_editor_core_bridge_causal_execution_authority import verify


def successor_zero_step(model: Path, checkpoint: Path, rootfs: Path, snapshot: Path,
                        outputs: Path, target_slug: str) -> dict:
    if target_slug not in SLUGS:
        raise ValueError("slot")
    arm, seed_text = target_slug.split("-seed-", 1)
    authority = verify(arm.upper(), int(seed_text))
    technical = zero_step(model, checkpoint, rootfs, snapshot, outputs, target_slug)
    if (technical.get("status") != "PASS_TECHNICAL_ZERO_STEP_REAL_RUN_AUTHORITY_STILL_BLOCKED"
            or technical.get("optimizer_steps") != 0
            or technical.get("model_loaded") is not False
            or technical.get("target_entries_before") != 0
            or technical.get("target_entries_after") != 0):
        raise ValueError("technical preflight")
    core = {"schema": "editor-core-bridge-causal-successor-zero-step", "schema_version": 1,
            "status": "PASS_PUBLISHED_AUTHORITY_AND_TECHNICAL_ZERO_STEP",
            "authority_identity": authority["authority_identity"],
            "published_commit": authority["commit"], "target_slug": target_slug,
            "technical_receipt_identity": technical["receipt_identity"],
            "model_loaded": False, "optimizer_created": False, "optimizer_steps": 0,
            "training_performed": False}
    return {**core, "receipt_identity": sha(canonical(core))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--parent-checkpoint", type=Path, required=True)
    parser.add_argument("--rootfs", type=Path, required=True)
    parser.add_argument("--driver-snapshot", type=Path, required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--target-slug", choices=SLUGS, required=True)
    args = parser.parse_args()
    print(json.dumps(successor_zero_step(args.model, args.parent_checkpoint, args.rootfs,
                                         args.driver_snapshot, args.outputs, args.target_slug), sort_keys=True))
