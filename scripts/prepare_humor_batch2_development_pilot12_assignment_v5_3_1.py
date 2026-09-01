"""Prepare Pilot 12 label-blind assignment under Governance V5.3.1."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "adfa1663e754986ed5f2f9d26845888bc4588d16"
INGESTION = "docs/artifacts/humor-mechanics-batch2-development-pilot12-ingestion-v1/"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def blob(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def load(path: str) -> dict[str, Any]:
    return json.loads(blob(path))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def write(name: str, value: Any) -> None:
    path = ART / name
    require(not path.exists(), f"artifact exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    receipt = load("docs/artifacts/humor-mechanics-batch2-development-pilot12-proposition-sufficiency-receipt-v5-3-1.json")
    sufficiency_audit = load("docs/artifacts/humor-mechanics-batch2-development-pilot12-proposition-sufficiency-audit-v5-3-1.json")
    governance = load("docs/artifacts/humor-mechanics-batch2-semantic-edge-role-continuity-governance-v5-3.json")
    schema = load("docs/artifacts/humor-mechanics-batch2-semantic-edge-role-continuity-conformance-schema-v5-3.json")
    alignment = load("docs/artifacts/humor-mechanics-batch2-development-constructor-surface-witness-alignment-contract-v5-3-1.json")
    operational = load("docs/artifacts/humor-mechanics-batch2-order-robust-causal-spine-governance-v3.json")
    package = load(INGESTION + "source-package.json")
    envelope = load(INGESTION + "factual-authority-envelope.json")
    source = blob(INGESTION + "source.utf8.txt")
    require(receipt["receipt_identity"] == "f8f754e005fd50031c8a7a0daf180c325eb0b0d49c9eaea8dbcbcbf2ac45998c", "receipt")
    require(sufficiency_audit["audit_identity"] == "21395aa6a314d10a9ee26d0b39b4c4b744cfc442872a9f7b999967299a0c061d", "audit")
    require(receipt["verdict"] == "PASS_SELECTED_PROPOSITION_SUFFICIENT", "verdict")
    require(receipt["selected_proposition_id"] == "P5" and receipt["eligible_propositions"] == ["P5", "P6"], "selection")
    require(receipt["selection_rule"] == "FIRST_SOURCE_ORDER_PROPOSITION_PASSING_ALL_SUFFICIENCY_REQUIREMENTS", "rule")
    require(receipt["semantic_role_or_affordance_planning_performed"] is False, "semantic planning")
    require(receipt["realization_witness_or_morphological_alignment_planning_performed"] is False, "realization planning")
    require(governance["governance_identity"] == receipt["governance_identity"], "governance")
    require(schema["schema_identity"] == receipt["schema_identity"], "schema")
    require(alignment["successor_contract_identity"] == receipt["alignment_contract_identity"], "alignment")
    selected = next(item for item in envelope["propositions"] if item["proposition_id"] == "P5")
    span = selected["supporting_span"]
    bs, be = span["utf8_byte_coordinates"]
    selected_bytes = source[bs:be]
    require(hashlib.sha256(selected_bytes).hexdigest() == receipt["selected_supporting_span_sha256"], "span")
    require(receipt["authorized_visible_context_sha256"] == hashlib.sha256(selected_bytes).hexdigest(), "context")

    visible_obligation = dict(operational["constructor_visible_obligation"])
    visible_obligation.update({
        "obligation_version": "DEVELOPMENT_TRANSFORMATION_V5_3_1_01",
        "future_phase_constraints": [
            "Într-o fază separată, înaintea realizării, fiecare operand și relație trebuie validate din propoziția selectată ori dintr-un rezultat local explicit.",
            "O reclasificare nu poate crea singură agenție, autoritate, proprietate, permisiune, capacitate sau posibilitatea unei acțiuni.",
            "Fiecare legătură, inclusiv cea terminală, trebuie să aibă compatibilitate locală și dependență contrafactuală explicită.",
            "Orice martor de suprafață viitor trebuie legat de coordonate reale; numai alinierile morfologice românești explicit licențiate sunt admise.",
        ],
        "creative_marking_constraints": [
            "Marcajul nonfactual trebuie ales local și firesc, fără formulă, tranziție, deschidere sau încheiere reutilizată.",
            "Nu transfera în rezultat limbajul cerințelor, planului, controlului, guvernanței sau validării.",
        ],
    })
    obligation_core = {
        "schema_name": "batch2-development-pilot12-label-blind-obligation-family-v5-3-1",
        "schema_version": "5.3.1", "family_version": "SEMANTIC_EDGE_ROLE_CONTINUITY_V5_3_1_NO_CONCRETE_SEMANTIC_PLAN",
        "governance_identity": governance["governance_identity"], "conformance_schema_identity": schema["schema_identity"],
        "alignment_contract_identity": alignment["successor_contract_identity"],
        "inherited_operational_governance_identity": operational["governance_identity"],
        "sufficiency_receipt_identity": receipt["receipt_identity"],
        "constructor_visible_obligation": visible_obligation, "semantic_role_signature": None,
        "affordance_topology": None, "realization_plan": None, "witness_topology": None,
        "morphological_alignment_opportunity": None, "candidate_surface": None,
        "construction_authority": False, "constructor_release_authority": False,
    }
    obligation_id = seal("B2_DEVELOPMENT_PILOT12_LABEL_BLIND_OBLIGATION_FAMILY_V5_3_1", obligation_core)
    obligation = {**obligation_core, "obligation_family_identity": obligation_id}
    revision_family = seal("B2_DEVELOPMENT_PILOT12_CONSTRUCTION_REVISION_FAMILY_V5_3_1",
                           {"source_family": package["family_identities"]["source_family"],
                            "obligation_family": obligation_id})
    mapping_core = {
        "schema_name": "batch2-development-pilot12-sealed-assignment-v5-3-1", "schema_version": "5.3.1",
        "admission_identity": receipt["admission_identity"], "sufficiency_receipt_identity": receipt["receipt_identity"],
        "selected_proposition_id": "P5", "selected_supporting_span_sha256": span["span_sha256"],
        "authorized_visible_context_sha256": receipt["authorized_visible_context_sha256"],
        "obligation_family_identity": obligation_id,
        "target_mapping": {"mechanism_id": "HMCV1-B02-M03-ABSURD_LOGICAL_EXTENSION",
                           "mechanism_name": "Absurd Logical Extension",
                           "frozen_plan_option": "M13_ABSURD_LOGICAL_EXTENSION"},
        "eligible_but_unselected_propositions": ["P6"], "fallback_authority": "NONE",
        "pool_outcome": "INACCESSIBLE_NOT_EVALUATED", "partition": "DEVELOPMENT",
        "construction_revision_family_id": revision_family,
        "creative_marker_family_id": "UNASSIGNED_UNTIL_POSTCONSTRUCTION",
        "creative_premise_family_id": "UNASSIGNED", "semantic_role_signature": None,
        "affordance_topology": None, "realization_plan": None, "witness_topology": None,
        "morphological_alignment_opportunity": None, "constructor_access": False,
        "candidate_surface": None, "status": "SEALED_PROPOSAL_NOT_RELEASED",
    }
    mapping_id = seal("B2_DEVELOPMENT_PILOT12_SEALED_ASSIGNMENT_V5_3_1", mapping_core)
    mapping = {**mapping_core, "sealed_assignment_identity": mapping_id}
    instance_id = seal("B2_DEVELOPMENT_PILOT12_UNLABELED_OBLIGATION_INSTANCE_V5_3_1",
                       {"assignment": mapping_id, "sufficiency_receipt": receipt["receipt_identity"],
                        "proposition": "P5", "obligation_family": obligation_id})
    visible_envelope = {key: envelope[key] for key in ("authority_scope", "source_commitment", "source_sha256", "world_scope")}
    visible_envelope["propositions"] = [selected]
    authority_names = ("constructor_v5_3_1_source_compatibility_evaluation", "semantic_role_or_affordance_planning",
                       "semantic_plan_evaluation", "constructor_release", "constructor_invocation", "realization",
                       "candidate_emission", "coordinate_bound_semantic_conformance", "semantic_edge_validation",
                       "fragment_collision_evaluation", "g02", "g02c", "g03", "g04b_pool_certification",
                       "model_exposure", "training", "runtime_integration", "production_routing")
    packet_core = {
        "schema_name": "batch2-development-pilot12-constructor-facing-assignment-proposal-v5-3-1",
        "schema_version": "5.3.1", "source_package_identity": package["source_package_identity"],
        "sufficiency_receipt_identity": receipt["receipt_identity"], "selected_proposition_id": "P5",
        "selected_supporting_span_sha256": span["span_sha256"],
        "authorized_visible_context_sha256": receipt["authorized_visible_context_sha256"],
        "exact_authorized_visible_context_utf8": selected_bytes.decode(),
        "closed_factual_authority_envelope": visible_envelope,
        "unlabeled_operational_obligation": {"obligation_instance_identity": instance_id, **visible_obligation},
        "output_constraints": {"language": "ROMANIAN", "register": "IDIOMATIC_NATURAL_CONCRETE_ROMANIAN",
                               "length_profile": "COMMON_BATCH2_NEUTRAL_PROFILE_30_TO_90_WORDS_1_TO_3_SENTENCES",
                               "prohibited": ["CANNED_OPENING_OR_TRANSITION", "GOVERNANCE_OR_INSTRUCTION_META_LANGUAGE",
                                              "PROCEDURAL_ABSTRACT_REGISTER", "UNBOUND_REFERENCE_OR_OPERAND",
                                              "FACTUAL_WIDENING"]},
        "mapping_commitment": seal("B2_DEVELOPMENT_PILOT12_MAPPING_COMMITMENT_V5_3_1", mapping),
        "immutable_assignment_identity": mapping_id, "construction_revision_family_id": revision_family,
        "creative_marker_family_id": "UNASSIGNED_UNTIL_POSTCONSTRUCTION",
        "creative_premise_family_id": "UNASSIGNED", "constructor_contract_identity": governance["constructor_contract_identity"],
        "alignment_contract_identity": alignment["successor_contract_identity"],
        "constructor_implementation_identity": "UNASSIGNED_PENDING_SEPARATE_V5_3_1_SOURCE_COMPATIBILITY_GATE",
        "constructor_v5_3_1_source_compatibility_evaluated": False, "semantic_role_signature": None,
        "affordance_topology": None, "realization_plan": None, "witness_topology": None,
        "morphological_alignment_opportunity": None,
        "fragment_denyset_identity": "UNASSIGNED_REQUIRES_FREEZE_BEFORE_RELEASE",
        "unselected_proposition_or_fallback_authority": "ABSENT", "status": "PROPOSAL_ZERO_CONSTRUCTION_NO_RELEASE_NO_SEMANTIC_PLANNING",
        "constructor_invoked": False, "candidate_surface": None,
        "authority_matrix": {key: False for key in authority_names},
    }
    packet_id = seal("B2_DEVELOPMENT_PILOT12_CONSTRUCTOR_FACING_ASSIGNMENT_PROPOSAL_V5_3_1", packet_core)
    packet = {**packet_core, "constructor_facing_packet_identity": packet_id}
    visible = canonical(packet)
    forbidden = [rb"HMCV1", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension",
                 rb"mechanism_id", rb"mechanism_name", rb"target_mapping", rb"pool_outcome",
                 rb"close_alternative", rb"answer_key", rb'"proposition_id":"P6"']
    hits = [pattern.decode() for pattern in forbidden if re.search(pattern, visible, re.I)]
    require(not hits, f"visible leakage: {hits}")
    require(len(packet["closed_factual_authority_envelope"]["propositions"]) == 1, "extra proposition")
    require(packet["exact_authorized_visible_context_utf8"].encode() == selected_bytes, "context")
    require(packet["semantic_role_signature"] is packet["affordance_topology"] is None, "semantic planning")
    require(packet["realization_plan"] is packet["witness_topology"] is None, "realization planning")
    require(packet["morphological_alignment_opportunity"] is None, "alignment planning")
    require(all(value is False for value in packet["authority_matrix"].values()), "authority")
    audit_core = {
        "schema_name": "batch2-development-pilot12-assignment-design-audit-v5-3-1", "schema_version": "5.3.1",
        "sealed_assignment_identity": mapping_id, "constructor_facing_packet_identity": packet_id,
        "obligation_family_identity": obligation_id, "obligation_instance_identity": instance_id,
        "construction_revision_family_identity": revision_family, "sufficiency_receipt_binding": "PASS_EXACT",
        "selected_proposition_binding": "PASS_EXACT_P5_ONLY", "authorized_span_binding": "PASS_EXACT",
        "p6_fallback_or_comparative_authority": "ABSENT", "extra_proposition_context": "ABSENT",
        "taxonomy_target_pool_answer_key_and_p6_scan": "PASS_ZERO_HITS",
        "operational_wording_leakage": "PASS_LABEL_BLIND_CUE_MINIMIZED",
        "source_shape_shortcut": "PASS_NO_PACKET_SHAPE_ENCODING", "factual_authority_widening": "ABSENT",
        "creative_premise_assignment": "ABSENT_UNASSIGNED", "creative_marker_assignment": "ABSENT_UNASSIGNED",
        "semantic_role_or_affordance_planning": "NOT_PERFORMED",
        "realization_witness_or_morphological_alignment_planning": "NOT_PERFORMED",
        "constructor_release": "NOT_PERFORMED", "constructor_contract_binding": "PASS_V5_3_AND_V5_3_1_ALIGNMENT_ONLY",
        "constructor_v5_3_1_source_compatibility_and_semantic_plan": "NOT_EVALUATED_SEPARATE_PHASE_REQUIRED",
        "constructor_implementation": "NOT_BOUND_TO_THIS_SOURCE", "fragment_collision_evaluation": "NOT_PERFORMED",
        "constructor_invocations": 0, "candidate_surfaces_created": 0, "downstream_authority": False,
        "deterministic_blockers": [],
        "verdict": "PASS_SAFE_ASSIGNMENT_ZERO_CONSTRUCTION_NO_RELEASE_NO_SEMANTIC_PLANNING",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT12_ASSIGNMENT_DESIGN_AUDIT_V5_3_1", audit_core)}
    write("humor-mechanics-batch2-development-pilot12-obligation-family-v5-3-1.json", obligation)
    write("humor-mechanics-batch2-development-pilot12-sealed-assignment-v5-3-1.json", mapping)
    write("humor-mechanics-batch2-development-pilot12-constructor-facing-assignment-proposal-v5-3-1.json", packet)
    write("humor-mechanics-batch2-development-pilot12-assignment-design-audit-v5-3-1.json", audit)
    print(json.dumps({"verdict": "SAFE_ASSIGNMENT_PROPOSAL_ZERO_CONSTRUCTION_NO_RELEASE_NO_SEMANTIC_PLANNING",
                      "obligation_family_identity": obligation_id, "obligation_instance_identity": instance_id,
                      "sealed_assignment_identity": mapping_id, "constructor_facing_packet_identity": packet_id,
                      "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
