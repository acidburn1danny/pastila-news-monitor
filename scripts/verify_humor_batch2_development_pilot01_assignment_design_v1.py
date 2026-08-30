"""Independent zero-construction verifier for Pilot 01 assignment design."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(name: str) -> dict[str, Any]:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def main() -> None:
    mapping = load("humor-mechanics-batch2-development-pilot01-sealed-assignment-mapping-v1.json")
    packet = load("humor-mechanics-batch2-development-pilot01-constructor-facing-assignment-proposal-v1.json")
    audit = load("humor-mechanics-batch2-development-pilot01-assignment-design-leakage-audit-v1.json")
    mapping_core = dict(mapping); mapping_id = mapping_core.pop("sealed_assignment_identity")
    require(seal("B2_DEVELOPMENT_PILOT01_SEALED_ASSIGNMENT_V1", mapping_core) == mapping_id, "mapping seal")
    packet_core = dict(packet); packet_id = packet_core.pop("constructor_facing_packet_identity")
    require(seal("B2_DEVELOPMENT_PILOT01_CONSTRUCTOR_PACKET_V1", packet_core) == packet_id, "packet seal")
    audit_core = dict(audit); audit_id = audit_core.pop("audit_identity")
    require(seal("B2_DEVELOPMENT_PILOT01_ASSIGNMENT_DESIGN_AUDIT_V1", audit_core) == audit_id, "audit seal")
    require(packet["immutable_assignment_identity"] == mapping_id, "assignment identity binding")
    require(packet["mapping_commitment"] == seal("B2_DEVELOPMENT_PILOT01_MAPPING_COMMITMENT_V1", mapping), "mapping commitment")
    forbidden = [rb"HMCV1-B02-M03", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension",
                 rb"mechanism_id", rb"mechanism_name", rb"BLIND_EVALUATION", rb"owner preference", rb"answer key"]
    packet_bytes = canonical(packet)
    require(not [x for x in forbidden if re.search(x, packet_bytes, re.I)], "label/mapping leak")
    require(packet["creative_premise_family_id"] == mapping["creative_premise_family_id"] == "UNASSIGNED", "creative premise")
    require(packet["candidate_surface"] is None and mapping["candidate_surface"] is None, "candidate surface")
    require(packet["constructor_invoked"] is False and all(value is False for value in packet["authority_matrix"].values()), "construction authority")
    require(len(packet["closed_factual_authority_envelope"]["propositions"]) == 6, "closed envelope")
    require(audit["verdict"] == "PASS_ZERO_CONSTRUCTION" and audit["constructor_invocations"] == audit["candidate_surfaces_created"] == 0, "audit outcome")
    print(json.dumps({"verdict": "INDEPENDENT_ASSIGNMENT_DESIGN_AUDIT_PASS_ZERO_CONSTRUCTION",
                      "sealed_assignment_identity": mapping_id, "constructor_facing_packet_identity": packet_id,
                      "audit_identity": audit_id, "creative_premise_family_id": "UNASSIGNED"}, sort_keys=True))


if __name__ == "__main__":
    main()
