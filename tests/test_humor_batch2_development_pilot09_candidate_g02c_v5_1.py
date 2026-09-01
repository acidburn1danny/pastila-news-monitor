import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot09_g02c_failure_is_sealed_mechanism_neutral_and_non_authorizing():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot09-candidate01-g02c-conformance-receipt-v5-1.json").read_text(encoding="utf-8"))
    review = json.loads((ART / "humor-mechanics-batch2-development-pilot09-candidate01-g02c-review-v5-1.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("conformance_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT09_G02C_CONFORMANCE_RECEIPT_V5_1", core)
    core = dict(review); identity = core.pop("g02c_review_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT09_G02C_REVIEW_V5_1", core)
    assert receipt["verdict"] == "FAIL_INCOMPLETE_CAUSAL_SPINE"
    assert receipt["failure"]["earliest_failed_link"] == "SELECTED_FACT_TO_FIRST_INVENTED_CONSEQUENCE"
    assert sum(not value for value in receipt["required_predicates"].values()) == 5
    assert receipt["sealed_mapping_accessed"] is False
    assert review["g03_eligibility"] is False
    assert review["candidate_modified"] is False
    assert all(value is False for value in review["authority_matrix"].values())
