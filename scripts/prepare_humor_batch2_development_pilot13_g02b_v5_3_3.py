"""Freeze Pilot 13's uninvoked, pathless V5.3.3 G02B release."""

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
from pastila_scout.humor_batch2_development_constructor_v5_3_3_integration import CLASS_C_FIELDS

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "beb4e3fa609a308f4bc9496c9c7c12eef05210ca"


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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


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
        sources.append({"path": path, "partition": "DEVELOPMENT_NONBLIND", "surface_sha256": hashlib.sha256(raw).hexdigest(),
                        "git_blob_oid_sha1": oid, "normalized_word_count": len(words), "normalized_ngram_hash_count": len(local)})
    core = {"schema_name": "batch2-nonblind-development-fragment-denyset-v5-3-3", "schema_version": "5.3.3",
            "source_commit": COMMIT, "eligible_corpus": "NONBLIND_DEVELOPMENT_ONLY", "blind_reserve_accessed": False,
            "candidate_sources": sources, "ngram_word_lengths": [3, 4, 5, 6, 7, 8],
            "normalization": "UNICODE_NFKC_CASEFOLD_ALPHANUMERIC_WORDS", "normalized_ngram_sha256": sorted(hashes),
            "complete_surface_text_included": False, "model_or_semantic_similarity_used": False}
    return {**core, "fragment_denyset_identity": seal("B2_NONBLIND_DEVELOPMENT_FRAGMENT_DENYSET_V5_3_3", core)}


