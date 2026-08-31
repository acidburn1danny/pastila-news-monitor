import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot06_disposition_is_nonpositive_sealed_and_non_authorizing():
    path = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot06-candidate01-disposition-v1.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    core = dict(value); identity = core.pop("disposition_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT06_AMBIGUOUS_DISPOSITION_V1", core)
    assert value["disposition"] == "DEVELOPMENT_NONPOSITIVE_AMBIGUOUS_CONFUSABLE_EVIDENCE"
    assert value["target_dominant_recovery_established"] is False
    assert value["positive_m13_coverage_eligible"] is False
    assert value["positive_pool_eligible"] is False
    assert value["candidate_bytes_modified"] is False
    assert value["visibility"] == "NON_MODEL_VISIBLE"
    assert all(flag is False for flag in value["authority_matrix"].values())
