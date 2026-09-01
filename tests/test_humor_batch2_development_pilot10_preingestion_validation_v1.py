"""Verify strict Pilot 10 pre-ingestion validation is sealed and non-authorizing."""

import hashlib
import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "docs/artifacts/humor-mechanics-batch2-development-pilot10-strict-preingestion-validation-v1.json"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace, value):
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot10_strict_preingestion_validation_is_sealed_and_non_authorizing():
    artifact = json.loads(PATH.read_text(encoding="utf-8"))
    core = dict(artifact)
    identity = core.pop("validation_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT10_STRICT_PREINGESTION_VALIDATION_V1", core)
    assert artifact["validation_verdict"] == "PASS_STRICT_PREINGESTION_VALIDATION_ONLY"
    assert artifact["source_sha256"] == "454a0c568c12a46224407f6c3b378f8197e3f4653cca6d897d1c03b8d94821d7"
    assert artifact["declaration_sha256"] == "4bc43e0b03964d50685fe2e5193fafcbfee2c14cd35ebe777fdba64c15540435"
    assert artifact["deterministic_blockers"] == []
    assert artifact["repair_performed"] is False
    assert artifact["proposition_sufficiency_evaluated"] is False
    assert artifact["prospective_identities_derived"] is False
    assert artifact["constructor_source_compatibility_release_or_invocation_performed"] is False
    assert artifact["realization_candidate_emission_or_preemission_conformance_performed"] is False
    assert all(value is False for value in artifact["authority_matrix"].values())
