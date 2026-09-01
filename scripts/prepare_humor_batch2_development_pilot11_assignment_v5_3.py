"""Prepare Pilot 11 label-blind assignment under Governance V5.3."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "f52fc4a0ce9a99afbf4852a0b1a64f904ff427b6"
INGESTION = "docs/artifacts/humor-mechanics-batch2-development-pilot11-ingestion-v1/"


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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    receipt = load("docs/artifacts/humor-mechanics-batch2-development-pilot11-proposition-sufficiency-receipt-v5-3.json")
    sufficiency_audit = load("docs/artifacts/humor-mechanics-batch2-development-pilot11-proposition-sufficiency-audit-v5-3.json")
    governance = load("docs/artifacts/humor-mechanics-batch2-semantic-edge-role-continuity-governance-v5-3.json")
    schema = load("docs/artifacts/humor-mechanics-batch2-semantic-edge-role-continuity-conformance-schema-v5-3.json")
    operational = load("docs/artifacts/humor-mechanics-batch2-order-robust-causal-spine-governance-v3.json")
    package = load(INGESTION + "source-package.json")
    envelope = load(INGESTION + "factual-authority-envelope.json")
    source = blob(INGESTION + "source.utf8.txt")
    require(receipt["receipt_identity"] == "2b2b2aeb07d7b2f36ce6c36b71e209ad255638079fc20851a2f6239ad2d46f79", "receipt")
    require(sufficiency_audit["audit_identity"] == "9fd2379f5f610433a714ffe32e11fd696cdc8708ec43971b4212a9a329a603b1", "audit")
    require(receipt["verdict"] == "PASS_SELECTED_PROPOSITION_SUFFICIENT" and receipt["selected_proposition_id"] == "P3", "selection")
    require(receipt["semantic_role_or_affordance_planning_performed"] is False and receipt["realization_or_witness_planning_performed"] is False, "planning")
    require(governance["governance_identity"] == receipt["governance_identity"] == "073d68d9d21c76974d12eb8e3f591f4172197377bfb36c2de2f85a5afe079dd6", "governance")
    require(schema["schema_identity"] == receipt["schema_identity"] == "4b26df92539082f11b83c83f76b1d158c7c8f4c87304bdcdd8a6129644f532f3", "schema")
    require(governance["constructor_contract_identity"] == schema["constructor_contract_identity"] == "9d811b18c16e8770549c19c9d8be63ef6f04e030fa67b5a47167b5e7ddc1bef6", "contract")
    selected = next(item for item in envelope["propositions"] if item["proposition_id"] == "P3")
    span = selected["supporting_span"]
    bs, be = span["utf8_byte_coordinates"]
    selected_bytes = source[bs:be]
    require(hashlib.sha256(selected_bytes).hexdigest() == receipt["selected_supporting_span_sha256"], "span")
    require(receipt["authorized_visible_context_sha256"] == hashlib.sha256(selected_bytes).hexdigest(), "context")

    visible_obligation = dict(operational["constructor_visible_obligation"])
    visible_obligation.update({
        "obligation_version": "DEVELOPMENT_TRANSFORMATION_V5_3_01",
        "typed_semantic_future_constraints": [
            "Într-o fază separată, înaintea oricărei realizări, fiecare operand și relație trebuie să primească o semnătură semantică derivată numai din propoziția selectată sau dintr-un rezultat local explicit.",
            "O reclasificare nu poate crea singură agenție, autoritate, proprietate, permisiune, capacitate ori posibilitatea unei acțiuni.",
            "Fiecare legătură, inclusiv cea terminală, trebuie să aibă compatibilitate locală și dependență contrafactuală explicită; simpla repetare lexicală nu este suficientă.",
        ],
        "creative_marking_constraints": [
            "Marcajul nonfactual trebuie ales local și firesc, fără formulă, tranziție, deschidere sau încheiere reutilizată.",
            "Nu transfera în rezultat limbajul cerințelor, planului, controlului, guvernanței sau validării.",
        ],
    })
    obligation_core = {"schema_name": "batch2-development-pilot11-label-blind-obligation-family-v5-3", "schema_version": "5.3.0",
        "family_version": "SEMANTIC_EDGE_ROLE_CONTINUITY_V5_3_NO_CONCRETE_SEMANTIC_PLAN",
        "governance_identity": governance["governance_identity"], "conformance_schema_identity": schema["schema_identity"],
        "inherited_operational_governance_identity": operational["governance_identity"],
        "sufficiency_receipt_identity": receipt["receipt_identity"], "constructor_visible_obligation": visible_obligation,
        "semantic_role_signature": None, "affordance_topology": None, "realization_plan": None, "witness_topology": None,
        "candidate_surface": None, "construction_authority": False, "constructor_release_authority": False}
    obligation_id = seal("B2_DEVELOPMENT_PILOT11_LABEL_BLIND_OBLIGATION_FAMILY_V5_3", obligation_core)
    obligation = {**obligation_core, "obligation_family_identity": obligation_id}
    revision_family = seal("B2_DEVELOPMENT_PILOT11_CONSTRUCTION_REVISION_FAMILY_V5_3",
        {"source_family": package["family_identities"]["source_family"], "obligation_family": obligation_id})
    mapping_core = {"schema_name": "batch2-development-pilot11-sealed-assignment-v5-3", "schema_version": "5.3.0",
        "admission_identity": receipt["admission_identity"], "sufficiency_receipt_identity": receipt["receipt_identity"],
        "selected_proposition_id": "P3", "selected_supporting_span_sha256": span["span_sha256"],
        "authorized_visible_context_sha256": receipt["authorized_visible_context_sha256"],
        "obligation_family_identity": obligation_id,
        "target_mapping": {"mechanism_id": "HMCV1-B02-M03-ABSURD_LOGICAL_EXTENSION",
                           "mechanism_name": "Absurd Logical Extension", "frozen_plan_option": "M13_ABSURD_LOGICAL_EXTENSION"},
        "pool_outcome": "INACCESSIBLE_NOT_EVALUATED", "partition": "DEVELOPMENT",
        "construction_revision_family_id": revision_family, "creative_marker_family_id": "UNASSIGNED_UNTIL_POSTCONSTRUCTION",
        "creative_premise_family_id": "UNASSIGNED", "semantic_role_signature": None, "affordance_topology": None,
        "realization_plan": None, "witness_topology": None, "constructor_access": False, "candidate_surface": None,
        "status": "SEALED_PROPOSAL_NOT_RELEASED"}
    mapping_id = seal("B2_DEVELOPMENT_PILOT11_SEALED_ASSIGNMENT_V5_3", mapping_core)
    mapping = {**mapping_core, "sealed_assignment_identity": mapping_id}
    instance_id = seal("B2_DEVELOPMENT_PILOT11_UNLABELED_OBLIGATION_INSTANCE_V5_3",
        {"assignment": mapping_id, "sufficiency_receipt": receipt["receipt_identity"], "proposition": "P3", "obligation_family": obligation_id})
    visible_envelope = {key: envelope[key] for key in ("authority_scope", "source_commitment", "source_sha256", "world_scope")}
    visible_envelope["propositions"] = [selected]
    packet_core = {"schema_name": "batch2-development-pilot11-constructor-facing-assignment-proposal-v5-3", "schema_version": "5.3.0",
        "source_package_identity": package["source_package_identity"], "sufficiency_receipt_identity": receipt["receipt_identity"],
        "selected_proposition_id": "P3", "selected_supporting_span_sha256": span["span_sha256"],
        "authorized_visible_context_sha256": receipt["authorized_visible_context_sha256"],
        "exact_authorized_visible_context_utf8": selected_bytes.decode(), "closed_factual_authority_envelope": visible_envelope,
        "unlabeled_operational_obligation": {"obligation_instance_identity": instance_id, **visible_obligation},
        "output_constraints": {"language": "ROMANIAN", "register": "IDIOMATIC_NATURAL_CONCRETE_ROMANIAN",
            "length_profile": "COMMON_BATCH2_NEUTRAL_PROFILE_30_TO_90_WORDS_1_TO_3_SENTENCES",
            "prohibited": ["CANNED_OPENING_OR_TRANSITION", "GOVERNANCE_OR_INSTRUCTION_META_LANGUAGE",
                "PROCEDURAL_ABSTRACT_REGISTER", "UNBOUND_REFERENCE_OR_OPERAND", "FACTUAL_WIDENING"]},
        "mapping_commitment": seal("B2_DEVELOPMENT_PILOT11_MAPPING_COMMITMENT_V5_3", mapping),
        "immutable_assignment_identity": mapping_id, "construction_revision_family_id": revision_family,
        "creative_marker_family_id": "UNASSIGNED_UNTIL_POSTCONSTRUCTION", "creative_premise_family_id": "UNASSIGNED",
        "constructor_contract_identity": governance["constructor_contract_identity"],
        "constructor_implementation_identity": "UNASSIGNED_PENDING_SEPARATE_V5_3_SOURCE_COMPATIBILITY_GATE",
        "constructor_v5_3_source_compatibility_evaluated": False, "semantic_role_signature": None,
        "affordance_topology": None, "realization_plan": None, "witness_topology": None,
        "fragment_denyset_identity": "UNASSIGNED_REQUIRES_FREEZE_BEFORE_RELEASE",
        "status": "PROPOSAL_ZERO_CONSTRUCTION_NO_RELEASE_NO_SEMANTIC_PLANNING", "constructor_invoked": False,
        "candidate_surface": None,
        "authority_matrix": {key: False for key in ("constructor_v5_3_source_compatibility_evaluation",
            "semantic_role_or_affordance_planning", "semantic_plan_evaluation", "constructor_release", "constructor_invocation",
            "realization", "candidate_emission", "semantic_edge_validation", "fragment_collision_evaluation", "g02", "g02c",
            "g03", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")}}
    packet_id = seal("B2_DEVELOPMENT_PILOT11_CONSTRUCTOR_FACING_ASSIGNMENT_PROPOSAL_V5_3", packet_core)
    packet = {**packet_core, "constructor_facing_packet_identity": packet_id}
    visible = canonical(packet)
    forbidden = [rb"HMCV1", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension",
                 rb"mechanism_id", rb"mechanism_name", rb"target_mapping", rb"pool_outcome", rb"BLIND_EVALUATION",
                 rb"close_alternative", rb"answer_key"]
    hits = [pattern.decode() for pattern in forbidden if re.search(pattern, visible, re.I)]
    require(not hits, f"visible leakage: {hits}")
    require(len(packet["closed_factual_authority_envelope"]["propositions"]) == 1, "extra proposition")
    require(packet["exact_authorized_visible_context_utf8"].encode() == selected_bytes, "context")
    require(packet["semantic_role_signature"] is packet["affordance_topology"] is None, "semantic planning")
    require(packet["realization_plan"] is packet["witness_topology"] is None, "realization planning")
    require(all(value is False for value in packet["authority_matrix"].values()), "authority")
    audit_core = {"schema_name": "batch2-development-pilot11-assignment-design-audit-v5-3", "schema_version": "5.3.0",
        "sealed_assignment_identity": mapping_id, "constructor_facing_packet_identity": packet_id,
        "obligation_family_identity": obligation_id, "obligation_instance_identity": instance_id,
        "construction_revision_family_identity": revision_family, "sufficiency_receipt_binding": "PASS_EXACT",
        "selected_proposition_binding": "PASS_EXACT_P3_ONLY", "authorized_span_binding": "PASS_EXACT",
        "extra_proposition_context": "ABSENT", "taxonomy_target_pool_and_answer_key_scan": "PASS_ZERO_HITS",
        "operational_wording_leakage": "PASS_LABEL_BLIND_CUE_MINIMIZED", "source_shape_shortcut": "PASS_NO_PACKET_SHAPE_ENCODING",
        "factual_authority_widening": "ABSENT", "creative_premise_assignment": "ABSENT_UNASSIGNED",
        "creative_marker_assignment": "ABSENT_UNASSIGNED", "semantic_role_or_affordance_planning": "NOT_PERFORMED",
        "realization_or_witness_planning": "NOT_PERFORMED", "constructor_release": "NOT_PERFORMED",
        "constructor_contract_binding": "PASS_V5_3_CONTRACT_ONLY",
        "constructor_v5_3_source_compatibility_and_semantic_plan": "NOT_EVALUATED_SEPARATE_PHASE_REQUIRED",
        "constructor_implementation": "NOT_BOUND_TO_THIS_SOURCE", "fragment_collision_evaluation": "NOT_PERFORMED",
        "constructor_invocations": 0, "candidate_surfaces_created": 0, "downstream_authority": False,
        "deterministic_blockers": [], "verdict": "PASS_SAFE_ASSIGNMENT_ZERO_CONSTRUCTION_NO_RELEASE_NO_SEMANTIC_PLANNING"}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT11_ASSIGNMENT_DESIGN_AUDIT_V5_3", audit_core)}
    write("humor-mechanics-batch2-development-pilot11-obligation-family-v5-3.json", obligation)
    write("humor-mechanics-batch2-development-pilot11-sealed-assignment-v5-3.json", mapping)
    write("humor-mechanics-batch2-development-pilot11-constructor-facing-assignment-proposal-v5-3.json", packet)
    write("humor-mechanics-batch2-development-pilot11-assignment-design-audit-v5-3.json", audit)
    print(json.dumps({"verdict": "SAFE_ASSIGNMENT_PROPOSAL_ZERO_CONSTRUCTION_NO_RELEASE_NO_SEMANTIC_PLANNING",
        "obligation_family_identity": obligation_id, "sealed_assignment_identity": mapping_id,
        "constructor_facing_packet_identity": packet_id, "obligation_instance_identity": instance_id,
        "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
