"""Adversarial verifier for the Batch 2 owned-authority protocol package."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"


def load(name: str) -> tuple[dict, str]:
    data = (ART / name).read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: dict, identity_field: str) -> str:
    unsealed = dict(value)
    unsealed.pop(identity_field)
    return hashlib.sha256(canonical({"namespace": namespace, "value": unsealed})).hexdigest()


def main() -> None:
    protocol, protocol_sha = load("humor-mechanics-batch2-owned-authority-acquisition-protocol-v1.json")
    rights, rights_sha = load("humor-mechanics-batch2-owned-authority-rights-instruments-v1.json")
    schema, schema_sha = load("humor-mechanics-batch2-owned-authority-source-package-v1.schema.json")
    escrow, escrow_sha = load("humor-mechanics-batch2-owned-authority-access-escrow-v1.json")
    audit, _ = load("humor-mechanics-batch2-owned-authority-acquisition-protocol-v1-audit.json")
    expected_false = {key: False for key in [
        "source_acquisition", "content_ingestion", "mechanism_assignment", "candidate_construction",
        "surface_generation", "model_exposure", "training", "runtime_integration", "production_routing"]}
    require(protocol["current_authority_matrix"] == expected_false, "protocol action authority widened")
    require(rights["current_grants"] == expected_false and escrow["current_authority"] == expected_false,
            "subordinate artifact authority widened")
    require(audit["authority_matrix"] == expected_false, "audit authority widened")
    require(protocol["artifact_bindings"] == {
        "rights_sha256": rights_sha, "source_schema_sha256": schema_sha, "escrow_sha256": escrow_sha},
        "artifact hash binding mismatch")
    require(audit["protocol_sha256"] == protocol_sha, "audit protocol hash mismatch")
    require(audit["protocol_identity"] == protocol["protocol_identity"], "protocol identity mismatch")
    require(protocol["protocol_identity"] ==
            seal("B2_OWNED_AUTHORITY_ACQUISITION_PROTOCOL_V1", protocol, "protocol_identity"),
            "protocol canonical seal invalid")
    require(rights["rights_template_identity"] ==
            seal("B2_OWNED_AUTHORITY_RIGHTS_TEMPLATE_V1", rights, "rights_template_identity"),
            "rights canonical seal invalid")
    require(escrow["escrow_spec_identity"] ==
            seal("B2_OWNED_AUTHORITY_ESCROW_V1", escrow, "escrow_spec_identity"),
            "escrow canonical seal invalid")
    require(audit["verdict"] == "PASS_SOURCE_ONLY_PROTOCOL_CLEAN" and not audit["deterministic_defects_remaining"],
            "audit not clean")
    require(all(value == "PASS" for value in audit["checks"].values()), "adversarial check failed")
    require(len(audit["adversarial_mutation_cases"]) >= 11 and
            set(audit["adversarial_mutation_cases"].values()) == {"REJECTED"},
            "adversarial mutation suite incomplete or fail-open")
    require(rights["closed_permitted_use_classes"]["REJECTED_OR_UNRESOLVED"] ==
            {"discovery": False, "construction_evaluation": False, "training": False, "production": False},
            "ambiguous rights fail-open")
    require(len(rights["noninheritance"]) == 4, "rights inheritance ambiguity")
    require(escrow["ordering"].index("BLIND_SEAL") < escrow["ordering"].index("PARTITION_SPECIFIC_CONTENT_ACCESS"),
            "blind seal occurs after access")
    require(escrow["permanent_contamination"] == {
        "event_ids": [1538, 2617], "reassignment": False, "downstream_use": False},
        "permanent contamination changed")
    require(escrow["existing_reservations"]["status"] ==
            "OPAQUE_RESERVATIONS_ONLY_NOT_PROMOTED_OR_INSPECTED", "blind reservations promoted")
    require(schema["construction_authority"] is False, "source schema embeds construction authority")
    require(schema["additionalProperties"] is False, "source package permits hidden fields")
    required = set(schema["required"])
    require({"original_bytes_sha256", "rights_instrument_id", "propositions", "family_identities",
             "partition_seal", "contamination_ledger_head", "archive_object_identity"} <= required,
            "immutable package requirement missing")
    require("MECHANISM_ID" in protocol["mechanism_blind_assignment"]["constructor_never_receives"],
            "mechanism label exposed")
    require("OWNER_PREFERENCE" in protocol["mechanism_blind_assignment"]["constructor_never_receives"],
            "owner preference exposed")
    require(protocol["family_derivation"]["pre_assignment_rule"] ==
            "CREATIVE_PREMISE_IDENTITY_MUST_BE_UNASSIGNED_THROUGH_G01B_AND_PARTITION_SEAL",
            "creative premise can become covert pre-partition assignment")
    require(protocol["revocation_correction_supersession"]["partition_rule"] ==
            "SUCCESSOR_REMAINS_IN_PREDECESSOR_FAMILY_PARTITION", "revision family can cross partitions")
    require(protocol["next_phase"] ==
            "SEPARATELY_AUTHORIZED_ACQUISITION_CHANNEL_AND_RIGHTS_INSTRUMENT_QUALIFICATION_ONLY",
            "next phase contains hidden acquisition authority")
    require(audit["actions_performed"] == {
        "sources_acquired": 0, "content_ingested": 0, "blind_surfaces_inspected": 0,
        "assignments_created": 0, "candidates_constructed": 0, "model_calls": 0},
        "source-only boundary violated")
    print(json.dumps({"verdict": "PASS_SOURCE_ONLY_PROTOCOL_CLEAN",
                      "protocol_identity": protocol["protocol_identity"],
                      "protocol_sha256": protocol_sha, "all_action_authorities": False}, sort_keys=True))


if __name__ == "__main__":
    main()
