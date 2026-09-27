"""Fresh fail-closed audit for the closed Hybrid semantic result."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluate_editor_core_source_bound_hybrid_closed_v1 import canonical, sha


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    result = json.loads(args.result.read_text(encoding="utf-8"))
    identity = result.pop("result_identity")
    checks = []
    checks.append(identity == sha(canonical(result)))
    checks.append(result["rows"] == 432)
    checks.append(len(result["slots"]) == 9)
    checks.append(result["decision"] == "REVISE")
    checks.append(not result["stop_reasons"])
    checks.append(result["development_parent"] == "R2_STEP_9" and not result["parent_changed"])
    checks.append(not result["historical_holdout_accessed"])
    checks.append(not result["inference_performed"] and not result["training_performed"] and result["optimizer_steps"] == 0)
    checks.append("PARENT_SELECTION" in result["claims_forbidden"])
    for arm in ("B0_R2_ONE_PASS", "B1_EXTRACTIVE_BASELINE", "B2_HYBRID"):
        arm_slots = [result["slots"][f"{arm}__seed_{seed}"] for seed in (161803, 271828, 314159)]
        checks.append(all(slot["aggregate"]["rows"] == 48 for slot in arm_slots))
        checks.append(len({result["source_receipts"][f"{arm}__seed_{seed}"]["observations_sha256"] for seed in (161803, 271828, 314159)}) == 1)
    checks.append(result["arm_summary_per_seed_mean"]["B2_HYBRID"]["material_drift_cases"] == 0)
    checks.append(result["arm_summary_per_seed_mean"]["B2_HYBRID"]["mean_fallback_rate"] > 0.25)
    if not all(checks):
        raise ValueError(f"adversarial audit failed: {[i for i, passed in enumerate(checks, 1) if not passed]}")
    print(json.dumps({"status": "PASS_ADVERSARIAL", "checks": len(checks), "result_identity": identity}, sort_keys=True))


if __name__ == "__main__":
    main()
