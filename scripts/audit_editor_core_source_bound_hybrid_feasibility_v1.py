"""Adversarial audit for the fixture-only source-bound hybrid diagnostic."""
from __future__ import annotations

import json

from fixture_editor_core_source_bound_hybrid_feasibility_v1 import (
    extractive_proposal,
    load_jsonl,
    run,
    validate_ledger,
    verify_proposal,
)


def main() -> None:
    result = run()
    ledgers = load_jsonl("editor-core-source-bound-hybrid-feasibility-v1-ledgers.jsonl")
    checks = 0
    for ledger in ledgers:
        validate_ledger(ledger)
        proposal = extractive_proposal(ledger)
        baseline = verify_proposal(ledger, proposal)
        assert baseline["accepted"]
        checks += 1

        bad_case = json.loads(json.dumps(proposal))
        bad_case["case_id"] += "-substitution"
        assert not verify_proposal(ledger, bad_case)["accepted"]
        checks += 1

        empty_binding = json.loads(json.dumps(proposal))
        empty_binding["sentences"][0]["atom_ids"] = []
        assert not verify_proposal(ledger, empty_binding)["accepted"]
        checks += 1

        repeated = json.loads(json.dumps(proposal))
        repeated["sentences"][0]["text"] += " " + repeated["sentences"][0]["text"]
        assert not verify_proposal(ledger, repeated)["accepted"]
        checks += 1

    print(json.dumps({
        "status": "PASS_ADVERSARIAL",
        "checks": checks,
        "fixture_status": result["status"],
        "model_loaded": False,
        "inference_performed": False,
        "training_performed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
