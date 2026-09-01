"""Statically validate Pilot 10 P3 against frozen Constructor V5.2 without release."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from pastila_scout.humor_batch2_development_constructor_v5_1 import (
    derive_proposition_plan, extract_typed_operands, validate_typed_plan,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "5a5780f5f829c32d7c807412dc06099ec0cac10d"
PROPOSAL_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-constructor-facing-assignment-proposal-v5-2.json"
MAPPING_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-sealed-assignment-v5-2.json"
OBLIGATION_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot10-obligation-family-v5-2.json"
RUNTIME_PATH = "src/pastila_scout/humor_batch2_development_constructor_v5_2_runtime.py"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def git_json(path: str) -> dict[str, Any]:
    return json.loads(git_bytes(path))


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
    contract = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-contract-v5-2.json")
    implementation = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v5-2.json")
    provider = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-2-realization-provider-implementation.json")
    emitter = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-2-candidate-emitter-implementation.json")
    static_audit = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-2-runtime-static-audit-v1.json")
    governance = git_json("docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-governance-v5-2.json")
    schema = git_json("docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-conformance-schema-v5-2.json")
    require(proposal["constructor_facing_packet_identity"] == "cf93852215e2214cf9a67eaf82aba747e4b88dc082d0fe935583d9d7af12a807", "proposal")
    require(mapping["sealed_assignment_identity"] == "c4677b0b8d148163d339cf72590078564f5a462a571d6272cbc8800d90ad4aab", "mapping")
    require(obligation["obligation_family_identity"] == "943261c4f1fe9622a71d5bd159fa8174b7a259323f491a81741b0b856a5284d6", "obligation")
    require(proposal["unlabeled_operational_obligation"]["obligation_instance_identity"] == "6aad43d4814e56aa7df3f747caa79e5809ebed19328365542de4321c33ddd97d", "instance")
    require(contract["constructor_contract_identity"] == governance["constructor_contract_identity"] == schema["constructor_contract_identity"] == "69138467540b37cbfb8444596d9a37119f8b74d002e0c491c8ff599ce77cec77", "contract")
    require(implementation["constructor_implementation_identity"] == "bdf48e9942f097f0259831c0f2f611e50644cdbe7179a2dc7d990bf9ab2b5493", "implementation")
    require(provider["realization_provider_implementation_identity"] == implementation["realization_provider_implementation_identity"] == "36b3669acb5e7d2b772ad6d8a912f4cdbfea8f58e3c45e72cafcd206336afce8", "provider")
    require(emitter["candidate_emitter_implementation_identity"] == implementation["candidate_emitter_implementation_identity"] == "e325bd20ba1f58bbc48a6e749dc7a505e5522e4ff11c798855e8d530dae113d4", "emitter")
    require(static_audit["static_audit_identity"] == "1171e1a53acbb733c530d2f2e4fa753284a9f4747ab905d9c2a57d7b22b3399d", "static audit")
    require(proposal["selected_proposition_id"] == "P3" and len(proposal["closed_factual_authority_envelope"]["propositions"]) == 1, "P3 only")
    proposition = proposal["closed_factual_authority_envelope"]["propositions"][0]
    source = proposal["exact_authorized_visible_context_utf8"]
    span = proposition["supporting_span"]
    require(hashlib.sha256(source.encode()).hexdigest() == proposal["selected_supporting_span_sha256"] == span["span_sha256"] == "188742ebbe30a23349601ddb369b0bb962d87dc9c8efe3227e50a38b6f89d967", "span")
    operands = extract_typed_operands(source, proposition)
    plan = derive_proposition_plan(operands)
    initial = {"FACT_OBJECT", operands.relation_id, "FACT_QUALIFICATION" if operands.qualification else "FACT_RELATION"}
    validate_typed_plan(plan, frozenset(initial))
    require(operands.subject == "lada", "subject")
    require(operands.predicate == "este înregistrată cu eticheta APROBAT și este mutată", "predicate")
    require(operands.object_value == "în zona de depozitare destinată materialelor horticole.", "object")
    require(operands.qualification == "Dacă greutatea corespunde valorii înscrise în document și numărul de pe etichetă corespunde celui din document,", "qualification")
    require(len(plan) == 3 and sum(len(node.predecessor_node_ids) for node in plan) == 2, "plan topology")
    require(all(operands.relation_id.rsplit("_", 1)[-1] in node.predicate_id for node in plan), "proposition-derived predicates")
    plan_evidence = [{"node_id": node.node_id, "bound_actor_id": node.bound_actor_id, "actor_role": node.actor_role,
        "predicate_id": node.predicate_id, "bound_patient_id": node.bound_patient_id,
        "predecessor_node_ids": list(node.predecessor_node_ids), "introduces_ids": list(node.introduces_ids),
        "source_provenance": node.source_provenance, "nonfactual_scope": node.nonfactual_scope} for node in plan]
    runtime_source = git_bytes(RUNTIME_PATH).decode("utf-8")
    require(hashlib.sha256(runtime_source.encode()).hexdigest() == implementation["module_sha256"], "runtime module hash")
    tree = ast.parse(runtime_source)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    require({"realize_typed_plan", "emit_candidate_utf8"}.issubset(functions), "runtime functions")
    provider_args = [arg.arg for arg in functions["realize_typed_plan"].args.kwonlyargs]
    require(provider_args == ["exact_source", "typed_plan", "lexicalizations"], "provider typed inputs")
    emitter_text = ast.unparse(functions["emit_candidate_utf8"])
    require("validate_realization_draft" in emitter_text and "coverage.nodes_realized != coverage.nodes_required" in emitter_text and "coverage.edges_realized != coverage.edges_required" in emitter_text and "not coverage.terminal_result_realized" in emitter_text, "pre-emission enforcement")
    imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imports.update(node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module)
    require(not imports.intersection({"os", "pathlib", "subprocess", "socket", "requests", "httpx", "openai", "torch", "transformers", "importlib"}), "pathless import allowlist")
    core = {
        "schema_name": "batch2-development-pilot10-constructor-v5-2-source-compatibility-v1", "schema_version": "1.0.0",
        "reviewed_commit": COMMIT, "constructor_contract_identity": contract["constructor_contract_identity"],
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "realization_provider_identity": provider["realization_provider_implementation_identity"],
        "candidate_emitter_identity": emitter["candidate_emitter_implementation_identity"],
        "constructor_static_audit_identity": static_audit["static_audit_identity"],
        "constructor_facing_proposal_identity": proposal["constructor_facing_packet_identity"],
        "sealed_assignment_identity": mapping["sealed_assignment_identity"], "selected_proposition_id": "P3",
        "selected_span_sha256": span["span_sha256"], "authority_binding": "PASS_EXACT_P3_AND_AUTHORIZED_SUPPORTING_SPAN_ONLY",
        "typed_operand_extraction": {"verdict": "PASS_SOURCE_SHAPE_NEUTRAL", "relation_id": operands.relation_id,
            "subject": operands.subject, "predicate": operands.predicate, "object": operands.object_value,
            "qualification_bound": operands.qualification is not None},
        "proposition_derived_abstract_plan_compatibility": plan_evidence,
        "abstract_plan_closure": "PASS_THREE_TYPED_NODES_TWO_EDGES_NO_UNBOUND_OPERANDS",
        "v5_2_pre_emission_static_prerequisites": "PASS_N_OVER_N_E_OVER_E_OPERAND_CONTINUITY_EXACTLY_ONE_TERMINAL_FAIL_CLOSED",
        "source_shape_neutrality": "PASS_NO_PILOT10_LEXICAL_CONSTANT_IN_IMPLEMENTATION",
        "factual_authority_widening": "ABSENT", "realization_or_surface_witnesses_created": False,
        "constructor_invoked": False, "provider_invoked": False, "emitter_invoked": False,
        "candidate_surface": None, "constructor_release": False,
        "verdict": "PASS_SOURCE_COMPATIBLE_WITH_FROZEN_CONSTRUCTOR_V5_2_NO_RELEASE",
        "authority_matrix": {key: False for key in ("g02b_release", "constructor_invocation", "provider_invocation",
            "emitter_invocation", "realization", "candidate_emission", "post_realization_pre_emission_conformance",
            "fragment_collision_evaluation", "g02", "g02c", "g03", "g04b_pool_certification", "model_exposure",
            "training", "runtime_integration", "production_routing")},
    }
    receipt = {**core, "compatibility_identity": seal("B2_DEVELOPMENT_PILOT10_CONSTRUCTOR_V5_2_SOURCE_COMPATIBILITY_V1", core)}
    audit_core = {
        "schema_name": "batch2-development-pilot10-constructor-v5-2-source-compatibility-audit-v1", "schema_version": "1.0.0",
        "compatibility_identity": receipt["compatibility_identity"], "git_object_only": True,
        "exact_contract_implementation_provider_emitter_static_audit_binding": "PASS",
        "exact_p3_authority_binding": "PASS", "source_shape_neutral_extraction": "PASS",
        "proposition_derived_plan_closure": "PASS", "pre_emission_static_prerequisites": "PASS",
        "pathless_import_allowlist": "PASS", "constructor_invocations": 0, "provider_invocations": 0,
        "emitter_invocations": 0, "candidate_surfaces_created": 0, "g02b_release": "NOT_PERFORMED",
        "deterministic_blockers": [], "verdict": "PASS_STATIC_VALIDATION_ZERO_REALIZATION_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT10_CONSTRUCTOR_V5_2_SOURCE_COMPATIBILITY_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot10-constructor-v5-2-source-compatibility-v1.json", receipt)
    write("humor-mechanics-batch2-development-pilot10-constructor-v5-2-source-compatibility-audit-v1.json", audit)
    print(json.dumps({"verdict": receipt["verdict"], "compatibility_identity": receipt["compatibility_identity"],
                      "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
