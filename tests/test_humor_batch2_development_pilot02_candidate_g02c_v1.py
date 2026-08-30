"""Verify Pilot 02's mechanism-neutral G02C conformance freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot02_g02c_is_schema_valid_mechanism_neutral_and_non_authorizing() -> None:
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot02-candidate01-g02c-conformance-receipt-v1.json").read_text(encoding="utf-8"))
    review = json.loads((ART / "humor-mechanics-batch2-development-pilot02-candidate01-g02c-review-v1.json").read_text(encoding="utf-8"))
    schema = json.loads((ART / "humor-mechanics-batch2-obligation-conformance-schema-v1.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(receipt)
    receipt_identity = seal("B2_DEVELOPMENT_PILOT02_G02C_CONFORMANCE_RECEIPT_V1", receipt)
    assert receipt_identity == review["conformance_receipt_identity"]
    review_core = dict(review)
    review_identity = review_core.pop("g02c_review_identity")
    assert seal("B2_DEVELOPMENT_PILOT02_G02C_REVIEW_V1", review_core) == review_identity
    assert receipt["verdict"] == review["g02c_verdict"] == "PASS"
    assert [step["ordinal"] for step in receipt["steps"]] == [1, 2]
    assert receipt["dependency"] == {
        "step2_requires_step1": True,
        "removal_test": "STEP2_STRUCTURALLY_UNAVAILABLE_WITHOUT_STEP1",
        "unrelated_replacement_possible": False,
    }
    assert not any(receipt["entity_status"].values())
    assert not any(receipt["imported_relation"].values())
    assert not any(receipt["neighbor_substitution"].values())
    assert review["sealed_mapping_accessed"] is False and review["g03_performed"] is False
    assert review["candidate_modified"] is False
    assert all(value is False for value in review["authority_matrix"].values())


def test_g02c_reviewer_source_has_no_mapping_access_path() -> None:
    source = (ROOT / "scripts/review_humor_batch2_development_pilot02_candidate_g02c_v1.py").read_text(encoding="utf-8")
    assert "sealed-assignment-mapping" not in source
    assert "target_mapping" not in source
