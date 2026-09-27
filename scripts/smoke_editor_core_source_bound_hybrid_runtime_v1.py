"""Fixture smoke for B0/B1/B2 separation and verifier/fallback behavior."""
from __future__ import annotations

import json

from editor_core_source_bound_hybrid_runtime_v1 import ARMS, fixture_arm
from fixture_editor_core_source_bound_hybrid_feasibility_v1 import (
    execute_with_fallback,
    extractive_proposal,
    load_jsonl,
)


def main() -> None:
    ledgers = load_jsonl("editor-core-source-bound-hybrid-feasibility-v1-ledgers.jsonl")
    outputs = {arm: fixture_arm(arm, ledgers[0]) for arm in ARMS}
    if outputs["B0_R2_ONE_PASS"]["mode"] != "REQUEST_ONLY_NO_INFERENCE":
        raise ValueError("B0 separation")
    if outputs["B1_EXTRACTIVE_BASELINE"]["mode"] != "DETERMINISTIC_EXTRACTIVE":
        raise ValueError("B1 separation")
    if outputs["B2_HYBRID"]["mode"] != "FIXTURE_REALIZER_THEN_VERIFY":
        raise ValueError("B2 separation")
    mutation = extractive_proposal(ledgers[0])
    mutation["sentences"][0]["text"] += " Birocrația confirmă 999999 de cazuri."
    fallback = execute_with_fallback(ledgers[0], mutation)
    if fallback["route"] != "EXTRACTIVE_FALLBACK" or not fallback["fallback"]["accepted"]:
        raise ValueError("fallback closure")
    print(json.dumps({
        "status": "PASS_FIXTURE_RUNTIME_SMOKE",
        "arms": list(ARMS),
        "fallback": "PASS",
        "model_loaded": False,
        "inference_performed": False,
        "optimizer_created": False,
        "training_performed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
