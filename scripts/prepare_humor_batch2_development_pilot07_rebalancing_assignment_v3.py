"""Prepare Pilot 07's label-blind rebalancing assignment under remediated governance."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "2abc9fb59531495498f2743e86d218d93cae1d8e"
INGESTION = "docs/artifacts/humor-mechanics-batch2-development-pilot07-ingestion-v1/"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def load(path: str) -> dict[str, Any]:
    return json.loads(blob(path))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def write(name: str, value: Any) -> None:
    path = ART / name
    require(not path.exists(), "artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    receipt = load("docs/artifacts/humor-mechanics-batch2-development-pilot07-proposition-sufficiency-receipt-v3-1.json")
    sufficiency_audit = load("docs/artifacts/humor-mechanics-batch2-development-pilot07-proposition-sufficiency-remediation-audit-v3-1.json")
    governance = load("docs/artifacts/humor-mechanics-batch2-order-robust-causal-spine-governance-v3.json")
    package = load(INGESTION + "source-package.json")
    envelope = load(INGESTION + "factual-authority-envelope.json")
    source = blob(INGESTION + "source.utf8.txt")
    require(receipt["receipt_identity"] == "a242e3019b6d204dc6b1673da1c235bbd182887c12bbfdbb19680e48392a9d04", "receipt")
    require(sufficiency_audit["audit_identity"] == "79438069c5d5747fe2d1dd92a83721b712bc4b7d7f8b3c270331c49fca57333f", "audit")
    require(receipt["verdict"] == "PASS_SELECTED_PROPOSITION_SUFFICIENT" and receipt["selected_proposition_id"] == "P5", "selection")
    require(governance["governance_identity"] == receipt["governance_identity"] == "4848bd025e43eff6652e4c2024072760d372ca4ac7427e5f21e1d2c4bcdb35dc", "governance")
    selected = next(p for p in envelope["propositions"] if p["proposition_id"] == "P5")
    span = selected["supporting_span"]
    bs, be = span["utf8_byte_coordinates"]
    selected_bytes = source[bs:be]
    require(hashlib.sha256(selected_bytes).hexdigest() == receipt["selected_supporting_span_sha256"] == "37e92f7c6b55729e6efee58d6145b8184fc0ac98410ab0d412b51f54605a1899", "span")
    require(receipt["authorized_visible_context_sha256"] == hashlib.sha256(selected_bytes).hexdigest(), "context")

    obligation_core = {
        "schema_name": "batch2-development-pilot07-rebalancing-obligation-family-v3",
        "schema_version": "3.0.0",
        "family_version": "ORDER_ROBUST_CAUSAL_SPINE_V3",
        "governance_identity": governance["governance_identity"],
        "sufficiency_schema_identity": receipt["schema_identity"],
        "constructor_visible_obligation": {
            **governance["constructor_visible_obligation"],
            "obligation_version": "DEVELOPMENT_TRANSFORMATION_V3_01",
        },
        "candidate_surface": None,
        "construction_authority": False,
    }
    obligation_id = seal("B2_DEVELOPMENT_PILOT07_REBALANCING_OBLIGATION_FAMILY_V3", obligation_core)
    obligation = {**obligation_core, "obligation_family_identity": obligation_id}
    mapping_core = {
        "schema_name": "batch2-development-pilot07-sealed-rebalancing-assignment-v3",
        "schema_version": "3.0.0",
        "admission_identity": receipt["admission_identity"],
        "sufficiency_receipt_identity": receipt["receipt_identity"],
        "selected_proposition_id": "P5",
        "selected_supporting_span_sha256": span["span_sha256"],
        "authorized_visible_context_sha256": receipt["authorized_visible_context_sha256"],
        "obligation_family_identity": obligation_id,
        "target_mapping": {"mechanism_id": "HMCV1-B02-M03-ABSURD_LOGICAL_EXTENSION", "mechanism_name": "Absurd Logical Extension", "frozen_plan_option": "M13_ABSURD_LOGICAL_EXTENSION"},
        "close_alternative_profile": {"primary_neighbor": "LITERALIZATION", "secondary_neighbors": ["MISDIRECTION", "ESCALATION"],
                                      "required_closed_choices": ["TARGET", "LITERALIZATION", "MISDIRECTION", "ESCALATION", "NONE", "AMBIGUOUS"],
                                      "distinct_from_pilot03_pilot04": True},
        "partition": "DEVELOPMENT",
        "creative_premise_family_id": "UNASSIGNED",
        "constructor_access": False,
        "candidate_surface": None,
        "status": "SEALED_PROPOSAL_NOT_RELEASED",
    }
    mapping_id = seal("B2_DEVELOPMENT_PILOT07_SEALED_REBALANCING_ASSIGNMENT_V3", mapping_core)
    mapping = {**mapping_core, "sealed_assignment_identity": mapping_id}
    instance_id = seal("B2_DEVELOPMENT_PILOT07_UNLABELED_REBALANCING_OBLIGATION_INSTANCE_V3",
                       {"assignment": mapping_id, "sufficiency_receipt": receipt["receipt_identity"], "proposition": "P5", "obligation_family": obligation_id})
    visible_envelope = {key: envelope[key] for key in ("authority_scope", "source_commitment", "source_sha256", "world_scope")}
    visible_envelope["propositions"] = [selected]
    packet_core = {
        "schema_name": "batch2-development-pilot07-constructor-facing-rebalancing-assignment-proposal-v3",
        "schema_version": "3.0.0",
        "source_package_identity": package["source_package_identity"],
        "sufficiency_receipt_identity": receipt["receipt_identity"],
        "selected_proposition_id": "P5",
        "selected_supporting_span_sha256": span["span_sha256"],
        "authorized_visible_context_sha256": receipt["authorized_visible_context_sha256"],
        "exact_authorized_visible_context_utf8": selected_bytes.decode(),
        "closed_factual_authority_envelope": visible_envelope,
        "unlabeled_operational_obligation": {"obligation_instance_identity": instance_id, **obligation["constructor_visible_obligation"]},
        "output_constraints": {"language": "ROMANIAN", "register": "IDIOMATIC_NATURAL_CONCRETE_ROMANIAN", "length_profile": "COMMON_BATCH2_NEUTRAL_PROFILE_30_TO_90_WORDS_1_TO_3_SENTENCES",
                               "prohibited": ["CANNED_OPENING", "GOVERNANCE_META_LANGUAGE", "PROCEDURAL_ABSTRACT_REGISTER", "UNBOUND_REFERENCE", "FACTUAL_WIDENING"]},
        "mapping_commitment": seal("B2_DEVELOPMENT_PILOT07_REBALANCING_MAPPING_COMMITMENT_V3", mapping),
        "immutable_assignment_identity": mapping_id,
        "creative_premise_family_id": "UNASSIGNED",
        "status": "PROPOSAL_ZERO_CONSTRUCTION_NO_RELEASE",
        "constructor_invoked": False,
        "candidate_surface": None,
        "authority_matrix": {key: False for key in ("constructor_release", "construction", "generation", "creative_premise_assignment", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    packet_id = seal("B2_DEVELOPMENT_PILOT07_REBALANCING_CONSTRUCTOR_PACKET_V3", packet_core)
    packet = {**packet_core, "constructor_facing_packet_identity": packet_id}
    visible = canonical(packet)
    forbidden = [rb"HMCV1", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension", rb"LITERALIZATION", rb"MISDIRECTION", rb"ESCALATION", rb"mechanism_id", rb"mechanism_name", rb"close_alternative", rb"BLIND_EVALUATION", rb"owner.preference"]
    hits = [pattern.decode() for pattern in forbidden if re.search(pattern, visible, re.I)]
    require(not hits, f"visible leakage: {hits}")
    require(len(packet["closed_factual_authority_envelope"]["propositions"]) == 1, "extra proposition")
    require(packet["exact_authorized_visible_context_utf8"].encode() == selected_bytes, "context equality")
    require(all(value is False for value in packet["authority_matrix"].values()), "authority")
    audit_core = {
        "schema_name": "batch2-development-pilot07-rebalancing-assignment-design-audit-v3",
        "schema_version": "3.0.0",
        "sealed_assignment_identity": mapping_id,
        "constructor_facing_packet_identity": packet_id,
        "obligation_family_identity": obligation_id,
        "sufficiency_receipt_binding": "PASS_EXACT",
        "selected_proposition_binding": "PASS_EXACT_P5_ONLY",
        "authorized_span_binding": "PASS_EXACT",
        "extra_proposition_context": "ABSENT",
        "taxonomy_and_alternative_label_scan": "PASS_ZERO_HITS",
        "factual_authority_widening": "ABSENT",
        "creative_premise_assignment": "ABSENT_UNASSIGNED",
        "constructor_release": "NOT_PERFORMED",
        "constructor_invocations": 0,
        "candidate_surfaces_created": 0,
        "downstream_authority": False,
        "deterministic_blockers": [],
        "verdict": "PASS_SAFE_REBALANCING_ASSIGNMENT_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT07_REBALANCING_ASSIGNMENT_DESIGN_AUDIT_V3", audit_core)}
    write("humor-mechanics-batch2-development-pilot07-rebalancing-obligation-family-v3.json", obligation)
    write("humor-mechanics-batch2-development-pilot07-sealed-rebalancing-assignment-v3.json", mapping)
    write("humor-mechanics-batch2-development-pilot07-constructor-facing-rebalancing-assignment-proposal-v3.json", packet)
    write("humor-mechanics-batch2-development-pilot07-rebalancing-assignment-design-audit-v3.json", audit)
    print(json.dumps({"verdict": "SAFE_REBALANCING_ASSIGNMENT_PROPOSAL_ZERO_CONSTRUCTION_NO_RELEASE", "obligation_family_identity": obligation_id,
                      "sealed_assignment_identity": mapping_id, "constructor_facing_packet_identity": packet_id,
                      "obligation_instance_identity": instance_id, "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
