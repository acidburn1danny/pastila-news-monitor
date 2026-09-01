"""Verify strict Pilot 09 pre-ingestion validation is sealed and non-authorizing."""

import hashlib
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "docs/artifacts/humor-mechanics-batch2-development-pilot09-strict-preingestion-validation-v1.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot09_strict_preingestion_validation_is_sealed_and_non_authorizing():
    artifact = json.loads(PATH.read_text(encoding="utf-8"))
    core = dict(artifact)
    identity = core.pop("validation_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT09_STRICT_PREINGESTION_VALIDATION_V1", core)
    assert artifact["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY"
    assert artifact["source_sha256"] == "608f26b4588c347707ae5eccb08194d498fb3b3e9e7a6402be63ad2bc7c77c77"
    assert artifact["declaration_sha256"] == "8c68d5bf2a711fc518879fcddfba9ea44d7c232fb962fdecc816bf97d249b41b"
    assert artifact["deterministic_blockers"] == []
    assert artifact["repair_performed"] is False
    assert artifact["proposition_sufficiency_evaluated"] is False
    assert artifact["prospective_identities_derived"] is False
    assert artifact["constructor_source_compatibility_or_release_performed"] is False
    assert all(value is False for value in artifact["authority_matrix"].values())
