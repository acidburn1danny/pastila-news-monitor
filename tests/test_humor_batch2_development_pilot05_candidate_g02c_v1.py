"""Verify Pilot 05 mechanism-neutral G02C rejection."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot05_g02c_is_sealed_mechanism_neutral_rejection() -> None:
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot05-candidate01-g02c-conformance-receipt-v1.json").read_text(encoding="utf-8"))
    review = json.loads((ART / "humor-mechanics-batch2-development-pilot05-candidate01-g02c-review-v1.json").read_text(encoding="utf-8"))
    receipt_core = dict(receipt)
    receipt_id = receipt_core.pop("conformance_receipt_identity")
    assert seal("B2_DEVELOPMENT_PILOT05_G02C_CONFORMANCE_RECEIPT_V1", receipt_core) == receipt_id
    assert receipt["verdict"] == "FAIL_INCOMPLETE_RECOVERABLE_REVERSE_DEPENDENCY"
    assert receipt["required_predicates"]["DIFFERENCE_STEP_RECOVERABLE_FROM_SELECTED_P3_RELATION"] is False
    assert receipt["failure"]["candidate_repair_performed"] is False
    review_core = dict(review)
    review_id = review_core.pop("g02c_review_identity")
    assert seal("B2_DEVELOPMENT_PILOT05_G02C_REVIEW_V1", review_core) == review_id
    assert review["g02c_verdict"].startswith("FAIL_")
    assert review["sealed_mapping_accessed"] is False and review["g03_performed"] is False
    assert review["candidate_modified"] is False
    assert all(value is False for value in review["authority_matrix"].values())
