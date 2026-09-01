"""Prepare Pilot 13 label-blind assignment under the frozen V5.3.3 path."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "1ac17fb84cfb049ca65c2f0f6cc27361ae060d02"
INGESTION = "docs/artifacts/humor-mechanics-batch2-development-pilot13-ingestion-v1/"


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
    receipt = load("docs/artifacts/humor-mechanics-batch2-development-pilot13-proposition-sufficiency-receipt-v5-3-3.json")
    sufficiency_audit = load("docs/artifacts/humor-mechanics-batch2-development-pilot13-proposition-sufficiency-audit-v5-3-3.json")
    operational = load("docs/artifacts/humor-mechanics-batch2-order-robust-causal-spine-governance-v3.json")
    qualification = load("docs/artifacts/humor-mechanics-batch2-constructor-v5-3-3-zero-family-executable-integration-qualification.json")
    partition = load("docs/artifacts/humor-mechanics-batch2-constructor-v5-3-3-single-source-authority-partition-contract.json")
    package = load(INGESTION + "source-package.json")
    envelope = load(INGESTION + "factual-authority-envelope.json")
    source = blob(INGESTION + "source.utf8.txt")
    require(receipt["receipt_identity"] == "32f44383ebaea7ccdc779f1b3c4c94af57e717e735185ebdfa0d601ad33076f6", "receipt")
    require(sufficiency_audit["audit_identity"] == "6af2118799b171ea7343abd045d7465b750af9918b6d194a9ac70a4c0ff2dbdc", "audit")
    require(receipt["verdict"] == "PASS_SELECTED_PROPOSITION_SUFFICIENT", "verdict")
    require(receipt["selected_proposition_id"] == "P5" and receipt["eligible_propositions"] == ["P5", "P6"], "selection")
    require(receipt["selection_rule"] == "FIRST_SOURCE_ORDER_PROPOSITION_PASSING_ALL_SUFFICIENCY_REQUIREMENTS", "rule")
    require(receipt["downstream_suitability_considered"] is False, "downstream selection")
    require(qualification["qualification_identity"] == "9016f7a82cb04ba447c2c2ae4275861ef0bfbd16782c4be3584d85220f5b5c0a", "qualification")
    require(qualification["implementation_identity"] == "3c7c353d488d032dd69f9d12a07a621bfc7bb95b668e76efc08494546f5d5362", "implementation")
    require(partition["contract_identity"] == "99a6265e3dac8ab8ec3eb47456e0fc6927124636a08d5afb380c4e77042cb5b5", "partition contract")
    selected = next(item for item in envelope["propositions"] if item["proposition_id"] == "P5")
    span = selected["supporting_span"]
    bs, be = span["utf8_byte_coordinates"]
    selected_bytes = source[bs:be]
    require(hashlib.sha256(selected_bytes).hexdigest() == receipt["selected_supporting_span_sha256"] == "e1b854d2b88d4489a45f6e53ce937dff06e2e9fad3abe7258a940fb5bf4a4566", "span")
    require(receipt["authorized_visible_context_sha256"] == hashlib.sha256(selected_bytes).hexdigest(), "context")

    visible_obligation = dict(operational["constructor_visible_obligation"])
    visible_obligation.update({
        "obligation_version": "DEVELOPMENT_TRANSFORMATION_V5_3_3_01",
        "selected_source_relation": "După montare, poziția efectivă a fiecărui senzor și ora instalării sunt consemnate în jurnalul campaniei.",
        "future_phase_constraints": [
            "Orice plan viitor trebuie derivat numai din relația factuală P5 și din rezultate locale explicit produse.",
            "Fiecare relație viitoare trebuie să păstreze identitatea operanzilor și să fie necesară, ne-arbitrară și închisă referențial.",
            "Validarea semantică și a martorilor de suprafață aparține exclusiv fazelor ulterioare autorizate separat.",
        ],
        "creative_marking_constraints": [
            "Premisa și marcajul creativ rămân neatribuite până la construcție.",
            "Nu transfera în rezultat limbajul cerințelor, planului, controlului, guvernanței sau validării.",
        ],
    })
    obligation_core = {"schema_name": "batch2-development-pilot13-label-blind-obligation-family-v5-3-3",
        "schema_version": "5.3.3", "family_version": "V5_3_3_LABEL_BLIND_NO_CONCRETE_SEMANTIC_PLAN",
        "qualification_identity": qualification["qualification_identity"], "authority_partition_contract_identity": partition["contract_identity"],
        "inherited_operational_governance_identity": operational["governance_identity"],
        "sufficiency_receipt_identity": receipt["receipt_identity"], "constructor_visible_obligation": visible_obligation,
        "semantic_role_signature": None, "affordance_topology": None, "realization_plan": None, "witness_topology": None,
        "morphological_alignment_opportunity": None, "candidate_surface": None, "construction_authority": False,
        "constructor_release_authority": False}
    obligation_id = seal("B2_DEVELOPMENT_PILOT13_LABEL_BLIND_OBLIGATION_FAMILY_V5_3_3", obligation_core)
    obligation = {**obligation_core, "obligation_family_identity": obligation_id}
    revision_family = seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTION_REVISION_FAMILY_V5_3_3", {"source_family": package["family_identities"]["source_family"], "obligation_family": obligation_id})
    mapping_core = {"schema_name": "batch2-development-pilot13-sealed-assignment-v5-3-3", "schema_version": "5.3.3",
        "admission_identity": receipt["admission_identity"], "sufficiency_receipt_identity": receipt["receipt_identity"],
        "selected_proposition_id": "P5", "selected_supporting_span_sha256": span["span_sha256"],
        "authorized_visible_context_sha256": receipt["authorized_visible_context_sha256"],
        "obligation_family_identity": obligation_id,
        "target_mapping": {"mechanism_id": "HMCV1-B02-M03-ABSURD_LOGICAL_EXTENSION", "mechanism_name": "Absurd Logical Extension", "frozen_plan_option": "M13_ABSURD_LOGICAL_EXTENSION"},
        "eligible_but_unselected_propositions": ["P6"], "fallback_authority": "NONE", "pool_outcome": "INACCESSIBLE_NOT_EVALUATED",
        "partition": "DEVELOPMENT", "construction_revision_family_id": revision_family,
        "creative_marker_family_id": "UNASSIGNED_UNTIL_POSTCONSTRUCTION", "creative_premise_family_id": "UNASSIGNED",
        "semantic_role_signature": None, "affordance_topology": None, "realization_plan": None, "witness_topology": None,
        "morphological_alignment_opportunity": None, "constructor_access": False, "candidate_surface": None,
        "status": "SEALED_PROPOSAL_NOT_RELEASED"}
    mapping_id = seal("B2_DEVELOPMENT_PILOT13_SEALED_ASSIGNMENT_V5_3_3", mapping_core)
    mapping = {**mapping_core, "sealed_assignment_identity": mapping_id}
    instance_id = seal("B2_DEVELOPMENT_PILOT13_UNLABELED_OBLIGATION_INSTANCE_V5_3_3", {"assignment": mapping_id, "sufficiency_receipt": receipt["receipt_identity"], "proposition": "P5", "obligation_family": obligation_id})
    visible_envelope = {key: envelope[key] for key in ("authority_scope", "source_commitment", "source_sha256", "world_scope")}
    visible_envelope["propositions"] = [selected]
    authority_names = ("constructor_compatibility", "semantic_role_or_affordance_planning", "semantic_plan", "constructor_release",
                       "constructor_invocation", "provider_invocation", "emitter_invocation", "realization", "candidate_emission",
                       "semantic_conformance", "fragment_collision", "g02", "g02c", "g03", "g03b", "g03c",
                       "romanian_naturalness", "voice", "owner_review", "g04b", "model_exposure", "training",
                       "runtime_integration", "production_routing")
    packet_core = {"schema_name": "batch2-development-pilot13-constructor-facing-assignment-proposal-v5-3-3",
        "schema_version": "5.3.3", "pilot_role": "LEGITIMATE_END_TO_END_MECHANISM_TRIAL",
        "source_package_identity": package["source_package_identity"], "sufficiency_receipt_identity": receipt["receipt_identity"],
        "selected_proposition_id": "P5", "selected_supporting_span_sha256": span["span_sha256"],
        "authorized_visible_context_sha256": receipt["authorized_visible_context_sha256"],
        "exact_authorized_visible_context_utf8": selected_bytes.decode(), "closed_factual_authority_envelope": visible_envelope,
        "unlabeled_operational_obligation": {"obligation_instance_identity": instance_id, **visible_obligation},
        "mapping_commitment": seal("B2_DEVELOPMENT_PILOT13_MAPPING_COMMITMENT_V5_3_3", mapping),
        "immutable_assignment_identity": mapping_id, "construction_revision_family_id": revision_family,
        "creative_marker_family_id": "UNASSIGNED_UNTIL_POSTCONSTRUCTION", "creative_premise_family_id": "UNASSIGNED",
        "qualified_executable_implementation_identity": qualification["implementation_identity"],
        "provider_identity": qualification["provider_identity"], "emitter_identity": qualification["emitter_identity"],
        "authority_partition_contract_identity": partition["contract_identity"],
        "constructor_compatibility_evaluated": False, "semantic_role_signature": None, "affordance_topology": None,
        "realization_plan": None, "witness_topology": None, "morphological_alignment_opportunity": None,
        "fragment_denyset_identity": "UNASSIGNED_REQUIRES_FREEZE_BEFORE_RELEASE",
        "unselected_proposition_or_fallback_authority": "ABSENT", "status": "PROPOSAL_ZERO_CONSTRUCTION_NO_RELEASE_NO_SEMANTIC_PLANNING",
        "constructor_invoked": False, "candidate_surface": None, "authority_matrix": {key: False for key in authority_names}}
    packet_id = seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTOR_FACING_ASSIGNMENT_PROPOSAL_V5_3_3", packet_core)
    packet = {**packet_core, "constructor_facing_packet_identity": packet_id}
    visible = canonical(packet)
    forbidden = [rb"HMCV1", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"Absurd Logical Extension", rb"mechanism_id",
                 rb"mechanism_name", rb"target_mapping", rb"pool_outcome", rb"answer_key", rb'"proposition_id":"P6"']
    hits = [pattern.decode() for pattern in forbidden if re.search(pattern, visible, re.I)]
    require(not hits, f"visible leakage: {hits}")
    require(len(packet["closed_factual_authority_envelope"]["propositions"]) == 1, "extra proposition")
    require(packet["exact_authorized_visible_context_utf8"].encode() == selected_bytes, "context")
    require(packet["semantic_role_signature"] is packet["affordance_topology"] is None, "semantic planning")
    require(packet["realization_plan"] is packet["witness_topology"] is packet["morphological_alignment_opportunity"] is None, "realization planning")
    require(all(value is False for value in packet["authority_matrix"].values()), "authority")
    audit_core = {"schema_name": "batch2-development-pilot13-assignment-design-audit-v5-3-3", "schema_version": "5.3.3",
        "sealed_assignment_identity": mapping_id, "constructor_facing_packet_identity": packet_id,
        "obligation_family_identity": obligation_id, "obligation_instance_identity": instance_id,
        "construction_revision_family_identity": revision_family, "sufficiency_receipt_binding": "PASS_EXACT",
        "selected_proposition_binding": "PASS_EXACT_P5_ONLY", "authorized_span_binding": "PASS_EXACT",
        "p6_fallback_or_comparative_authority": "ABSENT", "extra_proposition_context": "ABSENT",
        "taxonomy_target_pool_answer_key_and_p6_scan": "PASS_ZERO_HITS", "operational_wording_leakage": "PASS_LABEL_BLIND",
        "source_shape_shortcut": "PASS_NO_PACKET_SHAPE_ENCODING", "factual_authority_widening": "ABSENT",
        "semantic_role_or_affordance_planning": "NOT_PERFORMED", "realization_witness_or_morphological_alignment_planning": "NOT_PERFORMED",
        "constructor_compatibility_and_semantic_plan": "NOT_EVALUATED_SEPARATE_PHASE_REQUIRED", "constructor_release": "NOT_PERFORMED",
        "constructor_invocations": 0, "provider_invocations": 0, "emitter_invocations": 0, "candidate_surfaces_created": 0,
        "downstream_authority": False, "deterministic_blockers": [],
        "verdict": "PASS_SAFE_ASSIGNMENT_ZERO_CONSTRUCTION_NO_RELEASE_NO_SEMANTIC_PLANNING"}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT13_ASSIGNMENT_DESIGN_AUDIT_V5_3_3", audit_core)}
    write("humor-mechanics-batch2-development-pilot13-obligation-family-v5-3-3.json", obligation)
    write("humor-mechanics-batch2-development-pilot13-sealed-assignment-v5-3-3.json", mapping)
    write("humor-mechanics-batch2-development-pilot13-constructor-facing-assignment-proposal-v5-3-3.json", packet)
    write("humor-mechanics-batch2-development-pilot13-assignment-design-audit-v5-3-3.json", audit)
    print(json.dumps({"verdict": "SAFE_ASSIGNMENT_PROPOSAL_ZERO_CONSTRUCTION_NO_RELEASE_NO_SEMANTIC_PLANNING",
                      "obligation_family_identity": obligation_id, "obligation_instance_identity": instance_id,
                      "sealed_assignment_identity": mapping_id, "constructor_facing_packet_identity": packet_id,
                      "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
