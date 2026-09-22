"""Read-only, byte-exact projection of the seven future Bridge training arms."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_editor_core_editorial_mechanics_bridge import audit as audit_corpus
from build_editor_core_editorial_mechanics_bridge import ART, PREFIX, canonical, compact, sha

PUBLISHED_COMMIT = "94880823ac060539f21b1df4b8374b04a484ad78"
PUBLISHED_MANIFEST = "a4649f59a5a536c688e7d3741bc46e82d8997dc6a8c04948a25424528102ba3a"
PUBLISHED_PLAN = "4caa3811ff1eb9e19bc0e460edd760755e224100953595e5a5c4b91ab73cb6ef"


def load(artifacts: Path, label: str) -> list[dict]:
    return [json.loads(line) for line in (artifacts / f"{PREFIX}-{label}.jsonl").read_bytes().splitlines()]


def arm_rows(artifacts: Path, arm_id: str) -> tuple[list[dict], dict]:
    audit = audit_corpus(artifacts)
    if (audit["manifest_identity"], audit["plan_identity"]) != (PUBLISHED_MANIFEST, PUBLISHED_PLAN):
        raise ValueError("published Bridge identity")
    plan = json.loads((artifacts / f"{PREFIX}-plan.json").read_bytes())
    arms = {arm["id"]: arm for arm in plan["factorial"]["arms"]}
    if arm_id not in arms or arm_id == "A0":
        raise ValueError("A0 is baseline evaluation, not training projection")
    arm = arms[arm_id]
    target = {"LITERAL_SAFE_CONTROL": "control", "NEUTRAL_EDITORIAL_MECHANICS": "mechanics"}[arm["target"]]
    instruction = "-generic" if arm["instruction"] == "GENERIC_FACTUAL_REWRITE" else ""
    replay = "replay-protective" if arm["replay"] == "PROTECTIVE_SELECTION" else "replay-baseline"
    new = load(artifacts, f"train-{target}{instruction}")
    anchors = load(artifacts, replay)
    if len(new) != 48 or len(anchors) != 48:
        raise ValueError("arm row count")
    if len({row["example_id"] for row in new + anchors}) != 96:
        raise ValueError("arm case overlap")
    return new + anchors, arm


def projection(artifacts: Path = ART) -> dict:
    results = {}
    for arm_id in ("A1", "A2", "A3", "A4", "A5", "A6", "A7"):
        values, arm = arm_rows(artifacts, arm_id)
        raw = b"".join(compact(row).encode() + b"\n" for row in values)
        results[arm_id] = {"sha256": sha(raw), "bytes": len(raw), "rows": 96,
                           "target": arm["target"], "instruction": arm["instruction"],
                           "recipe": arm["recipe"], "replay": arm["replay"]}
    core = {"schema": "editor-core-editorial-bridge-arm-projections", "schema_version": 1,
            "published_commit": PUBLISHED_COMMIT, "manifest_identity": PUBLISHED_MANIFEST,
            "plan_identity": PUBLISHED_PLAN, "arms": results, "model_loaded": False,
            "optimizer_steps": 0, "training_performed": False}
    return {**core, "projection_identity": sha(canonical(core))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=ART)
    args = parser.parse_args()
    print(json.dumps(projection(args.artifacts), ensure_ascii=False, sort_keys=True))
