"""Verify the mechanism-neutral Pilot 08 Governance V4 G02C rejection."""

import hashlib
import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot08_g02c_is_sealed_mechanism_neutral_rejection():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot08-candidate01-g02c-conformance-receipt-v4.json").read_text(encoding="utf-8"))
    review = json.loads((ART / "humor-mechanics-batch2-development-pilot08-candidate01-g02c-review-v4.json").read_text(encoding="utf-8"))
    receipt_core = dict(receipt)
    receipt_id = receipt_core.pop("conformance_receipt_identity")
    assert seal("B2_DEVELOPMENT_PILOT08_G02C_CONFORMANCE_RECEIPT_V4", receipt_core) == receipt_id
    assert receipt["verdict"] == "FAIL_UNBOUND_OPERAND_AND_INCOMPLETE_MULTI_LINK_CAUSAL_SPINE"
    assert receipt["required_predicates"]["ALL_REFERENCES_AND_OPERANDS_BOUND"] is False
    assert receipt["required_predicates"]["COMPLETE_MULTI_LINK_CAUSAL_SPINE"] is False
    assert receipt["failure"]["earliest_failed_link"] == "FIRST_INVENTED_RELATION_TO_CONTROL_RETURN"
    assert receipt["failure"]["candidate_repair_performed"] is False
    review_core = dict(review)
    review_id = review_core.pop("g02c_review_identity")
    assert seal("B2_DEVELOPMENT_PILOT08_G02C_REVIEW_V4", review_core) == review_id
    assert review["g02c_verdict"].startswith("FAIL_")
    assert review["sealed_mapping_accessed"] is False and review["g03_performed"] is False
    assert review["candidate_modified"] is False
    assert review["romanian_naturalness_review_performed"] is False
    assert all(value is False for value in review["authority_matrix"].values())
