"""Validate Pilot 12 P5 against Constructor V5.3.1 without release or invocation."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from pastila_scout.humor_batch2_development_constructor_v5_1 import (
    derive_proposition_plan,
    extract_typed_operands,
    validate_typed_plan,
)
from pastila_scout.humor_batch2_development_constructor_v5_3_semantic_enforcement import (
    EdgeNecessityWitness,
    OperandSemanticSpec,
    PredicateSemanticSignature,
    validate_semantic_plan,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "6b568e541f6966bdb128233c98094bdb5a1698b4"
PROPOSAL_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot12-constructor-facing-assignment-proposal-v5-3-1.json"
MAPPING_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot12-sealed-assignment-v5-3-1.json"
OBLIGATION_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot12-obligation-family-v5-3-1.json"
RUNTIME_PATH = "src/pastila_scout/humor_batch2_development_constructor_v5_3_1_runtime.py"
ALIGNMENT_PATH = "src/pastila_scout/humor_batch2_development_constructor_v5_3_1_surface_alignment.py"


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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    proposal, mapping, obligation = git_json(PROPOSAL_PATH), git_json(MAPPING_PATH), git_json(OBLIGATION_PATH)
    base_contract = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-contract-v5-3.json")
    alignment_contract = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-surface-witness-alignment-contract-v5-3-1.json")
    implementation = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v5-3-1.json")
    provider = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-3-1-realization-provider-implementation.json")
    emitter = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-3-1-candidate-emitter-implementation.json")
    static_audit = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-3-1-runtime-static-audit-v1.json")
    require(proposal["constructor_facing_packet_identity"] == "7fd84b56a1ca02e9e91b3710099523a70cbb777a16fb73de0563f6bca6e6a440", "proposal")
    require(mapping["sealed_assignment_identity"] == "03f83dafe45d015bd00b31cf2454a88ecf057c4f37d7b4d0158557ac72258f1c", "mapping")
    require(obligation["obligation_family_identity"] == "28f806daec135bf8fdb6d49e7b98eda1941f81399f3fe33e747ae2cd5af348bf", "obligation")
    require(proposal["unlabeled_operational_obligation"]["obligation_instance_identity"] == "23419666734914cc7b8cdf4e18ae0f283720cb6bab8ea996434868ea6647005a", "instance")
    require(base_contract["constructor_contract_identity"] == "9d811b18c16e8770549c19c9d8be63ef6f04e030fa67b5a47167b5e7ddc1bef6", "base contract")
    require(alignment_contract["successor_contract_identity"] == "c4af75cd962802d0035d9de39e6d014f715d5b5f5b60fd690ea3761f289d99fc", "alignment contract")
    require(implementation["constructor_implementation_identity"] == "a966e92c37d6f957cbd080a9d2961cf05b288633d0d6e9f309c7d6baec956894", "implementation")
    require(provider["realization_provider_identity"] == "2846406e03cea3fbbdca5531a7d0bf23fc39b116f7e0413a4bc73a65ea9b6992", "provider")
    require(emitter["candidate_emitter_identity"] == "d08e74b2ccfaa5e157a86376e46b2ac70c7f4225261ecb1112c063a236804dd1", "emitter")
    require(static_audit["static_audit_identity"] == "9ebb9c17e228c5ed05f7b711b1284b0ca7a5defa697407d7c690e5f3e9a01d43", "static audit")
    propositions = proposal["closed_factual_authority_envelope"]["propositions"]
    require(proposal["selected_proposition_id"] == "P5" and len(propositions) == 1, "P5 only")
    require(proposal["unselected_proposition_or_fallback_authority"] == "ABSENT", "P6 fallback")
    proposition, source = propositions[0], proposal["exact_authorized_visible_context_utf8"]
    span = proposition["supporting_span"]
    require(hashlib.sha256(source.encode()).hexdigest() == proposal["selected_supporting_span_sha256"] == span["span_sha256"], "span")
    operands = extract_typed_operands(source, proposition)
    plan = derive_proposition_plan(operands)
    qualifier_id = "FACT_QUALIFICATION" if operands.qualification else "FACT_RELATION"
    validate_typed_plan(plan, frozenset({operands.relation_id, "FACT_OBJECT", qualifier_id}))

    operand_specs = (
        OperandSemanticSpec(operands.relation_id, "P5_CONDITIONED_BOX_TRANSPORT_DISPOSITION",
                            ("CONDITIONED_TRANSPORT_RELATION",), ("LICENSE_LOCAL_NONFACTUAL_EXTENSION",), (), False),
        OperandSemanticSpec(qualifier_id, "P5_SAME_DESTINATION_SHELF_CONDITION",
                            ("CONDITION_STATE",), ("QUALIFY_TRANSPORT_DISPOSITION",), (), False),
        OperandSemanticSpec("FACT_OBJECT", "P5_LIBRARY_STORAGE_DESTINATION",
                            ("TRANSFER_DESTINATION",), ("RECEIVE_BOX",), (), False),
        OperandSemanticSpec("INVENTED_RELATION_1", "LOCAL_TRANSPORT_ELIGIBILITY_STATE",
                            ("LICENSED_TRANSPORT_STATE",), ("PROPAGATE_TO_BOUND_DESTINATION",),
                            (operands.relation_id, qualifier_id), False),
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
    coverage = validate_semantic_plan(typed_plan=plan, operand_specs=operand_specs,
                                      predicate_signatures=signatures, edge_witnesses=edges)
    require((coverage.nodes_validated, coverage.edges_validated, coverage.terminal_edge_validated) == (3, 2, True), "semantic coverage")

    runtime_source = git_bytes(RUNTIME_PATH).decode("utf-8")
    alignment_source = git_bytes(ALIGNMENT_PATH).decode("utf-8")
    require(hashlib.sha256(runtime_source.encode()).hexdigest() == implementation["module_sha256"], "runtime hash")
    runtime_functions = {node.name: node for node in ast.parse(runtime_source).body if isinstance(node, ast.FunctionDef)}
    require({"realize_aligned_semantic_typed_plan", "emit_aligned_semantic_candidate_utf8"}.issubset(runtime_functions), "runtime functions")
    require("validate_semantic_plan" in ast.unparse(runtime_functions["realize_aligned_semantic_typed_plan"]), "plan validation order")
    require("validate_surface_semantics" in ast.unparse(runtime_functions["emit_aligned_semantic_candidate_utf8"]), "emitter validation")
    require("_validate_aligned_structure" in ast.unparse(runtime_functions["emit_aligned_semantic_candidate_utf8"]), "coordinate alignment")
    require("validate_coordinate_bound_role_witness" in alignment_source
            and "ROMANIAN_AMBELE_AMBELOR_CASE_INFLECTION" in alignment_source
            and "EXACT_NFKC_CASEFOLD" in alignment_source,
            "alignment constraints")
    plan_evidence = [{"node_id": node.node_id, "actor": node.bound_actor_id, "actor_role": node.actor_role,
                      "predicate": node.predicate_id, "patient": node.bound_patient_id,
                      "predecessors": list(node.predecessor_node_ids), "introduces": list(node.introduces_ids)} for node in plan]
    core = {
        "schema_name": "batch2-development-pilot12-constructor-v5-3-1-source-compatibility-v1",
        "schema_version": "1.0.0", "reviewed_commit": COMMIT,
        "base_constructor_contract_identity": base_contract["constructor_contract_identity"],
        "alignment_contract_identity": alignment_contract["successor_contract_identity"],
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "realization_provider_identity": provider["realization_provider_identity"],
        "candidate_emitter_identity": emitter["candidate_emitter_identity"],
        "constructor_static_audit_identity": static_audit["static_audit_identity"],
        "constructor_facing_proposal_identity": proposal["constructor_facing_packet_identity"],
        "sealed_assignment_identity": mapping["sealed_assignment_identity"], "selected_proposition_id": "P5",
        "selected_span_sha256": span["span_sha256"],
        "authority_binding": "PASS_EXACT_P5_AND_AUTHORIZED_SUPPORTING_SPAN_ONLY_NO_P6_FALLBACK",
        "typed_operand_extraction": {"verdict": "PASS_SOURCE_SHAPE_NEUTRAL", "relation_id": operands.relation_id,
                                     "subject_bound": True, "predicate_bound": True, "object_bound": True,
                                     "qualification_bound": True},
        "recovered_plan_topology": plan_evidence,
        "abstract_plan_closure": "PASS_THREE_TYPED_NODES_TWO_EDGES_NO_UNBOUND_OPERANDS",
        "semantic_plan_coverage": {"nodes": "3/3", "edges": "2/2", "terminal_edge_validated": True},
        "semantic_role_and_predicate_argument_signatures": "PASS_ALL_THREE_RELATIONS",
        "required_role_produced_role_compatibility": "PASS_EACH_EDGE",
        "action_affordance_compatibility": "PASS_EACH_NODE_AND_EDGE",
        "counterfactual_dependency_and_non_arbitrariness": "PASS_2_OF_2_EDGES",
        "terminal_edge_strength": "PASS_EQUAL_TO_INTERMEDIATE_EDGES",
        "entity_identity_preservation": "PASS_NO_RECLASSIFICATION_USED_OR_REQUIRED",
        "privileged_role_or_affordance_derivation": "ABSENT",
        "unbound_operands_or_role_incompatible_transitions": "ABSENT",
        "alignment_semantics": "PASS_STATIC_CONSTRAINT_ONLY_NO_OPPORTUNITY_INVENTED_OR_USED_AS_PLAN_EVIDENCE",
        "insufficient_evidence_rejected": ["LEXICAL_RECURRENCE", "STRUCTURAL_PREDECESSOR_CONTINUITY",
                                           "RECLASSIFICATION_ALONE", "POTENTIAL_TERMINAL_WITNESS",
                                           "POTENTIAL_MORPHOLOGICAL_ALIGNMENT"],
        "factual_authority_widening": "ABSENT", "semantic_plan_created": True,
        "realization_or_surface_witnesses_created": False, "constructor_invoked": False,
        "provider_invoked": False, "emitter_invoked": False, "candidate_surface": None,
        "constructor_release": False,
        "release_eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02B_PRECONSTRUCTION_REVIEW_ONLY",
        "verdict": "PASS_SOURCE_COMPATIBLE_WITH_FROZEN_CONSTRUCTOR_V5_3_1_STATIC_SEMANTIC_PLAN_NO_RELEASE",
        "authority_matrix": {key: False for key in ("g02b_release", "constructor_invocation", "provider_invocation",
            "emitter_invocation", "realization", "candidate_emission", "post_realization_coordinate_bound_semantic_conformance",
            "fragment_collision_evaluation", "g02", "g02c", "g03", "g04b_pool_certification", "model_exposure",
            "training", "runtime_integration", "production_routing")},
    }
    receipt = {**core, "compatibility_identity": seal("B2_DEVELOPMENT_PILOT12_CONSTRUCTOR_V5_3_1_SOURCE_COMPATIBILITY_V1", core)}
    audit_core = {
        "schema_name": "batch2-development-pilot12-constructor-v5-3-1-source-compatibility-audit-v1",
        "schema_version": "1.0.0", "compatibility_identity": receipt["compatibility_identity"],
        "git_object_only": True, "exact_frozen_bindings": "PASS", "exact_p5_authority_span": "PASS",
        "p6_fallback_or_comparative_authority": "ABSENT", "source_shape_neutral_extraction": "PASS",
        "typed_plan_closure": "PASS", "semantic_signature_coverage": "PASS_3_OF_3",
        "semantic_edge_coverage": "PASS_2_OF_2", "terminal_edge_equal_strength": "PASS",
        "privileged_affordance_minting": "ABSENT",
        "alignment_constraint_application": "PASS_NO_ALIGNMENT_OPPORTUNITY_INVENTED_OR_OPTIMIZED",
        "constructor_invocations": 0, "provider_invocations": 0, "emitter_invocations": 0,
        "candidate_surfaces_created": 0, "g02b_release": "NOT_PERFORMED", "deterministic_blockers": [],
        "verdict": "PASS_STATIC_SEMANTIC_PLAN_VALIDATION_ZERO_REALIZATION_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT12_CONSTRUCTOR_V5_3_1_SOURCE_COMPATIBILITY_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot12-constructor-v5-3-1-source-compatibility-v1.json", receipt)
    write("humor-mechanics-batch2-development-pilot12-constructor-v5-3-1-source-compatibility-audit-v1.json", audit)
    print(json.dumps({"verdict": receipt["verdict"], "compatibility_identity": receipt["compatibility_identity"],
                      "audit_identity": audit["audit_identity"], "topology": "3_NODES_2_EDGES"}, sort_keys=True))


if __name__ == "__main__":
    main()
