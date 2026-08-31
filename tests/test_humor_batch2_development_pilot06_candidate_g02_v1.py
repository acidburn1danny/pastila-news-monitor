import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot06_g02_receipt_is_pass_sealed_and_non_authorizing():
    path = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot06-candidate01-g02-v1.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    core = dict(receipt); identity = core.pop("g02_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT06_CANDIDATE_G02_V1", core)
    assert receipt["g02_verdict"] == "PASS"
    assert receipt["factual_assertion_trace"][0]["authority_proposition_ids"] == ["P3"]
    assert receipt["candidate_raw_sha256"] == "e00b1b83507ece1808445a3f6cfd07286ee20eecc6f4208d9aa4940ab2fbc1a9"
    assert receipt["candidate_git_blob_oid_sha1"] == "4d0aa51522e56038826badd4ae180cdcfe4499e1"
    assert receipt["sealed_mapping_accessed"] is False
    assert receipt["mechanism_adjudication_performed"] is False
    assert all(value is False for value in receipt["authority_matrix"].values())
