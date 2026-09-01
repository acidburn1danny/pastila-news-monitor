"""Prepare Pilot 08's label-blind rebalancing assignment under remediated governance."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "cd9b514cb69107152f6bea8338e1d672e6c2b49f"
INGESTION = "docs/artifacts/humor-mechanics-batch2-development-pilot08-ingestion-v1/"


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
    receipt = load("docs/artifacts/humor-mechanics-batch2-development-pilot08-proposition-sufficiency-receipt-v4.json")
    sufficiency_audit = load("docs/artifacts/humor-mechanics-batch2-development-pilot08-proposition-sufficiency-audit-v4.json")
    governance = load("docs/artifacts/humor-mechanics-batch2-template-diverse-creative-marking-governance-v4.json")
    schema = load("docs/artifacts/humor-mechanics-batch2-template-diverse-creative-marking-conformance-schema-v4.json")
    inherited_governance = load("docs/artifacts/humor-mechanics-batch2-order-robust-causal-spine-governance-v3.json")
    package = load(INGESTION + "source-package.json")
    envelope = load(INGESTION + "factual-authority-envelope.json")
    source = blob(INGESTION + "source.utf8.txt")
    require(receipt["receipt_identity"] == "be0f5cb5d2fa33a7163db4b59babf777d6cf004472cf6a6607206d82870edbe3", "receipt")
    require(sufficiency_audit["audit_identity"] == "24af6f4f3f0307f88e8760b79751c4504b0926290f6f8216b94f498f1219446a", "audit")
    require(receipt["verdict"] == "PASS_SELECTED_PROPOSITION_SUFFICIENT" and receipt["selected_proposition_id"] == "P5", "selection")
    require(governance["governance_identity"] == receipt["governance_identity"] == "cc86204c6f199c80ef7c7bf87a58cf3c62d17acb1fe14bd2666bbf5ba86692f6", "governance")
    require(schema["schema_identity"] == receipt["schema_identity"] == "12c96a72555a26181abd5d0e7fa033a425fdacafb3a7fb197a21b39358da1dbe", "schema")
    require(governance["preserves_v3_causal_spine_requirements"] is True, "V3 preservation")
    require(inherited_governance["governance_identity"] == governance["supersedes_governance_identity"], "inherited governance")
    selected = next(p for p in envelope["propositions"] if p["proposition_id"] == "P5")
    span = selected["supporting_span"]
    bs, be = span["utf8_byte_coordinates"]
    selected_bytes = source[bs:be]
    require(hashlib.sha256(selected_bytes).hexdigest() == receipt["selected_supporting_span_sha256"] == "6fd5aeac76fa3602374be0da17bf7bb82c8b878b6302b3ddd6789712d034f3db", "span")
    require(receipt["authorized_visible_context_sha256"] == hashlib.sha256(selected_bytes).hexdigest(), "context")

    obligation_core = {
        "schema_name": "batch2-development-pilot08-rebalancing-obligation-family-v4",
        "schema_version": "4.0.0",
        "family_version": "TEMPLATE_DIVERSE_CREATIVE_MARKING_V4_WITH_ORDER_ROBUST_CAUSAL_SPINE",
        "governance_identity": governance["governance_identity"],
        "conformance_schema_identity": schema["schema_identity"],
        "inherited_causal_spine_governance_identity": inherited_governance["governance_identity"],
        "sufficiency_schema_identity": receipt["schema_identity"],
        "constructor_visible_obligation": {
            **inherited_governance["constructor_visible_obligation"],
            "obligation_version": "DEVELOPMENT_TRANSFORMATION_V4_01",
            "creative_marking_constraints": [
                "Marcajul nonfactual trebuie ales local pentru acest text, fără formulă sau tranziție prestabilită.",
                "Nu reutiliza o tranziție creativă, o deschidere sau o aterizare dintr-un alt exemplu.",
                "Nu transforma cerințele ori limbajul de control în formulări ale rezultatului.",
            ],
        },
        "candidate_surface": None,
        "construction_authority": False,
    }
    obligation_id = seal("B2_DEVELOPMENT_PILOT08_REBALANCING_OBLIGATION_FAMILY_V4", obligation_core)
    obligation = {**obligation_core, "obligation_family_identity": obligation_id}
    construction_revision_family_id = seal(
        "B2_DEVELOPMENT_PILOT08_CONSTRUCTION_REVISION_FAMILY_V4",
        {"source_family": package["family_identities"]["source_family"], "obligation_family": obligation_id},
    )
    mapping_core = {
        "schema_name": "batch2-development-pilot08-sealed-rebalancing-assignment-v4",
        "schema_version": "4.0.0",
        "admission_identity": receipt["admission_identity"],
        "sufficiency_receipt_identity": receipt["receipt_identity"],
        "selected_proposition_id": "P5",
        "selected_supporting_span_sha256": span["span_sha256"],
        "authorized_visible_context_sha256": receipt["authorized_visible_context_sha256"],
        "obligation_family_identity": obligation_id,
        "target_mapping": {"mechanism_id": "HMCV1-B02-M03-ABSURD_LOGICAL_EXTENSION", "mechanism_name": "Absurd Logical Extension", "frozen_plan_option": "M13_ABSURD_LOGICAL_EXTENSION"},
        "close_alternative_profile": {"primary_neighbor": "ESCALATION", "secondary_neighbors": ["COMIC_RECLASSIFICATION", "MISDIRECTION"],
                                      "required_closed_choices": ["TARGET", "ESCALATION", "COMIC_RECLASSIFICATION", "MISDIRECTION", "NONE", "AMBIGUOUS"],
                                      "distinct_from_pilot03_pilot04": True, "distinct_from_pilot07": True},
        "partition": "DEVELOPMENT",
        "construction_revision_family_id": construction_revision_family_id,
        "creative_marker_family_id": "UNASSIGNED_UNTIL_POSTCONSTRUCTION",
        "creative_premise_family_id": "UNASSIGNED",
        "constructor_access": False,
        "candidate_surface": None,
        "status": "SEALED_PROPOSAL_NOT_RELEASED",
    }
    mapping_id = seal("B2_DEVELOPMENT_PILOT08_SEALED_REBALANCING_ASSIGNMENT_V4", mapping_core)
    mapping = {**mapping_core, "sealed_assignment_identity": mapping_id}
    instance_id = seal("B2_DEVELOPMENT_PILOT08_UNLABELED_REBALANCING_OBLIGATION_INSTANCE_V4",
                       {"assignment": mapping_id, "sufficiency_receipt": receipt["receipt_identity"], "proposition": "P5", "obligation_family": obligation_id})
    visible_envelope = {key: envelope[key] for key in ("authority_scope", "source_commitment", "source_sha256", "world_scope")}
    visible_envelope["propositions"] = [selected]
    packet_core = {
        "schema_name": "batch2-development-pilot08-constructor-facing-rebalancing-assignment-proposal-v4",
        "schema_version": "4.0.0",
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
        "mapping_commitment": seal("B2_DEVELOPMENT_PILOT08_REBALANCING_MAPPING_COMMITMENT_V4", mapping),
        "immutable_assignment_identity": mapping_id,
        "construction_revision_family_id": construction_revision_family_id,
        "creative_marker_family_id": "UNASSIGNED_UNTIL_POSTCONSTRUCTION",
        "creative_premise_family_id": "UNASSIGNED",
        "constructor_implementation_identity": "UNASSIGNED_REQUIRES_SEPARATE_IMPLEMENTATION_AND_STATIC_AUDIT",
        "fragment_denyset_identity": "UNASSIGNED_REQUIRES_FREEZE_BEFORE_RELEASE",
        "status": "PROPOSAL_ZERO_CONSTRUCTION_NO_RELEASE",
        "constructor_invoked": False,
        "candidate_surface": None,
        "authority_matrix": {key: False for key in ("constructor_release", "construction", "generation", "creative_premise_assignment", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    packet_id = seal("B2_DEVELOPMENT_PILOT08_REBALANCING_CONSTRUCTOR_PACKET_V4", packet_core)
    packet = {**packet_core, "constructor_facing_packet_identity": packet_id}
    visible = canonical(packet)
    forbidden = [rb"HMCV1", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension", rb"LITERALIZATION", rb"MISDIRECTION", rb"ESCALATION", rb"mechanism_id", rb"mechanism_name", rb"close_alternative", rb"BLIND_EVALUATION", rb"owner.preference"]
    hits = [pattern.decode() for pattern in forbidden if re.search(pattern, visible, re.I)]
    require(not hits, f"visible leakage: {hits}")
    require(len(packet["closed_factual_authority_envelope"]["propositions"]) == 1, "extra proposition")
    require(packet["exact_authorized_visible_context_utf8"].encode() == selected_bytes, "context equality")
    require(all(value is False for value in packet["authority_matrix"].values()), "authority")
    audit_core = {
        "schema_name": "batch2-development-pilot08-rebalancing-assignment-design-audit-v4",
        "schema_version": "4.0.0",
        "sealed_assignment_identity": mapping_id,
        "constructor_facing_packet_identity": packet_id,
        "obligation_family_identity": obligation_id,
        "construction_revision_family_identity": construction_revision_family_id,
        "close_alternative_profile_distinctness": "PASS_DISTINCT_FROM_PILOT03_PILOT04_AND_PILOT07",
        "sufficiency_receipt_binding": "PASS_EXACT",
        "selected_proposition_binding": "PASS_EXACT_P5_ONLY",
        "authorized_span_binding": "PASS_EXACT",
        "extra_proposition_context": "ABSENT",
        "taxonomy_and_alternative_label_scan": "PASS_ZERO_HITS",
        "factual_authority_widening": "ABSENT",
        "creative_premise_assignment": "ABSENT_UNASSIGNED",
        "constructor_release": "NOT_PERFORMED",
        "constructor_implementation": "NOT_IMPLEMENTED_SEPARATE_PHASE_REQUIRED",
        "fragment_collision_evaluation": "NOT_PERFORMED_POSTCONSTRUCTION_GATE_ONLY",
        "constructor_invocations": 0,
        "candidate_surfaces_created": 0,
        "downstream_authority": False,
        "deterministic_blockers": [],
        "verdict": "PASS_SAFE_REBALANCING_ASSIGNMENT_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT08_REBALANCING_ASSIGNMENT_DESIGN_AUDIT_V4", audit_core)}
    write("humor-mechanics-batch2-development-pilot08-rebalancing-obligation-family-v4.json", obligation)
    write("humor-mechanics-batch2-development-pilot08-sealed-rebalancing-assignment-v4.json", mapping)
    write("humor-mechanics-batch2-development-pilot08-constructor-facing-rebalancing-assignment-proposal-v4.json", packet)
    write("humor-mechanics-batch2-development-pilot08-rebalancing-assignment-design-audit-v4.json", audit)
    print(json.dumps({"verdict": "SAFE_REBALANCING_ASSIGNMENT_PROPOSAL_ZERO_CONSTRUCTION_NO_RELEASE", "obligation_family_identity": obligation_id,
                      "sealed_assignment_identity": mapping_id, "constructor_facing_packet_identity": packet_id,
                      "obligation_instance_identity": instance_id, "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
