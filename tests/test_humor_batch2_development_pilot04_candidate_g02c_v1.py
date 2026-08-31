"""Verify Pilot 04 Governance V2 G02C artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot04_g02c_is_mechanism_neutral_v2_and_non_authorizing() -> None:
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot04-candidate01-g02c-conformance-receipt-v1.json").read_text(encoding="utf-8"))
    review = json.loads((ART / "humor-mechanics-batch2-development-pilot04-candidate01-g02c-review-v1.json").read_text(encoding="utf-8"))
    receipt_core = dict(receipt); receipt_id = receipt_core.pop("conformance_receipt_identity")
    assert seal("B2_DEVELOPMENT_PILOT04_G02C_CONFORMANCE_RECEIPT_V2", receipt_core) == receipt_id
    assert receipt["verdict"] == "PASS"
    assert all(receipt["required_predicates"].values())
    assert all(value is False for key, value in receipt["naturalness_precheck"].items() if key != "does_not_replace_blind_g04a")
    review_core = dict(review); review_id = review_core.pop("g02c_review_identity")
    assert seal("B2_DEVELOPMENT_PILOT04_G02C_REVIEW_V1", review_core) == review_id
    assert review["g02c_verdict"] == "PASS"
    assert review["sealed_mapping_accessed"] is False and review["g03_performed"] is False
    assert all(value is False for value in review["authority_matrix"].values())
