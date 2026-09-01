import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot10_g02c_fails_terminal_semantic_edge_without_downstream_authority():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot10-candidate01-g02c-conformance-receipt-v5-2.json").read_text(encoding="utf-8"))
    review = json.loads((ART / "humor-mechanics-batch2-development-pilot10-candidate01-g02c-review-v5-2.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("conformance_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_G02C_CONFORMANCE_RECEIPT_V5_2", core)
    core = dict(review); identity = core.pop("g02c_review_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_G02C_REVIEW_V5_2", core)
    assert receipt["verdict"] == "FAIL_TERMINAL_EDGE_NON_ARBITRARY_CAUSAL_CONTINUITY"
    assert receipt["failure"]["earliest_failed_link"] == "L2_TO_TERMINAL_RESULT"
    assert receipt["independently_recovered_nodes"]["L1"]["local_recoverability"] == "PASS"
    assert receipt["independently_recovered_nodes"]["L2"]["local_recoverability"] == "PASS"
    assert receipt["independently_recovered_nodes"]["RESULT"]["local_recoverability"].startswith("FAIL_")
    assert receipt["independently_recovered_edges"]["L2_TO_RESULT"]["non_arbitrary"] is False
    assert receipt["pre_emission_conformance_provenance"].endswith("NOT_USED_AS_SUFFICIENT_SEMANTIC_EVIDENCE")
    assert receipt["sealed_mapping_accessed"] is False
    assert review["g03_eligibility"] is False
    assert review["candidate_modified"] is False
    assert all(value is False for value in review["authority_matrix"].values())
