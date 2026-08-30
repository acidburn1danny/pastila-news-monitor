from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps(
        {"namespace": namespace, "value": value},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_g03b_review_confirms_causality_without_new_candidate() -> None:
    value = load("humor-mechanics-batch2-development-pilot02-candidate01-g03b-review-v1.json")
    identity = value.pop("g03b_review_identity")

    assert identity == seal("B2_DEVELOPMENT_PILOT02_CANDIDATE01_G03B_REVIEW_V1", value)
    assert value["candidate_raw_sha256"] == "5c50ca8e4ae5ea32301c02ec8ea4104482bbc9c8e3c7e8314516d09aeb591fd3"
    assert value["candidate_bytes_modified"] is False
    assert value["counterfactuals_materialized_as_candidates"] is False
    assert value["causal_trace"]["verdict"] == "COMPLETE_RECOVERABLE_CAUSAL_CHAIN"
    assert {item["causal_result"] for item in value["minimal_interventions"]} >= {
        "DOMINANCE_REMOVED",
        "MECHANISM_REMOVED",
        "LABEL_CHANGE",
        "INVARIANT_UNDER_SURFACE_PARAPHRASE",
    }
    assert value["g03b_verdict"] == "CAUSAL_MECHANISM_CONFIRMED"
    assert not any(value["performed"].values())
    assert not any(value["authority_matrix"].values())


def test_g03b_receipt_is_sealed_and_only_allows_a_later_decision() -> None:
    value = load("humor-mechanics-batch2-development-pilot02-candidate01-g03b-receipt-v1.json")
    identity = value.pop("g03b_receipt_identity")

    assert identity == seal("B2_DEVELOPMENT_PILOT02_CANDIDATE01_G03B_RECEIPT_V1", value)
    assert value["g03b_verdict"] == "CAUSAL_MECHANISM_CONFIRMED"
    assert value["candidate_bytes_modified"] is False
    assert value["counterfactual_candidate_created"] is False
    assert value["next_gate_eligible"] == "G03C_SEPARATELY_AUTHORIZED_ONLY"
    assert not any(value["authority_matrix"].values())
