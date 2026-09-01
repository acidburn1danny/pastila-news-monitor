import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot07_g02_receipt_is_pass_sealed_and_non_authorizing():
    path = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-g02-v1.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("g02_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT07_CANDIDATE_G02_V1", core)
    assert receipt["g02_verdict"] == "PASS"
    assert receipt["factual_assertion_trace"][0]["authority_proposition_ids"] == ["P5"]
    assert receipt["candidate_raw_sha256"] == "769228fc99006e0f665360f28805f31d4480419095de1f1fba5794319cc1bfa8"
    assert receipt["candidate_git_blob_oid_sha1"] == "345829c569ae87d350a30158e026c52371e3c560"
    assert receipt["sealed_mapping_accessed"] is False
    assert receipt["mechanism_adjudication_performed"] is False
    assert all(value is False for value in receipt["authority_matrix"].values())
