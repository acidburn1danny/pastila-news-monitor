from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace: str, value: dict) -> str:
    return hashlib.sha256(json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def test_pilot04_validation_is_sealed_strict_and_nonoperational() -> None:
    value = json.loads((ART / "humor-mechanics-batch2-development-pilot04-strict-preingestion-validation-v1.json").read_text(encoding="utf-8"))
    identity = value.pop("validation_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT04_STRICT_PREINGESTION_VALIDATION_V1", value)
    assert value["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY"
    assert value["source_sha256"] == "db4d440d42596e2db5ca402afa23bc8f65dcf7a7ba23a06d3ebef9e2eb1aa480"
    assert value["declaration_sha256"] == "d7da118d32f2ca05fc5d1816a616e8bccdc58017f934539efc054733da9d5958"
    assert value["checks"]["pilot01_02_03_exact_source_and_line_independence"] == "PASS"
    assert value["checks"]["downstream_grants_false"] == "PASS"
    assert value["prospective_identities_derived"] is False
    assert value["signing_requested_or_packet_created"] is False
    assert value["ingestion_or_archive_write_performed"] is False
    assert value["g01_admission_performed"] is False
    assert value["g04b_pool_certification_performed"] is False
    assert not any(value["authority_matrix"].values())