def semantic_material(proposal: dict[str, Any]):
    proposition = proposal["closed_factual_authority_envelope"]["propositions"][0]
    operands = extract_typed_operands(proposal["exact_authorized_visible_context_utf8"], proposition)
    plan = derive_proposition_plan(operands)
    qualifier = "FACT_QUALIFICATION" if operands.qualification else "FACT_RELATION"
    validate_typed_plan(plan, frozenset({operands.relation_id, "FACT_OBJECT", qualifier}))
    specs = (
        OperandSemanticSpec(operands.relation_id, "P5_POST_INSTALLATION_POSITION_AND_TIME_RECORDING_RELATION",
                            ("POST_INSTALLATION_RECORDING_RELATION",), ("LICENSE_LOCAL_NONFACTUAL_EXTENSION",), (), False),
        OperandSemanticSpec(qualifier, "P5_POST_INSTALLATION_TEMPORAL_CONDITION",
                            ("TEMPORAL_PRECONDITION",), ("QUALIFY_RECORDING_DISPOSITION",), (), False),
        OperandSemanticSpec("FACT_OBJECT", "P5_CAMPAIGN_LOG_DESTINATION",
                            ("RECORD_DESTINATION",), ("RECEIVE_POSITION_AND_TIME_RECORD",), (), False),
        OperandSemanticSpec("INVENTED_RELATION_1", "LOCAL_POST_INSTALLATION_RECORD_ELIGIBILITY_STATE",
                            ("LICENSED_RECORDING_STATE",), ("PROPAGATE_TO_BOUND_LOG",),
                            (operands.relation_id, qualifier), False),
        OperandSemanticSpec("INVENTED_RELATION_2", "LOG_BOUND_RECORD_STATE", ("LOG_BOUND_RECORD_STATE",),
                            ("RESOLVE_AGAINST_SOURCE_RECORDING_RELATION",), ("INVENTED_RELATION_1", "FACT_OBJECT"), False),
    )
    signatures = (
        PredicateSemanticSignature(plan[0].predicate_id, ("POST_INSTALLATION_RECORDING_RELATION",), ("TEMPORAL_PRECONDITION",),
                                   ("LICENSE_LOCAL_NONFACTUAL_EXTENSION",), ("QUALIFY_RECORDING_DISPOSITION",)),
        PredicateSemanticSignature(plan[1].predicate_id, ("LICENSED_RECORDING_STATE",), ("RECORD_DESTINATION",),
                                   ("PROPAGATE_TO_BOUND_LOG",), ("RECEIVE_POSITION_AND_TIME_RECORD",)),
        PredicateSemanticSignature(plan[2].predicate_id, ("LOG_BOUND_RECORD_STATE",), ("POST_INSTALLATION_RECORDING_RELATION",),
                                   ("RESOLVE_AGAINST_SOURCE_RECORDING_RELATION",), ("LICENSE_LOCAL_NONFACTUAL_EXTENSION",)),
    )
    edges = (
        EdgeNecessityWitness("L1", "L2", "INVENTED_RELATION_1", "ACTOR", "RULE_L1_RECORD_ELIGIBILITY_IS_REQUIRED_ACTOR_OF_L2", True, True),
        EdgeNecessityWitness("L2", "RESULT", "INVENTED_RELATION_2", "ACTOR", "RULE_L2_LOG_BOUND_STATE_IS_REQUIRED_ACTOR_OF_TERMINAL_RESULT", True, True),
    )
    coverage = validate_semantic_plan(typed_plan=plan, operand_specs=specs, predicate_signatures=signatures, edge_witnesses=edges)
    require((coverage.nodes_validated, coverage.edges_validated, coverage.terminal_edge_validated) == (3, 2, True), "semantic plan")
    serialize = lambda values: [dict((field, getattr(item, field)) for field in item.__dataclass_fields__) for item in values]
    plan_json = [{"node_id": node.node_id, "bound_actor_id": node.bound_actor_id, "actor_role": node.actor_role,
                  "predicate_id": node.predicate_id, "bound_patient_id": node.bound_patient_id,
                  "predecessor_node_ids": list(node.predecessor_node_ids), "introduces_ids": list(node.introduces_ids),
                  "source_provenance": node.source_provenance, "nonfactual_scope": node.nonfactual_scope} for node in plan]
    return plan_json, serialize(specs), serialize(signatures), serialize(edges)


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    proposal = load("humor-mechanics-batch2-development-pilot13-constructor-facing-assignment-proposal-v5-3-3.json")
    mapping = load("humor-mechanics-batch2-development-pilot13-sealed-assignment-v5-3-3.json")
    compatibility = load("humor-mechanics-batch2-development-pilot13-constructor-v5-3-3-source-compatibility-v1.json")
    compatibility_audit = load("humor-mechanics-batch2-development-pilot13-constructor-v5-3-3-source-compatibility-audit-v1.json")
    qualification = load("humor-mechanics-batch2-constructor-v5-3-3-zero-family-executable-integration-qualification.json")
    partition = load("humor-mechanics-batch2-constructor-v5-3-3-single-source-authority-partition-contract.json")
    require(compatibility["compatibility_identity"] == "b8f0b874ce629de2c1e1d2f5b8744b4425178219de57e7f22631baecb54a01c0", "compatibility")
    require(compatibility_audit["audit_identity"] == "1b1a0ce66e183558343bebce6d37dee253106be2a06e3f447f1def343d4422e2", "compatibility audit")
    require(compatibility["verdict"] == "PASS_SOURCE_COMPATIBLE_WITH_FROZEN_CONSTRUCTOR_V5_3_3_STATIC_SEMANTIC_PLAN_NO_RELEASE", "verdict")
    require(compatibility["post_qualification_deterministic_infrastructure_defect"] == "NONE_DISCOVERED", "infrastructure defect")
    require(proposal["selected_proposition_id"] == "P5" and len(proposal["closed_factual_authority_envelope"]["propositions"]) == 1, "P5")
    require(proposal["unselected_proposition_or_fallback_authority"] == "ABSENT", "P6")
    require(hashlib.sha256(proposal["exact_authorized_visible_context_utf8"].encode()).hexdigest() == proposal["selected_supporting_span_sha256"], "span")
    require(qualification["qualification_identity"] == "9016f7a82cb04ba447c2c2ae4275861ef0bfbd16782c4be3584d85220f5b5c0a", "qualification")
    require(qualification["implementation_identity"] == compatibility["constructor_implementation_identity"] == "3c7c353d488d032dd69f9d12a07a621bfc7bb95b668e76efc08494546f5d5362", "implementation")
    require(qualification["provider_identity"] == compatibility["provider_identity"] == "865c1e9f7cedb5e78b5ecd7524781a8ed8a50816a9be76910c7ee76c375b81ea", "provider")
    require(qualification["emitter_identity"] == compatibility["emitter_identity"] == "5bb1fae007fb8898f7e1a514622bb9bac99d992cc81189cd4ffd33b60fa76a8b", "emitter")
    require(CLASS_C_FIELDS == frozenset({"clause"}) and compatibility["class_b_state"] == "NOT_CREATED_PRE_REALIZATION", "authority partition")
    denyset = build_denyset()
    plan, specs, signatures, edges = semantic_material(proposal)
    semantic_bundle = {"typed_plan": plan, "operand_semantic_specs": specs,
                       "predicate_semantic_signatures": signatures, "edge_necessity_witnesses": edges}
    semantic_commitment = seal("B2_PILOT13_P5_SEMANTIC_PLAN_V5_3_3", semantic_bundle)
    core = dict(proposal)
    superseded = core.pop("constructor_facing_packet_identity")
    core.pop("mapping_commitment")
    core["authority_matrix"] = dict(core["authority_matrix"])
    core["authority_matrix"].pop("g04b", None)
    for key in ("qualified_executable_implementation_identity", "provider_identity", "emitter_identity",
                "authority_partition_contract_identity", "constructor_compatibility_evaluated"):
        core.pop(key)
    core.update({"qualified_executable_implementation_identity": qualification["implementation_identity"],
        "realization_provider_identity": qualification["provider_identity"], "candidate_emitter_identity": qualification["emitter_identity"],
        "authority_partition_contract_identity": partition["contract_identity"],
        "constructor_source_compatibility_identity": compatibility["compatibility_identity"],
        "constructor_source_compatibility_audit_identity": compatibility_audit["audit_identity"],
        "proposition_derived_typed_plan": plan, "operand_semantic_specs": specs,
        "predicate_semantic_signatures": signatures, "edge_necessity_witnesses": edges,
        "semantic_plan_commitment": semantic_commitment, "class_a_closure_identity": compatibility["class_a_closure_identity"],
        "class_a_closure": "PASS_ALL_DETERMINISTIC_CLOSURE_BEFORE_PROVIDER", "class_b_state": "NOT_CREATED_PRE_REALIZATION",
        "provider_payload_schema": ["clause"], "fragment_denyset_identity": denyset["fragment_denyset_identity"],
        "mandatory_release_facing_path": ["FROZEN_SEMANTICS", "PRE_INVOCATION_CLOSURE", "CLAUSE_ONLY_GENERATION",
            "ACTUAL_UTF8_BYTES", "TRUSTED_COORDINATE_BOUND_CLASS_B_OBSERVATION", "SEMANTIC_CONFORMANCE", "CONDITIONAL_EMITTER"],
        "emitter_requirement": "MATCHING_TRUSTED_CONFORMANCE_RECEIPT_ONLY",
        "status": "G02B_RELEASE_CANDIDATE_ZERO_CONSTRUCTION"})
    packet_id = seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTOR_PACKET_G02B_V5_3_3", core)
    packet = {**core, "constructor_facing_packet_identity": packet_id}
    release_core = {"constructor_facing_packet_identity": packet_id,
        "packet_seal_namespace": "B2_DEVELOPMENT_PILOT13_CONSTRUCTOR_PACKET_G02B_V5_3_3",
        "immutable_assignment_identity": mapping["sealed_assignment_identity"],
        "sufficiency_receipt_identity": packet["sufficiency_receipt_identity"], "selected_proposition_id": "P5",
        "selected_supporting_span_sha256": packet["selected_supporting_span_sha256"],
        "authorized_visible_context_sha256": packet["authorized_visible_context_sha256"],
        "unselected_proposition_or_fallback_authority": "ABSENT", "partition": "DEVELOPMENT",
        "creative_premise_family_id": "UNASSIGNED", "qualified_executable_implementation_identity": qualification["implementation_identity"],
        "realization_provider_identity": qualification["provider_identity"], "candidate_emitter_identity": qualification["emitter_identity"],
        "authority_partition_contract_identity": partition["contract_identity"],
        "constructor_source_compatibility_identity": compatibility["compatibility_identity"],
        "constructor_source_compatibility_audit_identity": compatibility_audit["audit_identity"],
        "semantic_plan_commitment": semantic_commitment, "class_a_closure_identity": compatibility["class_a_closure_identity"],
        "fragment_denyset_identity": denyset["fragment_denyset_identity"],
        "release_mode": "PATHLESS_SINGLE_OBJECT_CAPABILITY_NOT_RELEASED_TO_CONSTRUCTOR",
        "single_use_state": "UNCONSUMED_0_OF_1_NOT_AUTHORIZED", "constructor_invocation_authorized": False}
    release_id = seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTOR_ACCESS_RELEASE_V5_3_3", release_core)
    transport = {"constructor_role": "CONSTRUCTOR", "packet_delivery": "IN_MEMORY_EXACT_BYTES_SINGLE_USE_PATHLESS_CAPABILITY",
                 **{key: False for key in ("repository_access", "filesystem_path_access", "sibling_artifact_discovery",
                    "environment_inheritance", "command_line_payload", "process_handle_inheritance", "metadata_enumeration",
                    "cache_or_temp_file", "import_time_repository_access", "logs_contain_packet_or_mapping",
                    "exceptions_contain_packet_or_mapping", "network_access", "constructor_invocation_authorized",
                    "provider_invocation_authorized", "emitter_invocation_authorized")}}
    release = {"schema_name": "batch2-development-pilot13-constructor-access-release-v5-3-3", "schema_version": "5.3.3",
               "release_core": release_core, "release_identity": release_id, "constructor_packet": packet,
               "constructor_visible_object_set": ["CONSTRUCTOR_PACKET_EXACT_BYTES"], "transport_policy": transport}
    forbidden = [rb"HMCV1", rb"M13", rb"ABSURD_LOGICAL_EXTENSION", rb"LITERALIZATION", rb"MISDIRECTION",
                 rb"mechanism_id", rb"mechanism_name", rb"close_alternative", rb"mapping_commitment",
                 rb"BLIND_EVALUATION", rb"owner.preference", rb"G04B", rb"pool", rb'"proposition_id":"P6"']
    hits = [item.decode() for item in forbidden if re.search(item, canonical(packet), re.I)]
    require(not hits, f"leakage {hits}")
    require(packet["candidate_surface"] is None and packet["constructor_invoked"] is False, "candidate")
    require(packet["class_b_state"] == "NOT_CREATED_PRE_REALIZATION" and packet["provider_payload_schema"] == ["clause"], "Class B/provider")
    require(all(value is False for value in packet["authority_matrix"].values()), "authority")
    audit_core = {"schema_name": "batch2-development-pilot13-g02b-preconstruction-audit-v5-3-3", "schema_version": "5.3.3",
        "reviewed_commit": COMMIT, "superseded_packet_identity": superseded, "constructor_facing_packet_identity": packet_id,
        "release_identity": release_id, "implementation_provider_emitter_binding": "PASS_EXACT_V5_3_3",
        "compatibility_and_audit_binding": "PASS_EXACT", "selected_proposition_and_span_binding": "PASS_EXACT_P5_ONLY_NO_P6_FALLBACK",
        "semantic_plan_binding": "PASS_EXACT_THREE_NODES_TWO_EDGES_NO_UNBOUND_OPERANDS",
        "class_a_closure": "PASS_ALL_DETERMINISTIC_CLOSURE_BEFORE_PROVIDER", "class_b_state": "NOT_CREATED_PRE_REALIZATION",
        "provider_payload_schema": "PASS_EXACT_CLAUSE_ONLY", "predicate_role_and_affordance_binding": "PASS_3_OF_3",
        "edge_counterfactual_non_arbitrariness_binding": "PASS_2_OF_2", "terminal_edge_binding": "PASS_EQUAL_STRENGTH",
        "mandatory_release_facing_path": "PASS_EXACT_V5_3_3", "emitter_gating": "PASS_MATCHING_TRUSTED_RECEIPT_REQUIRED",
        "fragment_denyset_binding": f"PASS_EXACT_{len(denyset['candidate_sources'])}_NONBLIND_DEVELOPMENT_FAMILIES_{len(denyset['normalized_ngram_sha256'])}_HASHES",
        "blind_reserve_access": "NONE", "sealed_mapping_access": "DENIED_TO_CONSTRUCTOR", "pathless_single_object_isolation": "PASS",
        "label_target_pool_answer_key_and_p6_scan": "PASS_ZERO_HITS", "constructor_invocations": 0, "provider_invocations": 0,
        "emitter_invocations": 0, "candidate_surfaces": 0, "capability_state": "UNCONSUMED_0_OF_1_NOT_AUTHORIZED",
        "post_qualification_deterministic_infrastructure_defect": "REPAIRED_PILOT13_RELEASE_SCHEMA_AND_BINDING_ALLOWLIST",
        "infrastructure_repair_scope": "GENERIC_CONSTRUCTOR_ACCESS_VERIFIER_PILOT13_V5_3_3_SCHEMA_AND_EXACT_BINDINGS_ONLY",
        "infrastructure_repair_preserved_qualified_executable_bytes": True, "downstream_authority_granted": False,
        "deterministic_blockers_remaining": [], "verdict": "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION"}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT13_G02B_AUDIT_V5_3_3", audit_core)}
    write("humor-mechanics-batch2-nonblind-development-fragment-denyset-v5-3-3.json", denyset)
    write("humor-mechanics-batch2-development-pilot13-constructor-facing-assignment-g02b-v5-3-3.json", packet)
    write("humor-mechanics-batch2-development-pilot13-constructor-access-release-v5-3-3.json", release)
    write("humor-mechanics-batch2-development-pilot13-g02b-preconstruction-audit-v5-3-3.json", audit)
    print(json.dumps({"verdict": audit["verdict"], "packet_identity": packet_id, "release_identity": release_id,
                      "audit_identity": audit["audit_identity"], "fragment_denyset_identity": denyset["fragment_denyset_identity"],
                      "families": len(denyset["candidate_sources"]), "hashes": len(denyset["normalized_ngram_sha256"])}, sort_keys=True))


if __name__ == "__main__":
    main()
