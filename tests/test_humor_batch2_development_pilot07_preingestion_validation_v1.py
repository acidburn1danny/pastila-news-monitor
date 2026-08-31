import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot07_validation_is_sealed_and_non_authorizing():
    path = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot07-strict-preingestion-validation-v1.json"
    value = json.loads(path.read_text(encoding="utf-8")); core = dict(value); identity = core.pop("validation_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT07_STRICT_PREINGESTION_VALIDATION_V1", core)
    assert value["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY"
    assert value["proposition_sufficiency_evaluated"] is False
    assert value["signing_requested_or_packet_created"] is False
    assert value["ingestion_or_archive_write_performed"] is False
    assert all(flag is False for flag in value["authority_matrix"].values())
