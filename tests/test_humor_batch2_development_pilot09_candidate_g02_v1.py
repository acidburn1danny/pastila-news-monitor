import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot09_g02_receipt_is_pass_sealed_and_non_authorizing():
    path = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot09-candidate01-g02-v1.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    core = dict(receipt)
    identity = core.pop("g02_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT09_CANDIDATE_G02_V1", core)
    assert receipt["g02_verdict"] == "PASS"
    assert receipt["factual_assertion_trace"][0]["authority_proposition_ids"] == ["P5"]
    assert receipt["candidate_raw_sha256"] == "3249775af5b93a68f00ab1e8217652a1411db03d61a40dfbe1e1fa3f7cd7e307"
    assert receipt["candidate_git_blob_oid_sha1"] == "fd1c7c024523faf63efe610849620364638a48b3"
    assert receipt["fragment_collision_binding"]["collision_count"] == 0
    assert receipt["sealed_mapping_accessed"] is False
    assert receipt["mechanism_adjudication_performed"] is False
    assert receipt["romanian_naturalness_review_performed"] is False
    assert all(value is False for value in receipt["authority_matrix"].values())
