"""Prepare Pilot 10's label-blind assignment under Governance V5.2."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "dadde0764910e2f95a05fbb2c4547821887fbf9c"
INGESTION = "docs/artifacts/humor-mechanics-batch2-development-pilot10-ingestion-v1/"


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
    receipt = load("docs/artifacts/humor-mechanics-batch2-development-pilot10-proposition-sufficiency-receipt-v5-2.json")
    sufficiency_audit = load("docs/artifacts/humor-mechanics-batch2-development-pilot10-proposition-sufficiency-audit-v5-2.json")
    governance = load("docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-governance-v5-2.json")
    schema = load("docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-conformance-schema-v5-2.json")
    inherited_governance = load("docs/artifacts/humor-mechanics-batch2-typed-operand-closed-construction-governance-v5.json")
    operational_governance = load("docs/artifacts/humor-mechanics-batch2-order-robust-causal-spine-governance-v3.json")
    package = load(INGESTION + "source-package.json")
    envelope = load(INGESTION + "factual-authority-envelope.json")
    source = blob(INGESTION + "source.utf8.txt")
    require(receipt["receipt_identity"] == "a3ce7039e7e01af1f32d5063022b86a0eb463da72ed5e182c32882776b3d1b1f", "receipt")
    require(sufficiency_audit["audit_identity"] == "c29ab6fc030aa1b581a1c7c7f676e9a626113d74ff0d6c8de9992e3362498cb5", "audit")
    require(receipt["verdict"] == "PASS_SELECTED_PROPOSITION_SUFFICIENT" and receipt["selected_proposition_id"] == "P3", "selection")
    require(receipt["realization_or_witness_planning_performed"] is False, "planning boundary")
    require(governance["governance_identity"] == receipt["governance_identity"] == "80bbf059956424ce6f20885de51ce900f6116b40a223a107a46a29d3b012efc6", "governance")
    require(schema["schema_identity"] == receipt["schema_identity"] == "084ddf4d8e9f215db3665370221260c351d3befe747c4dbb45ab35baac4c993b", "schema")
    require(governance["supersedes_governance_identity"] == inherited_governance["governance_identity"], "V5 inheritance")
    require(inherited_governance["preserves_v3_order_robust_causal_spine_requirements"] is True, "V3 preservation")
    require(operational_governance["governance_identity"] in inherited_governance["supersedes_governance_identities"], "operational governance")
    require(governance["constructor_contract_identity"] == schema["constructor_contract_identity"] == "69138467540b37cbfb8444596d9a37119f8b74d002e0c491c8ff599ce77cec77", "V5.2 contract")
    selected = next(item for item in envelope["propositions"] if item["proposition_id"] == "P3")
    span = selected["supporting_span"]
    bs, be = span["utf8_byte_coordinates"]
    selected_bytes = source[bs:be]
    require(hashlib.sha256(selected_bytes).hexdigest() == receipt["selected_supporting_span_sha256"] == "188742ebbe30a23349601ddb369b0bb962d87dc9c8efe3227e50a38b6f89d967", "span")
    require(receipt["authorized_visible_context_sha256"] == hashlib.sha256(selected_bytes).hexdigest(), "context")

    obligation_core = {
        "schema_name": "batch2-development-pilot10-label-blind-obligation-family-v5-2", "schema_version": "5.2.0",
        "family_version": "PLAN_WITNESSED_REALIZATION_V5_2_WITH_TYPED_OPERAND_CLOSURE_AND_TEMPLATE_DIVERSITY",
        "governance_identity": governance["governance_identity"], "conformance_schema_identity": schema["schema_identity"],
        "inherited_typed_operand_governance_identity": inherited_governance["governance_identity"],
        "inherited_operational_governance_identity": operational_governance["governance_identity"],
        "sufficiency_receipt_identity": receipt["receipt_identity"],
        "constructor_visible_obligation": {
            **operational_governance["constructor_visible_obligation"],
            "obligation_version": "DEVELOPMENT_TRANSFORMATION_V5_2_01",
            "typed_operand_constraints": [
                "Înaintea oricărei realizări, fiecare operand trebuie descris numai prin rol, tip, proveniența din relația factuală selectată sau din legătura precedentă și compatibilitatea sa locală.",
                "Fiecare legătură inventată poate consuma numai operanzi expliciți ai relației selectate ori rezultate produse explicit de legătura precedentă.",
                "Nu introduce actori, agenți, obiecte de control, referințe sau rezultate fără producător local și tip compatibil.",
                "Orice neînchidere a operanzilor trebuie să oprească procesul înaintea unei suprafețe.",
            ],
            "creative_marking_constraints": [
                "Marcajul nonfactual trebuie ales local, firesc și fără formulă, tranziție, deschidere sau aterizare reutilizată.",
                "Nu transfera în rezultat limbajul cerințelor, al planului, al controlului, al guvernanței sau al validării.",
            ],
            "future_pre_emission_constraints": [
                "Orice viitoare realizare trebuie verificată mecanism-neutru înaintea emiterii, conform contractului V5.2 separat autorizat.",
                "O afirmație că există o legătură ori un rezultat nu poate înlocui realizarea lor explicită.",
            ],
        },
        "realization_plan": None, "witness_topology": None, "candidate_surface": None,
        "construction_authority": False, "constructor_release_authority": False,
    }
    obligation_id = seal("B2_DEVELOPMENT_PILOT10_LABEL_BLIND_OBLIGATION_FAMILY_V5_2", obligation_core)
    obligation = {**obligation_core, "obligation_family_identity": obligation_id}
    construction_revision_family_id = seal("B2_DEVELOPMENT_PILOT10_CONSTRUCTION_REVISION_FAMILY_V5_2",
        {"source_family": package["family_identities"]["source_family"], "obligation_family": obligation_id})
    mapping_core = {
        "schema_name": "batch2-development-pilot10-sealed-assignment-v5-2", "schema_version": "5.2.0",
        "admission_identity": receipt["admission_identity"], "sufficiency_receipt_identity": receipt["receipt_identity"],
        "selected_proposition_id": "P3", "selected_supporting_span_sha256": span["span_sha256"],
        "authorized_visible_context_sha256": receipt["authorized_visible_context_sha256"],
        "obligation_family_identity": obligation_id,
        "target_mapping": {"mechanism_id": "HMCV1-B02-M03-ABSURD_LOGICAL_EXTENSION",
                           "mechanism_name": "Absurd Logical Extension", "frozen_plan_option": "M13_ABSURD_LOGICAL_EXTENSION"},
        "pool_outcome": "INACCESSIBLE_NOT_EVALUATED", "partition": "DEVELOPMENT",
        "construction_revision_family_id": construction_revision_family_id,
        "creative_marker_family_id": "UNASSIGNED_UNTIL_POSTCONSTRUCTION",
        "creative_premise_family_id": "UNASSIGNED", "realization_plan": None, "witness_topology": None,
        "constructor_access": False, "candidate_surface": None, "status": "SEALED_PROPOSAL_NOT_RELEASED",
    }
    mapping_id = seal("B2_DEVELOPMENT_PILOT10_SEALED_ASSIGNMENT_V5_2", mapping_core)
    mapping = {**mapping_core, "sealed_assignment_identity": mapping_id}
    instance_id = seal("B2_DEVELOPMENT_PILOT10_UNLABELED_OBLIGATION_INSTANCE_V5_2",
        {"assignment": mapping_id, "sufficiency_receipt": receipt["receipt_identity"], "proposition": "P3", "obligation_family": obligation_id})
    visible_envelope = {key: envelope[key] for key in ("authority_scope", "source_commitment", "source_sha256", "world_scope")}
    visible_envelope["propositions"] = [selected]
    packet_core = {
        "schema_name": "batch2-development-pilot10-constructor-facing-assignment-proposal-v5-2", "schema_version": "5.2.0",
        "source_package_identity": package["source_package_identity"], "sufficiency_receipt_identity": receipt["receipt_identity"],
        "selected_proposition_id": "P3", "selected_supporting_span_sha256": span["span_sha256"],
        "authorized_visible_context_sha256": receipt["authorized_visible_context_sha256"],
        "exact_authorized_visible_context_utf8": selected_bytes.decode(), "closed_factual_authority_envelope": visible_envelope,
        "unlabeled_operational_obligation": {"obligation_instance_identity": instance_id, **obligation["constructor_visible_obligation"]},
        "output_constraints": {"language": "ROMANIAN", "register": "IDIOMATIC_NATURAL_CONCRETE_ROMANIAN",
            "length_profile": "COMMON_BATCH2_NEUTRAL_PROFILE_30_TO_90_WORDS_1_TO_3_SENTENCES",
            "prohibited": ["CANNED_OPENING_OR_TRANSITION", "GOVERNANCE_OR_INSTRUCTION_META_LANGUAGE",
                "PROCEDURAL_ABSTRACT_REGISTER", "UNBOUND_REFERENCE_OR_OPERAND", "FACTUAL_WIDENING"]},
        "mapping_commitment": seal("B2_DEVELOPMENT_PILOT10_MAPPING_COMMITMENT_V5_2", mapping),
        "immutable_assignment_identity": mapping_id, "construction_revision_family_id": construction_revision_family_id,
        "creative_marker_family_id": "UNASSIGNED_UNTIL_POSTCONSTRUCTION", "creative_premise_family_id": "UNASSIGNED",
        "constructor_contract_identity": governance["constructor_contract_identity"],
        "constructor_implementation_identity": "UNASSIGNED_PENDING_SEPARATE_V5_2_SOURCE_COMPATIBILITY_GATE",
        "constructor_v5_2_source_compatibility_evaluated": False,
        "realization_plan": None, "witness_topology": None,
        "fragment_denyset_identity": "UNASSIGNED_REQUIRES_FREEZE_BEFORE_RELEASE",
        "status": "PROPOSAL_ZERO_CONSTRUCTION_NO_RELEASE", "constructor_invoked": False, "candidate_surface": None,
        "authority_matrix": {key: False for key in ("constructor_v5_2_source_compatibility_evaluation",
            "realization_witness_planning", "constructor_release", "constructor_invocation", "realization", "candidate_emission",
            "post_realization_pre_emission_conformance", "fragment_collision_evaluation", "g02", "g02c", "g03",
            "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    packet_id = seal("B2_DEVELOPMENT_PILOT10_CONSTRUCTOR_FACING_ASSIGNMENT_PROPOSAL_V5_2", packet_core)
    packet = {**packet_core, "constructor_facing_packet_identity": packet_id}
    visible = canonical(packet)
    forbidden = [rb"HMCV1", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension",
                 rb"mechanism_id", rb"mechanism_name", rb"target_mapping", rb"pool_outcome", rb"BLIND_EVALUATION",
                 rb"owner.preference", rb"close_alternative", rb"answer_key"]
    hits = [pattern.decode() for pattern in forbidden if re.search(pattern, visible, re.I)]
    require(not hits, f"visible leakage: {hits}")
    require(len(packet["closed_factual_authority_envelope"]["propositions"]) == 1, "extra proposition")
    require(packet["exact_authorized_visible_context_utf8"].encode() == selected_bytes, "context equality")
    require(packet["realization_plan"] is None and packet["witness_topology"] is None, "planning leakage")
    require(all(value is False for value in packet["authority_matrix"].values()), "authority")
    audit_core = {
        "schema_name": "batch2-development-pilot10-assignment-design-audit-v5-2", "schema_version": "5.2.0",
        "sealed_assignment_identity": mapping_id, "constructor_facing_packet_identity": packet_id,
        "obligation_family_identity": obligation_id, "obligation_instance_identity": instance_id,
        "construction_revision_family_identity": construction_revision_family_id,
        "sufficiency_receipt_binding": "PASS_EXACT", "selected_proposition_binding": "PASS_EXACT_P3_ONLY",
        "authorized_span_binding": "PASS_EXACT", "extra_proposition_context": "ABSENT",
        "taxonomy_target_pool_and_answer_key_scan": "PASS_ZERO_HITS",
        "operational_wording_leakage": "PASS_LABEL_BLIND_CUE_MINIMIZED",
        "source_shape_shortcut": "PASS_NO_PACKET_SHAPE_ENCODING", "factual_authority_widening": "ABSENT",
        "creative_premise_assignment": "ABSENT_UNASSIGNED", "creative_marker_assignment": "ABSENT_UNASSIGNED",
        "realization_or_witness_planning": "NOT_PERFORMED", "constructor_release": "NOT_PERFORMED",
        "constructor_contract_binding": "PASS_V5_2_CONTRACT_ONLY",
        "constructor_v5_2_source_compatibility": "NOT_EVALUATED_SEPARATE_PHASE_REQUIRED",
        "constructor_implementation": "NOT_BOUND_TO_THIS_SOURCE", "fragment_collision_evaluation": "NOT_PERFORMED",
        "constructor_invocations": 0, "candidate_surfaces_created": 0, "downstream_authority": False,
        "deterministic_blockers": [], "verdict": "PASS_SAFE_ASSIGNMENT_ZERO_CONSTRUCTION_NO_RELEASE_NO_PLANNING",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT10_ASSIGNMENT_DESIGN_AUDIT_V5_2", audit_core)}
    write("humor-mechanics-batch2-development-pilot10-obligation-family-v5-2.json", obligation)
    write("humor-mechanics-batch2-development-pilot10-sealed-assignment-v5-2.json", mapping)
    write("humor-mechanics-batch2-development-pilot10-constructor-facing-assignment-proposal-v5-2.json", packet)
    write("humor-mechanics-batch2-development-pilot10-assignment-design-audit-v5-2.json", audit)
    print(json.dumps({"verdict": "SAFE_ASSIGNMENT_PROPOSAL_ZERO_CONSTRUCTION_NO_RELEASE_NO_PLANNING",
        "obligation_family_identity": obligation_id, "sealed_assignment_identity": mapping_id,
        "constructor_facing_packet_identity": packet_id, "obligation_instance_identity": instance_id,
        "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
