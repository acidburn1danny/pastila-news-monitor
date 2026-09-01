import hashlib
import json
from pathlib import Path

ART = Path(__file__).resolve().parents[1] / "docs/artifacts"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot13_g02c_is_sealed_mechanism_neutral_candidate_failure():
    receipt = json.loads((ART / "humor-mechanics-batch2-development-pilot13-candidate01-g02c-conformance-receipt-v5-3-3.json").read_text(encoding="utf-8"))
    review = json.loads((ART / "humor-mechanics-batch2-development-pilot13-candidate01-g02c-review-v5-3-3.json").read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("conformance_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT13_G02C_CONFORMANCE_RECEIPT_V5_3_3", core)
    core = dict(review); identity = core.pop("g02c_review_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT13_G02C_REVIEW_V5_3_3", core)
    assert receipt["verdict"] == "FAIL_FIRST_INVENTED_LINK_ROLE_AFFORDANCE_AND_CAUSAL_NECESSITY"
    assert receipt["failure"]["earliest_failed_link"] == "P5_TO_L1"
    assert all(node["material_presence"].startswith("PASS_") for node in receipt["independently_recovered_nodes"].values())
    assert all(edge["material_presence"] == "PASS" for edge in receipt["independently_recovered_edges"].values())
    assert all(edge["semantic_role_compatibility"] == "FAIL" and edge["causal_necessity"] == "FAIL"
               for edge in receipt["independently_recovered_edges"].values())
    assert receipt["sealed_mapping_accessed"] is False and receipt["mechanism_adjudication_performed"] is False
    assert receipt["candidate_bytes_unchanged"] is True and review["g03_eligibility"] is False
    assert review["POST_REQUALIFICATION_DETERMINISTIC_INFRASTRUCTURE_DEFECT"] == "NONE_CANDIDATE_LEVEL_FAILURE"
    assert all(value is False for value in review["authority_matrix"].values())
