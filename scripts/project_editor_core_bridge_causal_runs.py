"""Deterministic, non-consuming projections for six matched A1/A2 runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from audit_editor_core_bridge_development_causal_pilot import audit as audit_pilot
from build_editor_core_editorial_mechanics_bridge import ART, canonical, compact, sha
from project_editor_core_editorial_bridge_arms import arm_rows

ARMS = ("A1", "A2")
SEEDS = (271828, 314159, 161803)


def project(arm: str, seed: int, artifacts: Path = ART) -> tuple[bytes, dict]:
    if arm not in ARMS or seed not in SEEDS or type(seed) is not int:
        raise ValueError("arm/seed not authorized")
    pilot = audit_pilot(artifacts)
    rows, arm_plan = arm_rows(artifacts, arm)
    corpus = b"".join(compact(row).encode("utf-8") + b"\n" for row in rows)
    expected = {"A1": "f3461bfcc83d199c4517db08fafaa05dfab31e4a6d3ec98519c33ca9ff34df48",
                "A2": "10b7fda096e2155f1bbc199268ba60fb37432e6317806cfe51d305d45cb3afc5"}[arm]
    if sha(corpus) != expected or len(rows) != 96 or arm_plan["recipe"] != "R2_LIKE":
        raise ValueError("published arm projection or recipe drift")
    core = {"schema": "editor-core-bridge-causal-pilot-run-spec", "schema_version": 1,
            "arm": arm, "seed": seed, "output_slug": f"{arm.lower()}-seed-{seed}",
            "published_bridge_commit": "94880823ac060539f21b1df4b8374b04a484ad78",
            "successor_protocol_sha256": pilot["successor_protocol_sha256"],
            "parent_adapter_identity": pilot["parent_adapter_identity"],
            "parent_checkpoint_identity": "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be",
            "training_corpus_sha256": expected, "training_rows": 96, "new_rows": 48, "replay_rows": 48,
            "optimizer": "PAGED_ADAMW_8BIT_NEW_STATE", "learning_rate": "0.000003",
            "scheduler": "CONSTANT_WITHOUT_WARMUP", "epochs": 1, "micro_batch_size": 1,
            "gradient_accumulation_steps": 8, "expected_optimizer_steps": 12,
            "max_sequence_tokens": 3072, "precision": "BF16", "packing": False,
            "development_only": True, "holdout_training_or_inference_use": False,
            "r3_r6_parent_use": False, "training_authorized": False}
    return corpus, {**core, "run_spec_identity": sha(canonical(core))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--seed", type=int, choices=SEEDS, required=True)
    parser.add_argument("--corpus-output", type=Path, required=True)
    parser.add_argument("--spec-output", type=Path, required=True)
    args = parser.parse_args()
    if (args.corpus_output.exists() or args.spec_output.exists()
            or args.corpus_output.parent != args.spec_output.parent):
        raise ValueError("projection output collision or split")
    corpus, spec = project(args.arm, args.seed)
    args.corpus_output.write_bytes(corpus)
    args.spec_output.write_bytes(json.dumps(spec, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")


if __name__ == "__main__":
    main()
