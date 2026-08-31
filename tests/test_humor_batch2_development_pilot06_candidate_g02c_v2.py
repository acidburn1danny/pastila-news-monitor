import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot06_g02c_receipts_pass_and_are_sealed():
    base = ROOT / "docs/artifacts"
    receipt = json.loads((base / "humor-mechanics-batch2-development-pilot06-candidate01-g02c-conformance-receipt-v2.json").read_text(encoding="utf-8"))
    review = json.loads((base / "humor-mechanics-batch2-development-pilot06-candidate01-g02c-review-v2.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("conformance_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT06_G02C_CONFORMANCE_RECEIPT_V2", core)
    review_core = dict(review); review_identity = review_core.pop("g02c_review_identity")
    assert review_identity == seal("B2_DEVELOPMENT_PILOT06_G02C_REVIEW_V2", review_core)
    assert receipt["verdict"] == review["g02c_verdict"] == "PASS"
    assert receipt["selected_proposition_id"] == "P3"
    assert all(receipt["required_predicates"].values())
    assert receipt["dependency_trace"]["arbitrary_substitution"] is False
    assert review["sealed_mapping_accessed"] is False and review["g03_performed"] is False
    assert all(value is False for value in review["authority_matrix"].values())
