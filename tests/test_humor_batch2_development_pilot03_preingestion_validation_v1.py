from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot03-strict-preingestion-validation-v1.json"


def test_validation_is_sealed_pass_and_stops_before_derivation_or_ingestion() -> None:
    value = json.loads(PATH.read_text(encoding="utf-8"))
    identity = value.pop("validation_identity")
    payload = json.dumps(
        {"namespace": "B2_DEVELOPMENT_PILOT03_STRICT_PREINGESTION_VALIDATION_V1", "value": value},
        ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    assert identity == hashlib.sha256(payload).hexdigest()
    assert value["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY"
    assert value["source_sha256"] == "61a5889cb03f72c6f4f72b0f1652b2db43c092f51c91f7d5e59933a99ca2fc30"
    assert value["declaration_sha256"] == "5915ee71841ed1a40ae375e0e7c6a4b611c525d0b8690464e61d66e078b14d8d"
    assert all(result.startswith("PASS") for result in value["checks"].values())
    assert value["prospective_identities_derived"] is False
    assert value["proposition_envelope_created"] is False
    assert value["family_identities_derived"] is False
    assert value["signing_requested_or_packet_created"] is False
    assert value["ingestion_or_archive_write_performed"] is False
    assert value["g01_admission_performed"] is False
    assert not any(value["authority_matrix"].values())
