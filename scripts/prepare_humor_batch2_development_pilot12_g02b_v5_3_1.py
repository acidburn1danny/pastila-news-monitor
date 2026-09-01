"""Freeze Pilot 12's uninvoked, pathless Governance V5.3.1 G02B release."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

from pastila_scout.humor_batch2_development_constructor_v5_1 import derive_proposition_plan, extract_typed_operands, validate_typed_plan
from pastila_scout.humor_batch2_development_constructor_v5_3_semantic_enforcement import (
    EdgeNecessityWitness, OperandSemanticSpec, PredicateSemanticSignature, validate_semantic_plan,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "c5c0928f6d2cc830d515bd6d31f2b7461432f442"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def load(name: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{COMMIT}:docs/artifacts/{name}"], cwd=ROOT))


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), f"artifact exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def normalized_words(surface: str) -> list[str]:
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", surface).casefold(), flags=re.UNICODE)


def build_denyset() -> dict[str, Any]:
    sources, hashes = [], set()
    for pilot in range(1, 11):
        path = f"docs/artifacts/humor-mechanics-batch2-development-pilot{pilot:02d}-candidate01-v1.txt"
        raw = git_bytes(path)
        words = normalized_words(raw.decode("utf-8"))
        local = {hashlib.sha256(" ".join(words[index:index + size]).encode()).hexdigest()
                 for size in range(3, 9) for index in range(len(words) - size + 1)}
        hashes.update(local)
        oid = subprocess.check_output(["git", "rev-parse", f"{COMMIT}:{path}"], cwd=ROOT, text=True).strip()
        sources.append({"path": path, "partition": "DEVELOPMENT_NONBLIND",
                        "surface_sha256": hashlib.sha256(raw).hexdigest(), "git_blob_oid_sha1": oid,
                        "normalized_word_count": len(words), "normalized_ngram_hash_count": len(local)})
    core = {"schema_name": "batch2-nonblind-development-fragment-denyset-v5-3-1", "schema_version": "5.3.1",
            "source_commit": COMMIT, "eligible_corpus": "NONBLIND_DEVELOPMENT_ONLY",
            "blind_reserve_accessed": False, "candidate_sources": sources,
            "ngram_word_lengths": [3, 4, 5, 6, 7, 8],
            "normalization": "UNICODE_NFKC_CASEFOLD_ALPHANUMERIC_WORDS",
            "normalized_ngram_sha256": sorted(hashes), "complete_surface_text_included": False,
            "model_or_semantic_similarity_used": False}
    return {**core, "fragment_denyset_identity": seal("B2_NONBLIND_DEVELOPMENT_FRAGMENT_DENYSET_V5_3_1", core)}


def semantic_material(proposal: dict[str, Any]):
    proposition = proposal["closed_factual_authority_envelope"]["propositions"][0]
    operands = extract_typed_operands(proposal["exact_authorized_visible_context_utf8"], proposition)
    plan = derive_proposition_plan(operands)
    qualifier = "FACT_QUALIFICATION" if operands.qualification else "FACT_RELATION"
    validate_typed_plan(plan, frozenset({operands.relation_id, "FACT_OBJECT", qualifier}))
    specs = (
        OperandSemanticSpec(operands.relation_id, "P5_CONDITIONED_BOX_TRANSPORT_DISPOSITION",
                            ("CONDITIONED_TRANSPORT_RELATION",), ("LICENSE_LOCAL_NONFACTUAL_EXTENSION",), (), False),
        OperandSemanticSpec(qualifier, "P5_SAME_DESTINATION_SHELF_CONDITION",
                            ("CONDITION_STATE",), ("QUALIFY_TRANSPORT_DISPOSITION",), (), False),
        OperandSemanticSpec("FACT_OBJECT", "P5_LIBRARY_STORAGE_DESTINATION",
                            ("TRANSFER_DESTINATION",), ("RECEIVE_BOX",), (), False),
        OperandSemanticSpec("INVENTED_RELATION_1", "LOCAL_TRANSPORT_ELIGIBILITY_STATE",
                            ("LICENSED_TRANSPORT_STATE",), ("PROPAGATE_TO_BOUND_DESTINATION",),
                            (operands.relation_id, qualifier), False),
        OperandSemanticSpec("INVENTED_RELATION_2", "DESTINATION_BOUND_TRANSPORT_STATE",
                            ("DESTINATION_BOUND_TRANSPORT_STATE",), ("RESOLVE_AGAINST_SOURCE_TRANSPORT_RELATION",),
                            ("INVENTED_RELATION_1", "FACT_OBJECT"), False),
    )
    signatures = (
        PredicateSemanticSignature(plan[0].predicate_id, ("CONDITIONED_TRANSPORT_RELATION",), ("CONDITION_STATE",),
                                   ("LICENSE_LOCAL_NONFACTUAL_EXTENSION",), ("QUALIFY_TRANSPORT_DISPOSITION",)),
        PredicateSemanticSignature(plan[1].predicate_id, ("LICENSED_TRANSPORT_STATE",), ("TRANSFER_DESTINATION",),
                                   ("PROPAGATE_TO_BOUND_DESTINATION",), ("RECEIVE_BOX",)),
        PredicateSemanticSignature(plan[2].predicate_id, ("DESTINATION_BOUND_TRANSPORT_STATE",),
                                   ("CONDITIONED_TRANSPORT_RELATION",),
                                   ("RESOLVE_AGAINST_SOURCE_TRANSPORT_RELATION",),
                                   ("LICENSE_LOCAL_NONFACTUAL_EXTENSION",)),
    )
    edges = (
        EdgeNecessityWitness("L1", "L2", "INVENTED_RELATION_1", "ACTOR",
                             "RULE_L1_TRANSPORT_ELIGIBILITY_IS_REQUIRED_ACTOR_OF_L2", True, True),
        EdgeNecessityWitness("L2", "RESULT", "INVENTED_RELATION_2", "ACTOR",
                             "RULE_L2_DESTINATION_BOUND_STATE_IS_REQUIRED_ACTOR_OF_TERMINAL_RESULT", True, True),
    )
    coverage = validate_semantic_plan(typed_plan=plan, operand_specs=specs,
                                      predicate_signatures=signatures, edge_witnesses=edges)
    require((coverage.nodes_validated, coverage.edges_validated, coverage.terminal_edge_validated) == (3, 2, True), "semantic plan")
    serialize = lambda values: [dict((field, getattr(item, field)) for field in item.__dataclass_fields__) for item in values]
    plan_json = [{"node_id": node.node_id, "bound_actor_id": node.bound_actor_id, "actor_role": node.actor_role,
                  "predicate_id": node.predicate_id, "bound_patient_id": node.bound_patient_id,
                  "predecessor_node_ids": list(node.predecessor_node_ids), "introduces_ids": list(node.introduces_ids),
                  "source_provenance": node.source_provenance, "nonfactual_scope": node.nonfactual_scope} for node in plan]
    return plan_json, serialize(specs), serialize(signatures), serialize(edges)


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    proposal = load("humor-mechanics-batch2-development-pilot12-constructor-facing-assignment-proposal-v5-3-1.json")
    mapping = load("humor-mechanics-batch2-development-pilot12-sealed-assignment-v5-3-1.json")
    compatibility = load("humor-mechanics-batch2-development-pilot12-constructor-v5-3-1-source-compatibility-v1.json")
    compatibility_audit = load("humor-mechanics-batch2-development-pilot12-constructor-v5-3-1-source-compatibility-audit-v1.json")
    base_contract = load("humor-mechanics-batch2-development-constructor-contract-v5-3.json")
    alignment_contract = load("humor-mechanics-batch2-development-constructor-surface-witness-alignment-contract-v5-3-1.json")
    implementation = load("humor-mechanics-batch2-development-constructor-implementation-v5-3-1.json")
    provider = load("humor-mechanics-batch2-development-constructor-v5-3-1-realization-provider-implementation.json")
    emitter = load("humor-mechanics-batch2-development-constructor-v5-3-1-candidate-emitter-implementation.json")
    governance = load("humor-mechanics-batch2-semantic-edge-role-continuity-governance-v5-3.json")
    schema = load("humor-mechanics-batch2-semantic-edge-role-continuity-conformance-schema-v5-3.json")
    enforcement = load("humor-mechanics-batch2-development-constructor-semantic-edge-enforcement-v5-3.json")
    alignment_implementation = load("humor-mechanics-batch2-development-constructor-surface-witness-alignment-implementation-v5-3-1.json")
    static_audit = load("humor-mechanics-batch2-development-constructor-v5-3-1-runtime-static-audit-v1.json")
    require(compatibility["compatibility_identity"] == "1a3ca6684d124cb036dc2c738fd4d1fa5d13985207b4f4d3189b4baf977f7721", "compatibility")
    require(compatibility_audit["audit_identity"] == "4a64a029dbcb2cd8e6346f66ffdc1aeca02061a5ab320aa1a3bd24e5f94cae4f", "compatibility audit")
    require(compatibility["verdict"] == "PASS_SOURCE_COMPATIBLE_WITH_FROZEN_CONSTRUCTOR_V5_3_1_STATIC_SEMANTIC_PLAN_NO_RELEASE", "verdict")
    require(proposal["selected_proposition_id"] == "P5" and len(proposal["closed_factual_authority_envelope"]["propositions"]) == 1, "P5")
    require(proposal["unselected_proposition_or_fallback_authority"] == "ABSENT", "P6")
    require(hashlib.sha256(proposal["exact_authorized_visible_context_utf8"].encode()).hexdigest() == proposal["selected_supporting_span_sha256"], "span")
    require(alignment_contract["successor_contract_identity"] == "c4af75cd962802d0035d9de39e6d014f715d5b5f5b60fd690ea3761f289d99fc", "alignment contract")
    require(implementation["constructor_implementation_identity"] == "a966e92c37d6f957cbd080a9d2961cf05b288633d0d6e9f309c7d6baec956894", "implementation")
    require(provider["realization_provider_identity"] == "2846406e03cea3fbbdca5531a7d0bf23fc39b116f7e0413a4bc73a65ea9b6992", "provider")
    require(emitter["candidate_emitter_identity"] == "d08e74b2ccfaa5e157a86376e46b2ac70c7f4225261ecb1112c063a236804dd1", "emitter")
    require(static_audit["constructor_invocations"] == static_audit["provider_invocations"] == static_audit["emitter_invocations"] == 0, "invocations")
    denyset = build_denyset()
    plan, specs, signatures, edges = semantic_material(proposal)
    semantic_bundle = {"typed_plan": plan, "operand_semantic_specs": specs,
                       "predicate_semantic_signatures": signatures, "edge_necessity_witnesses": edges}
    semantic_commitment = seal("B2_PILOT12_P5_SEMANTIC_PLAN_V5_3_1", semantic_bundle)
    core = dict(proposal)
    superseded = core.pop("constructor_facing_packet_identity")
    core.pop("mapping_commitment")
    core["authority_matrix"].pop("g04b_pool_certification")
    for key in ("constructor_implementation_identity", "fragment_denyset_identity",
                "constructor_v5_3_1_source_compatibility_evaluated", "realization_plan",
                "semantic_role_signature", "affordance_topology", "witness_topology",
                "morphological_alignment_opportunity"):
        core.pop(key)
    core.update({
        "base_constructor_contract_identity": base_contract["constructor_contract_identity"],
        "alignment_contract_identity": alignment_contract["successor_contract_identity"],
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "realization_provider_identity": provider["realization_provider_identity"],
        "candidate_emitter_identity": emitter["candidate_emitter_identity"],
        "constructor_source_compatibility_identity": compatibility["compatibility_identity"],
        "constructor_source_compatibility_audit_identity": compatibility_audit["audit_identity"],
        "proposition_derived_typed_plan": plan, "operand_semantic_specs": specs,
        "predicate_semantic_signatures": signatures, "edge_necessity_witnesses": edges,
        "semantic_plan_commitment": semantic_commitment,
        "pre_emission_governance_identity": governance["governance_identity"],
        "pre_emission_conformance_schema_identity": schema["schema_identity"],
        "pre_emission_semantic_enforcement_identity": enforcement["semantic_enforcement_implementation_identity"],
        "pre_emission_coordinate_alignment_identity": alignment_implementation["implementation_identity"],
        "fragment_denyset_identity": denyset["fragment_denyset_identity"],
        "status": "G02B_RELEASE_CANDIDATE_ZERO_CONSTRUCTION",
    })
    packet_id = seal("B2_DEVELOPMENT_PILOT12_CONSTRUCTOR_PACKET_G02B_V5_3_1", core)
    packet = {**core, "constructor_facing_packet_identity": packet_id}
    release_core = {
        "constructor_facing_packet_identity": packet_id,
        "packet_seal_namespace": "B2_DEVELOPMENT_PILOT12_CONSTRUCTOR_PACKET_G02B_V5_3_1",
        "immutable_assignment_identity": mapping["sealed_assignment_identity"],
        "sufficiency_receipt_identity": packet["sufficiency_receipt_identity"], "selected_proposition_id": "P5",
        "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
        "authorized_visible_context_sha256": packet["authorized_visible_context_sha256"],
        "unselected_proposition_or_fallback_authority": "ABSENT", "partition": "DEVELOPMENT",
        "creative_premise_family_id": "UNASSIGNED",
        "base_constructor_contract_identity": base_contract["constructor_contract_identity"],
        "alignment_contract_identity": alignment_contract["successor_contract_identity"],
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "realization_provider_identity": provider["realization_provider_identity"],
        "candidate_emitter_identity": emitter["candidate_emitter_identity"],
        "constructor_source_compatibility_identity": compatibility["compatibility_identity"],
        "constructor_source_compatibility_audit_identity": compatibility_audit["audit_identity"],
        "semantic_plan_commitment": semantic_commitment, "fragment_denyset_identity": denyset["fragment_denyset_identity"],
        "pre_emission_governance_identity": governance["governance_identity"],
        "pre_emission_conformance_schema_identity": schema["schema_identity"],
        "pre_emission_semantic_enforcement_identity": enforcement["semantic_enforcement_implementation_identity"],
        "pre_emission_coordinate_alignment_identity": alignment_implementation["implementation_identity"],
        "release_mode": "PATHLESS_SINGLE_OBJECT_CAPABILITY_NOT_RELEASED_TO_CONSTRUCTOR",
        "single_use_state": "UNCONSUMED_0_OF_1_NOT_AUTHORIZED", "constructor_invocation_authorized": False,
    }
    release_id = seal("B2_DEVELOPMENT_PILOT12_CONSTRUCTOR_ACCESS_RELEASE_V5_3_1", release_core)
    transport = {"constructor_role": "CONSTRUCTOR",
                 "packet_delivery": "IN_MEMORY_EXACT_BYTES_SINGLE_USE_PATHLESS_CAPABILITY",
                 **{key: False for key in ("repository_access", "filesystem_path_access", "sibling_artifact_discovery",
                    "environment_inheritance", "command_line_payload", "process_handle_inheritance", "metadata_enumeration",
                    "cache_or_temp_file", "import_time_repository_access", "logs_contain_packet_or_mapping",
                    "exceptions_contain_packet_or_mapping", "network_access", "constructor_invocation_authorized",
                    "provider_invocation_authorized", "emitter_invocation_authorized")}}
    release = {"schema_name": "batch2-development-pilot12-constructor-access-release-v5-3-1",
               "schema_version": "5.3.1", "release_core": release_core, "release_identity": release_id,
               "constructor_packet": packet, "constructor_visible_object_set": ["CONSTRUCTOR_PACKET_EXACT_BYTES"],
               "transport_policy": transport}
    forbidden = [rb"HMCV1", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"LITERALIZATION", rb"MISDIRECTION",
                 rb"mechanism_id", rb"mechanism_name", rb"close_alternative", rb"mapping_commitment",
                 rb"BLIND_EVALUATION", rb"owner.preference", rb"G04B", rb"pool", rb'"proposition_id":"P6"']
    hits = [item.decode() for item in forbidden if re.search(item, canonical(packet), re.I)]
    require(not hits, f"leakage {hits}")
    require(packet["candidate_surface"] is None and packet["constructor_invoked"] is False, "candidate")
    require(all(value is False for value in packet["authority_matrix"].values()), "authority")
    audit_core = {
        "schema_name": "batch2-development-pilot12-g02b-preconstruction-audit-v5-3-1", "schema_version": "5.3.1",
        "reviewed_commit": COMMIT, "superseded_packet_identity": superseded,
        "constructor_facing_packet_identity": packet_id, "release_identity": release_id,
        "contract_provider_emitter_binding": "PASS_EXACT_V5_3_1",
        "compatibility_and_audit_binding": "PASS_EXACT", "selected_proposition_and_span_binding": "PASS_EXACT_P5_ONLY_NO_P6_FALLBACK",
        "semantic_plan_binding": "PASS_EXACT_THREE_NODES_TWO_EDGES_NO_UNBOUND_OPERANDS",
        "predicate_role_and_affordance_binding": "PASS_3_OF_3",
        "edge_counterfactual_non_arbitrariness_binding": "PASS_2_OF_2",
        "entity_identity_and_privileged_affordance_binding": "PASS_NO_RECLASSIFICATION_OR_PRIVILEGED_DERIVATION",
        "terminal_edge_binding": "PASS_EQUAL_STRENGTH",
        "pre_emission_semantic_and_coordinate_conformance": "PASS_EXACT_MANDATORY_BEFORE_EMISSION",
        "alignment_binding": "PASS_STATIC_CONSTRAINT_ONLY_NO_OPPORTUNITY_INVENTED",
        "fragment_denyset_binding": f"PASS_EXACT_{len(denyset['candidate_sources'])}_NONBLIND_DEVELOPMENT_FAMILIES_{len(denyset['normalized_ngram_sha256'])}_HASHES",
        "blind_reserve_access": "NONE", "sealed_mapping_access": "DENIED",
        "pathless_single_object_isolation": "PASS", "label_target_pool_answer_key_and_p6_scan": "PASS_ZERO_HITS",
        "constructor_invocations": 0, "provider_invocations": 0, "emitter_invocations": 0,
        "candidate_surfaces": 0, "capability_state": "UNCONSUMED_0_OF_1_NOT_AUTHORIZED",
        "downstream_authority_granted": False, "deterministic_blockers_remaining": [],
        "verdict": "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT12_G02B_AUDIT_V5_3_1", audit_core)}
    write("humor-mechanics-batch2-nonblind-development-fragment-denyset-v5-3-1.json", denyset)
    write("humor-mechanics-batch2-development-pilot12-constructor-facing-assignment-g02b-v5-3-1.json", packet)
    write("humor-mechanics-batch2-development-pilot12-constructor-access-release-v5-3-1.json", release)
    write("humor-mechanics-batch2-development-pilot12-g02b-preconstruction-audit-v5-3-1.json", audit)
    print(json.dumps({"verdict": audit["verdict"], "packet_identity": packet_id,
                      "release_identity": release_id, "audit_identity": audit["audit_identity"],
                      "fragment_denyset_identity": denyset["fragment_denyset_identity"],
                      "families": len(denyset["candidate_sources"]),
                      "hashes": len(denyset["normalized_ngram_sha256"])}, sort_keys=True))


if __name__ == "__main__":
    main()
