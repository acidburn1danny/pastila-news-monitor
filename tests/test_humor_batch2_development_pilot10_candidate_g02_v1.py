import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot10_g02_receipt_is_pass_sealed_and_non_authorizing():
    path = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot10-candidate01-g02-v1.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    core = dict(receipt)
    identity = core.pop("g02_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_CANDIDATE_G02_V1", core)
    assert receipt["g02_verdict"] == "PASS"
    assert receipt["factual_assertion_trace"][0]["authority_proposition_ids"] == ["P3"]
    assert receipt["factual_assertion_trace"][-1]["classification"] == "CREATIVE_NONFACTUAL"
    assert receipt["candidate_raw_sha256"] == "013c70e3c15833e789592915f5f31b62eeaed5c1148ff6b6f78607cb0c907464"
    assert receipt["candidate_git_blob_oid_sha1"] == "8dfbc43c94190e5b0fca48d6bcd28adf55c21391"
    assert receipt["fragment_collision_binding"]["collision_count"] == 0
    assert receipt["sealed_mapping_accessed"] is False
    assert receipt["mechanism_adjudication_performed"] is False
    assert receipt["g02c_obligation_conformance_performed"] is False
    assert receipt["romanian_naturalness_review_performed"] is False
    assert receipt["eligibility"] == "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02C_OBLIGATION_CONFORMANCE"
    assert all(value is False for value in receipt["authority_matrix"].values())
