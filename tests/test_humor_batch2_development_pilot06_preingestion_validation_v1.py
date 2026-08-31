"""Verify Pilot 06 strict pre-ingestion validation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "docs/artifacts/humor-mechanics-batch2-development-pilot06-strict-preingestion-validation-v1.json"


def seal(namespace: str, value: dict) -> str:
    raw = json.dumps({"namespace": namespace, "value": value}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def test_pilot06_validation_is_strict_sealed_and_nonoperational() -> None:
    value = json.loads(PATH.read_text(encoding="utf-8"))
    core = dict(value); identity = core.pop("validation_identity")
    assert seal("B2_DEVELOPMENT_PILOT06_STRICT_PREINGESTION_VALIDATION_V1", core) == identity
    assert value["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY"
    assert value["source_sha256"] == "eb97e6bdffc809d0902f90bb26b95c3c4a6047476b27eec7ac46b613dba030ad"
    assert value["declaration_sha256"] == "9612cd4e0b58b752636b83dfcab28f2e0c4eb208981f52b6b34f9295526050c4"
    assert value["checks"]["pilot01_through_05_exact_source_and_line_independence"] == "PASS"
    assert value["checks"]["downstream_grants_false"] == "PASS"
    assert value["proposition_sufficiency_evaluated"] is False
    assert value["prospective_identities_derived"] is False
    assert value["signing_requested_or_packet_created"] is False
    assert value["ingestion_or_archive_write_performed"] is False
    assert value["g01_admission_performed"] is False
    assert value["assignment_or_constructor_release_performed"] is False
    assert not any(value["authority_matrix"].values())
