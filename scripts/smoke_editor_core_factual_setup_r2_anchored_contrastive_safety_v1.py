from __future__ import annotations

import json
from pathlib import Path

from editor_core_factual_setup_r2_anchored_contrastive_safety_fixture_v1 import ARMS, FAILURE_CLASSES, LAYER_GROUPS, SEEDS, decide, gradient_probe, run_fixture


ROOT = Path(__file__).resolve().parents[1]
PAIRS = ROOT / "docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-v1-minimal-pairs.jsonl"


def main() -> None:
    pairs = [json.loads(line) for line in PAIRS.read_text(encoding="utf-8").splitlines()]
    runs = [run_fixture(arm, seed, f"{arm}__seed_{seed}", pairs) for arm in ARMS for seed in SEEDS]
    corrective = {}; replay = {}
    for f_index, failure in enumerate(FAILURE_CLASSES, 1):
        for l_index, layer in enumerate(LAYER_GROUPS, 1):
            corrective[(failure, layer)] = [float(f_index), float(l_index), 1.0]
            replay[(failure, layer)] = [float(f_index), float(l_index), 0.5]
    probe = gradient_probe(corrective, replay)
    decision = decide({"material_regressions": 0, "novel_actor_or_repetition": False, "replicated_gain_seeds": 3, "pairwise_margin_classes": 6, "retention_pass_seeds": 3, "strong_unresolved_conflicts": 0})
    if any(run["publication_order"][-1] != "terminal.json" or run["terminal"]["status"] != "PASS_FIXTURE_ONLY" for run in runs):
        raise ValueError("fixture terminal closure")
    print(json.dumps({"status": "PASS_FIXTURE_ONLY", "blockers": 0, "slots": len(runs), "gradient_cells": len(probe["rows"]), "decision_fixture": decision, "model_loaded": False, "optimizer_created": False, "training_performed": False, "inference_performed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
