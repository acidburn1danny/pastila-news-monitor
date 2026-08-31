from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def test_g03b_confirms_causality_without_materializing_counterfactuals() -> None:
    review = json.loads((ART / "humor-mechanics-batch2-development-pilot03-candidate01-g03b-review-v1.json").read_text(encoding="utf-8"))
    identity = review.pop("g03b_review_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT03_CANDIDATE01_G03B_REVIEW_V1", review)
    assert review["candidate_bytes_modified"] is False
    assert review["counterfactuals_materialized_as_candidates"] is False
    assert review["causal_trace"]["verdict"] == "COMPLETE_RECOVERABLE_CAUSAL_CHAIN"
    assert {x["causal_result"] for x in review["minimal_interventions"]} >= {
        "DOMINANCE_REMOVED", "MECHANISM_REMOVED", "LABEL_CHANGE", "INVARIANT_UNDER_SURFACE_PARAPHRASE"}
    assert review["g03b_verdict"] == "CAUSAL_MECHANISM_CONFIRMED"
    assert not any(review["performed"].values()) and not any(review["authority_matrix"].values())


def test_g03b_receipt_is_sealed_and_non_authorizing() -> None:
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot03-candidate01-g03b-receipt-v1.json").read_text(encoding="utf-8"))
    identity = receipt.pop("g03b_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT03_CANDIDATE01_G03B_RECEIPT_V1", receipt)
    assert receipt["g03b_verdict"] == "CAUSAL_MECHANISM_CONFIRMED"
    assert receipt["candidate_bytes_modified"] is False and receipt["counterfactual_candidate_created"] is False
    assert receipt["next_gate_eligible"] == "G03C_SEPARATELY_AUTHORIZED_ONLY"
    assert not any(receipt["authority_matrix"].values())
