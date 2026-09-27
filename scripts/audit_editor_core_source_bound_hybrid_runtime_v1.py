"""Adversarial audit for the fixture-only hybrid runtime boundary."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from editor_core_source_bound_hybrid_runtime_v1 import ARMS, SEEDS, fixture_arm
from fixture_editor_core_source_bound_hybrid_feasibility_v1 import (
    execute_with_fallback,
    extractive_proposal,
    load_jsonl,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"


def main() -> None:
    boundary_path = ART / "editor-core-source-bound-hybrid-runtime-boundary-v1.json"
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    core = {key: value for key, value in boundary.items() if key != "runtime_boundary_identity"}
    identity = hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if identity != boundary["runtime_boundary_identity"]:
        raise ValueError("boundary identity")
    if boundary["files"] != {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in boundary["files"]}:
        raise ValueError("runtime source closure")
    if boundary["slots"] != len(ARMS) * len(SEEDS) or boundary["execution_authority"]:
        raise ValueError("slot/authority closure")
    if not boundary["oracle_fixture_upper_bound"] or boundary["autonomous_ledger_construction_claimed"]:
        raise ValueError("oracle limitation")
    ledgers = load_jsonl("editor-core-source-bound-hybrid-feasibility-v1-ledgers.jsonl")
    checks = 0
    for ledger in ledgers:
        outputs = {arm: fixture_arm(arm, ledger) for arm in ARMS}
        if any(output["model_loaded"] for output in outputs.values()):
            raise ValueError("model load in fixture")
        checks += 3
        mutation = extractive_proposal(ledger)
        mutation["sentences"][0]["text"] += " Entitatea Fantomă raportează 999999."
        result = execute_with_fallback(ledger, mutation)
        if result["route"] != "EXTRACTIVE_FALLBACK" or not result["fallback"]["accepted"]:
            raise ValueError("verifier/fallback escape")
        checks += 1
    route = (ROOT / "scripts/run_editor_core_source_bound_hybrid_runtime_v1.sh").read_text(encoding="utf-8")
    if "--zero-step-only" not in route or "exit 64" not in route:
        raise ValueError("route execution guard")
    print(json.dumps({
        "status": "PASS_ADVERSARIAL",
        "checks": checks,
        "runtime_boundary_identity": boundary["runtime_boundary_identity"],
        "model_loaded": False,
        "inference_performed": False,
        "training_performed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
