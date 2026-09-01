import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot08_g02_receipt_is_pass_sealed_and_non_authorizing():
    path = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot08-candidate01-g02-v1.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    core = dict(receipt)
    identity = core.pop("g02_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT08_CANDIDATE_G02_V1", core)
    assert receipt["g02_verdict"] == "PASS"
    assert receipt["factual_assertion_trace"][0]["authority_proposition_ids"] == ["P5"]
    assert receipt["candidate_raw_sha256"] == "bc71da32026e9173440a494279fd4dca752cfc8c5547abcaa1ad922bdda0368a"
    assert receipt["candidate_git_blob_oid_sha1"] == "679ad8c85f55f002523657baf531587694f5f607"
    assert receipt["fragment_collision_binding"]["collision_count"] == 0
    assert receipt["sealed_mapping_accessed"] is False
    assert receipt["mechanism_adjudication_performed"] is False
    assert receipt["romanian_naturalness_review_performed"] is False
    assert all(value is False for value in receipt["authority_matrix"].values())
