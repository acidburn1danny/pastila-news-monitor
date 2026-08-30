"""Verify content-free custodial appointments and signing readiness."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"


def load(name: str) -> tuple[dict, str]:
    raw = (ART / name).read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: dict, field: str) -> str:
    body = dict(value)
    body.pop(field)
    return hashlib.sha256(canonical({"namespace": namespace, "value": body})).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    appointments, appointments_sha = load("humor-mechanics-batch2-custodial-appointment-registry-v1.json")
    signing, signing_sha = load("humor-mechanics-batch2-custodial-signing-envelope-v1.json")
    genesis, genesis_sha = load("humor-mechanics-batch2-custodial-access-ledger-genesis-v1.json")
    fixtures, fixtures_sha = load("humor-mechanics-batch2-custodial-signing-readiness-fixtures-v1.json")
    readiness, readiness_sha = load("humor-mechanics-batch2-custodial-appointment-signing-readiness-v1.json")
    audit, _ = load("humor-mechanics-batch2-custodial-signing-readiness-v1-audit.json")
    false_matrix = {key: False for key in [
        "source_acquisition", "content_ingestion", "mechanism_assignment", "candidate_construction",
        "surface_generation", "model_exposure", "training", "runtime_integration", "production_routing"]}
    require(appointments["appointment_registry_identity"] ==
            seal("B2_CUSTODIAL_APPOINTMENT_REGISTRY_V1", appointments, "appointment_registry_identity"),
            "appointment seal invalid")
    require(signing["signing_spec_identity"] ==
            seal("B2_CUSTODIAL_SIGNING_ENVELOPE_V1", signing, "signing_spec_identity"), "signing seal invalid")
    require(genesis["entry_hash"] ==
            seal("B2_CUSTODIAL_ACCESS_LEDGER_ENTRY_V1", genesis, "entry_hash"), "genesis seal invalid")
    require(fixtures["fixture_identity"] ==
            seal("B2_CUSTODIAL_SIGNING_READINESS_FIXTURES_V1", fixtures, "fixture_identity"), "fixture seal invalid")
    require(readiness["readiness_identity"] ==
            seal("B2_CUSTODIAL_APPOINTMENT_SIGNING_READINESS_V1", readiness, "readiness_identity"),
            "readiness seal invalid")
    principals = [item["principal_identity"] for item in appointments["appointments"]]
    require(len(principals) == len(set(principals)) == 6, "custodial principals not distinct")
    require(all(item["appointment_status"] == "CONDITIONALLY_APPOINTED_NONOPERATIONAL" and
                item["public_key_status"] == "UNREGISTERED" and
                item["credential_status"] == "UNPROVISIONED" and
                not item["operational_access"] and not item["source_or_content_access"]
                for item in appointments["appointments"]), "appointment activated")
    require(appointments["current_authority"] == readiness["authority_matrix"] ==
            audit["authority_matrix"] == false_matrix, "authority widened")
    require(signing["secret_keys_created"] == signing["public_keys_registered"] == 0 and
            not signing["signing_enabled"], "signing activated or key invented")
    require(not genesis["source_content_present"] and not genesis["blind_content_present"] and
            not genesis["operational_authority"] and not genesis["object_commitments"], "genesis contains content")
    require(fixtures["metadata_only"] and fixtures["real_keys_used"] == 0 and
            fixtures["real_signatures_created"] == 0, "fixture uses real signing or content")
    require(len(fixtures["rejected_cases"]) >= 13, "adversarial fixture coverage incomplete")
    require(readiness["bindings"] == {
        "appointments_sha256": appointments_sha, "signing_spec_sha256": signing_sha,
        "ledger_genesis_sha256": genesis_sha, "fixtures_sha256": fixtures_sha}, "readiness binding mismatch")
    require(readiness["verdict"] == "READY_FOR_SEPARATE_PUBLIC_KEY_REGISTRATION_NOT_OPERATION",
            "readiness overclaims operation")
    require(readiness["next_phase"] ==
            "SEPARATELY_AUTHORIZED_PUBLIC_KEY_REGISTRATION_AND_PROOF_OF_POSSESSION_ONLY",
            "next phase contains source authority")
    require(audit["readiness_sha256"] == readiness_sha and
            audit["readiness_identity"] == readiness["readiness_identity"], "audit binding mismatch")
    require(audit["verdict"] == "PASS_CONTENT_FREE_CUSTODIAL_SIGNING_READINESS" and
            not audit["deterministic_defects_remaining"] and set(audit["checks"].values()) == {"PASS"},
            "audit not clean")
    require(fixtures["actions_performed"] == {
        "sources_acquired": 0, "content_ingested": 0, "keys_generated": 0,
        "signatures_created": 0, "credentials_provisioned": 0, "model_calls": 0},
        "content-free readiness boundary violated")
    print(json.dumps({"verdict": audit["verdict"],
                      "readiness_identity": readiness["readiness_identity"],
                      "logical_custodians": len(principals), "operational_access": False,
                      "all_action_authorities": False}, sort_keys=True))


if __name__ == "__main__":
    main()
