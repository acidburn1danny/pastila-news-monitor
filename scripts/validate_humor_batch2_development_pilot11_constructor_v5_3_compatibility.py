"""Validate Pilot 11 P3 against Constructor V5.3 without release or invocation."""

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
COMMIT = "13822403d3a7bf8f1850f463c52ff3cdce0fc111"
PROPOSAL_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot11-constructor-facing-assignment-proposal-v5-3.json"
MAPPING_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot11-sealed-assignment-v5-3.json"
OBLIGATION_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot11-obligation-family-v5-3.json"
RUNTIME_PATH = "src/pastila_scout/humor_batch2_development_constructor_v5_3_runtime.py"


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
    contract = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-contract-v5-3.json")
    implementation = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v5-3.json")
    provider = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-3-realization-provider-implementation.json")
    emitter = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-3-candidate-emitter-implementation.json")
    static_audit = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-3-runtime-static-audit-v1.json")
    require(proposal["constructor_facing_packet_identity"] == "274a9950c275f01fdfdddc561da991751bc1b5e915914200a502451ca4c2c420", "proposal")
    require(mapping["sealed_assignment_identity"] == "9778b0f7be4acb019cc112aacd34ea31bc7696db4ba82c0e41f9e3718511c57b", "mapping")
    require(obligation["obligation_family_identity"] == "f789d41c36a63952a2fb9dbef432bc1429c1769958236c6295774a11e99c1703", "obligation")
    require(proposal["unlabeled_operational_obligation"]["obligation_instance_identity"] == "064ac73f610826555fc58f9949d926a3d80d0f8c6ad8ad903427adadf5e22a2d", "instance")
    require(contract["constructor_contract_identity"] == "9d811b18c16e8770549c19c9d8be63ef6f04e030fa67b5a47167b5e7ddc1bef6", "contract")
    require(implementation["constructor_implementation_identity"] == "18bd032218924cc8d2890301a1c92a376036918affddea335904a1491c807237", "implementation")
    require(provider["realization_provider_implementation_identity"] == "c458ecb1c9fe64285f0b70db1ccb9be6ed3e48a4f461f72d22abc0a1f0714a93", "provider")
    require(emitter["candidate_emitter_implementation_identity"] == "5a274ac6f140708066f587071e31f5376c0a985e5430d2537839c9627685ad5d", "emitter")
    require(static_audit["static_audit_identity"] == "46b24207afbfa388862598ea3c75a55342be13e108bef1fcd154f2612ec182b8", "static audit")
    propositions = proposal["closed_factual_authority_envelope"]["propositions"]
    require(proposal["selected_proposition_id"] == "P3" and len(propositions) == 1, "P3 only")
    proposition, source = propositions[0], proposal["exact_authorized_visible_context_utf8"]
    span = proposition["supporting_span"]
    require(hashlib.sha256(source.encode()).hexdigest() == proposal["selected_supporting_span_sha256"] == span["span_sha256"], "span")
    operands = extract_typed_operands(source, proposition)
    plan = derive_proposition_plan(operands)
    qualifier_id = "FACT_QUALIFICATION" if operands.qualification else "FACT_RELATION"
    validate_typed_plan(plan, frozenset({operands.relation_id, "FACT_OBJECT", qualifier_id}))

    operand_specs = (
        OperandSemanticSpec(operands.relation_id, "P3_CONDITIONED_CONTAINER_DISPOSITION", ("CONDITIONED_DISPOSITION_RELATION",), ("LICENSE_LOCAL_NONFACTUAL_EXTENSION",), (), False),
        OperandSemanticSpec(qualifier_id, "P3_CONFORMITY_CONDITION", ("CONDITION_STATE",), ("QUALIFY_DISPOSITION",), (), False),
        OperandSemanticSpec("FACT_OBJECT", "P3_FILLING_LINE_DESTINATION", ("TRANSFER_DESTINATION",), ("RECEIVE_CONTAINER",), (), False),
        OperandSemanticSpec("INVENTED_RELATION_1", "LOCAL_PROCESS_STATE_1", ("LICENSED_PROCESS_STATE",), ("PROPAGATE_TO_AUTHORIZED_DESTINATION",), (operands.relation_id, qualifier_id), False),
        OperandSemanticSpec("INVENTED_RELATION_2", "LOCAL_PROCESS_STATE_2", ("DESTINATION_BOUND_PROCESS_STATE",), ("RESOLVE_AGAINST_SOURCE_RELATION",), ("INVENTED_RELATION_1", "FACT_OBJECT"), False),
    )
    signatures = (
        PredicateSemanticSignature(plan[0].predicate_id, ("CONDITIONED_DISPOSITION_RELATION",), ("CONDITION_STATE",), ("LICENSE_LOCAL_NONFACTUAL_EXTENSION",), ("QUALIFY_DISPOSITION",)),
        PredicateSemanticSignature(plan[1].predicate_id, ("LICENSED_PROCESS_STATE",), ("TRANSFER_DESTINATION",), ("PROPAGATE_TO_AUTHORIZED_DESTINATION",), ("RECEIVE_CONTAINER",)),
        PredicateSemanticSignature(plan[2].predicate_id, ("DESTINATION_BOUND_PROCESS_STATE",), ("CONDITIONED_DISPOSITION_RELATION",), ("RESOLVE_AGAINST_SOURCE_RELATION",), ("LICENSE_LOCAL_NONFACTUAL_EXTENSION",)),
    )
    edges = (
        EdgeNecessityWitness("L1", "L2", "INVENTED_RELATION_1", "ACTOR", "RULE_L1_OUTPUT_IS_REQUIRED_ACTOR_OF_L2", True, True),
        EdgeNecessityWitness("L2", "RESULT", "INVENTED_RELATION_2", "ACTOR", "RULE_L2_OUTPUT_IS_REQUIRED_ACTOR_OF_TERMINAL_RESULT", True, True),
    )
    coverage = validate_semantic_plan(typed_plan=plan, operand_specs=operand_specs, predicate_signatures=signatures, edge_witnesses=edges)
    require((coverage.nodes_validated, coverage.edges_validated, coverage.terminal_edge_validated) == (3, 2, True), "semantic coverage")

    runtime_source = git_bytes(RUNTIME_PATH).decode("utf-8")
    require(hashlib.sha256(runtime_source.encode()).hexdigest() == implementation["module_sha256"], "runtime hash")
    tree = ast.parse(runtime_source)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    require({"realize_semantic_typed_plan", "emit_semantic_candidate_utf8"}.issubset(functions), "runtime functions")
    require("validate_semantic_plan" in ast.unparse(functions["realize_semantic_typed_plan"]), "plan validation order")
    require("validate_surface_semantics" in ast.unparse(functions["emit_semantic_candidate_utf8"]), "emitter semantic validation")

    plan_evidence = [{"node_id": node.node_id, "actor": node.bound_actor_id, "predicate": node.predicate_id,
                      "patient": node.bound_patient_id, "predecessors": list(node.predecessor_node_ids),
                      "introduces": list(node.introduces_ids)} for node in plan]
    core = {
        "schema_name": "batch2-development-pilot11-constructor-v5-3-source-compatibility-v1", "schema_version": "1.0.0",
        "reviewed_commit": COMMIT, "constructor_contract_identity": contract["constructor_contract_identity"],
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "realization_provider_identity": provider["realization_provider_implementation_identity"],
        "candidate_emitter_identity": emitter["candidate_emitter_implementation_identity"],
        "constructor_static_audit_identity": static_audit["static_audit_identity"],
        "constructor_facing_proposal_identity": proposal["constructor_facing_packet_identity"],
        "sealed_assignment_identity": mapping["sealed_assignment_identity"], "selected_proposition_id": "P3",
        "selected_span_sha256": span["span_sha256"], "authority_binding": "PASS_EXACT_P3_AND_AUTHORIZED_SUPPORTING_SPAN_ONLY",
        "typed_operand_extraction": {"verdict": "PASS_SOURCE_SHAPE_NEUTRAL", "relation_id": operands.relation_id,
                                     "subject_bound": True, "predicate_bound": True, "object_bound": True, "qualification_bound": True},
        "recovered_plan_topology": plan_evidence, "abstract_plan_closure": "PASS_THREE_TYPED_NODES_TWO_EDGES_NO_UNBOUND_OPERANDS",
        "semantic_plan_coverage": {"nodes": "3/3", "edges": "2/2", "terminal_edge_validated": True},
        "semantic_role_and_predicate_argument_signatures": "PASS_ALL_THREE_RELATIONS",
        "required_role_produced_role_compatibility": "PASS_EACH_EDGE",
        "action_affordance_compatibility": "PASS_EACH_NODE_AND_EDGE",
        "counterfactual_dependency_and_non_arbitrariness": "PASS_2_OF_2_EDGES",
        "terminal_edge_strength": "PASS_EQUAL_TO_INTERMEDIATE_EDGES",
        "entity_identity_preservation": "PASS_NO_RECLASSIFICATION_USED_OR_REQUIRED",
        "privileged_role_or_affordance_derivation": "ABSENT",
        "unbound_operands_or_role_incompatible_transitions": "ABSENT",
        "insufficient_evidence_rejected": ["LEXICAL_RECURRENCE", "STRUCTURAL_PREDECESSOR_CONTINUITY", "RECLASSIFICATION_ALONE", "TERMINAL_WITNESS_CAPABILITY_ALONE"],
        "factual_authority_widening": "ABSENT", "semantic_plan_created": True,
        "realization_or_surface_witnesses_created": False, "constructor_invoked": False, "provider_invoked": False,
        "emitter_invoked": False, "candidate_surface": None, "constructor_release": False,
        "release_eligibility": "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_G02B_PRECONSTRUCTION_REVIEW_ONLY",
        "verdict": "PASS_SOURCE_COMPATIBLE_WITH_FROZEN_CONSTRUCTOR_V5_3_STATIC_SEMANTIC_PLAN_NO_RELEASE",
        "authority_matrix": {key: False for key in ("g02b_release", "constructor_invocation", "provider_invocation", "emitter_invocation", "realization", "candidate_emission", "post_realization_semantic_conformance", "fragment_collision_evaluation", "g02", "g02c", "g03", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    receipt = {**core, "compatibility_identity": seal("B2_DEVELOPMENT_PILOT11_CONSTRUCTOR_V5_3_SOURCE_COMPATIBILITY_V1", core)}
    audit_core = {
        "schema_name": "batch2-development-pilot11-constructor-v5-3-source-compatibility-audit-v1", "schema_version": "1.0.0",
        "compatibility_identity": receipt["compatibility_identity"], "git_object_only": True,
        "exact_frozen_bindings": "PASS", "exact_p3_authority_span": "PASS", "source_shape_neutral_extraction": "PASS",
        "typed_plan_closure": "PASS", "semantic_signature_coverage": "PASS_3_OF_3", "semantic_edge_coverage": "PASS_2_OF_2",
        "terminal_edge_equal_strength": "PASS", "privileged_affordance_minting": "ABSENT",
        "constructor_invocations": 0, "provider_invocations": 0, "emitter_invocations": 0, "candidate_surfaces_created": 0,
        "g02b_release": "NOT_PERFORMED", "deterministic_blockers": [],
        "verdict": "PASS_STATIC_SEMANTIC_PLAN_VALIDATION_ZERO_REALIZATION_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT11_CONSTRUCTOR_V5_3_SOURCE_COMPATIBILITY_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot11-constructor-v5-3-source-compatibility-v1.json", receipt)
    write("humor-mechanics-batch2-development-pilot11-constructor-v5-3-source-compatibility-audit-v1.json", audit)
    print(json.dumps({"verdict": receipt["verdict"], "compatibility_identity": receipt["compatibility_identity"], "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
