"""Validate Pilot 13 P5 against V5.3.3 without release or invocation."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from pastila_scout.humor_batch2_development_constructor_v5_1 import (
    derive_proposition_plan, extract_typed_operands, validate_typed_plan,
)
from pastila_scout.humor_batch2_development_constructor_v5_3_semantic_enforcement import (
    EdgeNecessityWitness, OperandSemanticSpec, PredicateSemanticSignature, validate_semantic_plan,
)
from pastila_scout.humor_batch2_development_constructor_v5_3_3_integration import CLASS_C_FIELDS

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "18c13566989dae7c69d494c75a5d774c0de32f1b"
PROPOSAL_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-constructor-facing-assignment-proposal-v5-3-3.json"
MAPPING_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-sealed-assignment-v5-3-3.json"
OBLIGATION_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot13-obligation-family-v5-3-3.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_json(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT))


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), "artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    proposal, mapping, obligation = git_json(PROPOSAL_PATH), git_json(MAPPING_PATH), git_json(OBLIGATION_PATH)
    qualification = git_json("docs/artifacts/humor-mechanics-batch2-constructor-v5-3-3-zero-family-executable-integration-qualification.json")
    partition = git_json("docs/artifacts/humor-mechanics-batch2-constructor-v5-3-3-single-source-authority-partition-contract.json")
    integration_path = "src/pastila_scout/humor_batch2_development_constructor_v5_3_3_integration.py"
    release_path = "src/pastila_scout/humor_batch2_development_constructor_v5_3_3_release_path.py"
    integration_source, release_source = git_bytes(integration_path), git_bytes(release_path)
    implementation = seal("B2_CONSTRUCTOR_V5_3_3_EXECUTABLE_IMPLEMENTATION", {
        "integration_sha256": hashlib.sha256(integration_source).hexdigest(),
        "release_path_sha256": hashlib.sha256(release_source).hexdigest(),
        "contract": partition["contract_identity"]})
    require(proposal["constructor_facing_packet_identity"] == "95a69db9e90f2383fae884b82ca572ef74990a23aa9da788b38312b3955f3aa4", "proposal")
    require(mapping["sealed_assignment_identity"] == "ee5f0743e5c2e52945a26b2fd2afe709d73d6865667bbca3826d1ede9a845954", "mapping")
    require(obligation["obligation_family_identity"] == "2ee11a101748644a43062aadbd9ceee9bcb69b1a3eef2ed90a29e598ca5cded3", "obligation")
    require(proposal["unlabeled_operational_obligation"]["obligation_instance_identity"] == "85b142a8988b99981d7a44c2c2665fce1b303a441663d3dc1b383e03ca773d3d", "instance")
    require(qualification["qualification_identity"] == "9016f7a82cb04ba447c2c2ae4275861ef0bfbd16782c4be3584d85220f5b5c0a", "qualification")
    require(qualification["implementation_identity"] == implementation == "3c7c353d488d032dd69f9d12a07a621bfc7bb95b668e76efc08494546f5d5362", "implementation")
    require(qualification["provider_identity"] == proposal["provider_identity"] == "865c1e9f7cedb5e78b5ecd7524781a8ed8a50816a9be76910c7ee76c375b81ea", "provider")
    require(qualification["emitter_identity"] == proposal["emitter_identity"] == "5bb1fae007fb8898f7e1a514622bb9bac99d992cc81189cd4ffd33b60fa76a8b", "emitter")
    require(qualification["INFRASTRUCTURE_READINESS_VERDICT"] == "READY_FOR_NEXT_INDEPENDENT_FAMILY_AS_MECHANISM_TRIAL", "readiness")
    require(qualification["CLASS_A_PREINVOCATION_CLOSURE_VERDICT"] == "PASS_ALL_DETERMINISTIC_CLOSURE_BEFORE_PROVIDER", "Class A qualification")
    require(qualification["CLASS_B_BYTE_DERIVATION_VERDICT"] == "PASS_OBSERVED_EXCLUSIVELY_FROM_ACTUAL_UTF8_BYTES", "Class B qualification")
    require(qualification["CLAUSE_ONLY_PROVIDER_VERDICT"] == "PASS_EXACT_ONE_FIELD" and CLASS_C_FIELDS == frozenset({"clause"}), "provider schema")
    require(qualification["LEGACY_PATH_UNREACHABILITY_VERDICT"] == "PASS_NO_HISTORICAL_MIXED_RUNTIME_IMPORT_OR_ENTRY_POINT", "legacy path")
    require(qualification["EMITTER_GATING_VERDICT"] == "PASS_MATCHING_TRUSTED_RECEIPT_REQUIRED", "emitter gate")
    propositions = proposal["closed_factual_authority_envelope"]["propositions"]
    require(proposal["selected_proposition_id"] == "P5" and len(propositions) == 1, "P5 only")
    require(proposal["unselected_proposition_or_fallback_authority"] == "ABSENT", "P6 fallback")
    proposition, source = propositions[0], proposal["exact_authorized_visible_context_utf8"]
    span = proposition["supporting_span"]
    require(hashlib.sha256(source.encode()).hexdigest() == proposal["selected_supporting_span_sha256"] == span["span_sha256"] == "e1b854d2b88d4489a45f6e53ce937dff06e2e9fad3abe7258a940fb5bf4a4566", "span")
    operands = extract_typed_operands(source, proposition)
    plan = derive_proposition_plan(operands)
    qualifier_id = "FACT_QUALIFICATION" if operands.qualification else "FACT_RELATION"
    validate_typed_plan(plan, frozenset({operands.relation_id, "FACT_OBJECT", qualifier_id}))
    operand_specs = (
        OperandSemanticSpec(operands.relation_id, "P5_POST_INSTALLATION_POSITION_AND_TIME_RECORDING_RELATION",
                            ("POST_INSTALLATION_RECORDING_RELATION",), ("LICENSE_LOCAL_NONFACTUAL_EXTENSION",), (), False),
        OperandSemanticSpec(qualifier_id, "P5_POST_INSTALLATION_TEMPORAL_CONDITION",
                            ("TEMPORAL_PRECONDITION",), ("QUALIFY_RECORDING_DISPOSITION",), (), False),
        OperandSemanticSpec("FACT_OBJECT", "P5_CAMPAIGN_LOG_DESTINATION",
                            ("RECORD_DESTINATION",), ("RECEIVE_POSITION_AND_TIME_RECORD",), (), False),
        OperandSemanticSpec("INVENTED_RELATION_1", "LOCAL_POST_INSTALLATION_RECORD_ELIGIBILITY_STATE",
                            ("LICENSED_RECORDING_STATE",), ("PROPAGATE_TO_BOUND_LOG",),
                            (operands.relation_id, qualifier_id), False),
        OperandSemanticSpec("INVENTED_RELATION_2", "LOG_BOUND_RECORD_STATE",
                            ("LOG_BOUND_RECORD_STATE",), ("RESOLVE_AGAINST_SOURCE_RECORDING_RELATION",),
                            ("INVENTED_RELATION_1", "FACT_OBJECT"), False),
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
    coverage = validate_semantic_plan(typed_plan=plan, operand_specs=operand_specs, predicate_signatures=signatures, edge_witnesses=edges)
    require((coverage.nodes_validated, coverage.edges_validated, coverage.terminal_edge_validated) == (3, 2, True), "semantic coverage")
    plan_evidence = [{"node_id": node.node_id, "actor": node.bound_actor_id, "actor_role": node.actor_role,
                      "predicate": node.predicate_id, "patient": node.bound_patient_id,
                      "predecessors": list(node.predecessor_node_ids), "introduces": list(node.introduces_ids)} for node in plan]
    class_a_core = {"exact_source_utf8_sha256": hashlib.sha256(source.encode()).hexdigest(), "proposition_id": "P5",
                    "typed_plan": plan_evidence,
                    "operand_specs": [{"operand_id": item.operand_id, "semantic_roles": list(item.semantic_roles),
                                       "affordances": list(item.affordances), "provenance_operand_ids": list(item.provenance_operand_ids)} for item in operand_specs],
                    "predicate_signatures": [{"predicate_id": item.predicate_id,
                                              "required_actor_roles": list(item.required_actor_roles),
                                              "required_patient_roles": list(item.required_patient_roles)} for item in signatures],
                    "edge_witnesses": [{"predecessor": item.predecessor_node_id, "successor": item.successor_node_id,
                                        "operand": item.produced_operand_id, "rule": item.explicit_licensing_rule} for item in edges],
                    "implementation_identity": implementation, "provider_identity": qualification["provider_identity"],
                    "emitter_identity": qualification["emitter_identity"], "provider_schema": ["clause"]}
    class_a_identity = seal("B2_DEVELOPMENT_PILOT13_V5_3_3_STATIC_CLASS_A_CLOSURE", class_a_core)
    authority_names = ("g02b_release", "constructor_invocation", "provider_invocation", "emitter_invocation", "realization",
                       "candidate_emission", "class_b_surface_observation", "semantic_conformance", "fragment_collision",
                       "g02", "g02c", "g03", "g03b", "g03c", "romanian_naturalness", "voice", "owner_review",
                       "g04b", "model_exposure", "training", "runtime_integration", "production_routing")
    core = {"schema_name": "batch2-development-pilot13-constructor-v5-3-3-source-compatibility-v1", "schema_version": "1.0.0",
        "reviewed_commit": COMMIT, "pilot_role": "LEGITIMATE_END_TO_END_MECHANISM_TRIAL",
        "qualification_identity": qualification["qualification_identity"], "constructor_implementation_identity": implementation,
        "provider_identity": qualification["provider_identity"], "emitter_identity": qualification["emitter_identity"],
        "authority_partition_contract_identity": partition["contract_identity"],
        "constructor_facing_proposal_identity": proposal["constructor_facing_packet_identity"],
        "sealed_assignment_identity": mapping["sealed_assignment_identity"], "selected_proposition_id": "P5",
        "selected_span_sha256": span["span_sha256"],
        "authority_binding": "PASS_EXACT_P5_AND_AUTHORIZED_SUPPORTING_SPAN_ONLY_NO_P6_FALLBACK",
        "typed_operand_extraction": {"verdict": "PASS_SOURCE_SHAPE_NEUTRAL", "relation_id": operands.relation_id,
                                     "subject_bound": True, "predicate_bound": True, "object_bound": True, "qualification_bound": True},
        "recovered_plan_topology": plan_evidence, "abstract_plan_closure": "PASS_THREE_TYPED_NODES_TWO_EDGES_NO_UNBOUND_OPERANDS",
        "semantic_plan_coverage": {"nodes": "3/3", "edges": "2/2", "terminal_edge_validated": True},
        "semantic_role_and_predicate_argument_signatures": "PASS_3_OF_3",
        "required_role_produced_role_compatibility": "PASS_EACH_EDGE",
        "action_affordance_compatibility": "PASS_EACH_NODE_AND_EDGE",
        "entity_identity_preservation": "PASS_NO_RECLASSIFICATION_USED_OR_REQUIRED",
        "privileged_role_or_affordance_derivation": "ABSENT",
        "causal_direction": "PASS_SOURCE_TO_L1_TO_L2_TO_TERMINAL",
        "counterfactual_dependency_and_non_arbitrariness": "PASS_2_OF_2_EDGES",
        "terminal_edge_strength": "PASS_EQUAL_TO_INTERMEDIATE_EDGES",
        "topology_arity_and_operand_closure": "PASS_3_NODES_2_EDGES_NO_UNBOUND_OPERANDS",
        "class_a_closure": "PASS_ALL_DETERMINISTIC_CLOSURE_BEFORE_PROVIDER", "class_a_closure_identity": class_a_identity,
        "class_b_state": "NOT_CREATED_PRE_REALIZATION", "provider_schema": ["clause"],
        "provider_schema_verdict": "PASS_EXACT_ONE_FIELD", "factual_authority_widening": "ABSENT",
        "constructor_invoked": False, "provider_invoked": False, "emitter_invoked": False, "candidate_surface": None,
        "constructor_release": False, "post_qualification_deterministic_infrastructure_defect": "NONE_DISCOVERED",
        "release_eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02B_PRECONSTRUCTION_REVIEW_ONLY",
        "verdict": "PASS_SOURCE_COMPATIBLE_WITH_FROZEN_CONSTRUCTOR_V5_3_3_STATIC_SEMANTIC_PLAN_NO_RELEASE",
        "authority_matrix": {key: False for key in authority_names}}
    receipt = {**core, "compatibility_identity": seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTOR_V5_3_3_SOURCE_COMPATIBILITY_V1", core)}
    audit_core = {"schema_name": "batch2-development-pilot13-constructor-v5-3-3-source-compatibility-audit-v1",
        "schema_version": "1.0.0", "compatibility_identity": receipt["compatibility_identity"], "git_object_only": True,
        "exact_frozen_bindings": "PASS", "exact_p5_authority_span": "PASS", "p6_fallback_or_comparative_authority": "ABSENT",
        "source_shape_neutral_extraction": "PASS", "typed_plan_closure": "PASS",
        "semantic_signature_coverage": "PASS_3_OF_3", "semantic_edge_coverage": "PASS_2_OF_2",
        "terminal_edge_equal_strength": "PASS", "class_a_closure": "PASS", "class_b_observations": "ABSENT",
        "clause_only_provider": "PASS_EXACT_ONE_FIELD", "constructor_invocations": 0, "provider_invocations": 0,
        "emitter_invocations": 0, "candidate_surfaces_created": 0, "g02b_release": "NOT_PERFORMED",
        "post_qualification_deterministic_infrastructure_defect": "NONE_DISCOVERED", "deterministic_blockers": [],
        "verdict": "PASS_STATIC_SEMANTIC_PLAN_VALIDATION_ZERO_REALIZATION_ZERO_CONSTRUCTION_NO_RELEASE"}
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT13_CONSTRUCTOR_V5_3_3_SOURCE_COMPATIBILITY_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot13-constructor-v5-3-3-source-compatibility-v1.json", receipt)
    write("humor-mechanics-batch2-development-pilot13-constructor-v5-3-3-source-compatibility-audit-v1.json", audit)
    print(json.dumps({"verdict": receipt["verdict"], "compatibility_identity": receipt["compatibility_identity"],
                      "audit_identity": audit["audit_identity"], "topology": "3_NODES_2_EDGES",
                      "class_a": receipt["class_a_closure"], "class_b": receipt["class_b_state"],
                      "post_qualification_defect": receipt["post_qualification_deterministic_infrastructure_defect"]}, sort_keys=True))


if __name__ == "__main__":
    main()
