from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def seal(namespace: str, value: dict) -> str:
    return hashlib.sha256(json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def test_pilot05_validation_is_sealed_strict_and_nonoperational() -> None:
    value = json.loads((ART / "humor-mechanics-batch2-development-pilot05-strict-preingestion-validation-v1.json").read_text(encoding="utf-8"))
    identity = value.pop("validation_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT05_STRICT_PREINGESTION_VALIDATION_V1", value)
    assert value["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY"
    assert value["source_sha256"] == "e3404a694bf1203f8a11ceeed0e682511882237e4777bd0e092876994c4326cc"
    assert value["submitted_declaration_sha256"] == "acff7c3ffd4124c6c0d8921e3887811259f4192ef35e7fc40d51e8bcad7fe71c"
    assert value["canonical_declaration_sha256"] == "69e207463fcb8d31e0ccaf99db46192bd577997dfb4b1d3658a5f955fb148e25"
    assert value["checks"]["pilot01_02_03_04_exact_source_and_line_independence"] == "PASS"
    assert value["checks"]["duplicated_04_suffix_repair"] == "PASS_CANONICAL_SUCCESSOR_VALUES_PRESERVED"
    assert value["checks"]["downstream_grants_false"] == "PASS"
    assert value["prospective_identities_derived"] is False
    assert value["signing_requested_or_packet_created"] is False
    assert value["ingestion_or_archive_write_performed"] is False
    assert value["g01_admission_performed"] is False
    assert value["g04b_pool_certification_performed"] is False
    assert not any(value["authority_matrix"].values())
