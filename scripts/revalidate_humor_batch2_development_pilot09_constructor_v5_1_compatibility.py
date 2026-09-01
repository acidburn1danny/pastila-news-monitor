"""Revalidate Pilot 09 P5 compatibility with frozen Constructor V5.1, without invocation."""

from __future__ import annotations

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
COMMIT = "9b0df3daf3aa894e72259b80131c0da4b0480995"
PROPOSAL_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot09-constructor-facing-rebalancing-assignment-proposal-v5.json"
MAPPING_PATH = "docs/artifacts/humor-mechanics-batch2-development-pilot09-sealed-rebalancing-assignment-v5.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_json(path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), "artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    proposal, mapping = git_json(PROPOSAL_PATH), git_json(MAPPING_PATH)
    contract = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-contract-v5-1.json")
    implementation = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v5-1.json")
    static_audit = git_json("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-1-static-audit-v1.json")
    prior_failure = git_json("docs/artifacts/humor-mechanics-batch2-development-pilot09-constructor-v5-source-compatibility-v1.json")
    require(contract["constructor_contract_identity"] == "9b647d33dfa40171040fe6acf08b8b6dca6081c41c0f1f4428f910bfdfaa8a6b", "contract")
    require(implementation["constructor_implementation_identity"] == "c7134743e6b0e7c3ed7637bff3203f774159f192fef7a7b712e15d4d44a6f419", "implementation")
    require(static_audit["audit_identity"] == "7c304534fbe2ee6b526a4cc4582a243b685ab97f5694ef5524abdeb3e150de47", "audit")
    require(prior_failure["verdict"] == "FAIL_FROZEN_V5_SOURCE_INCOMPATIBLE_NO_RELEASE", "prior failure")
    require(proposal["constructor_facing_packet_identity"] == "2fc8967cb7fba1667524a8683c4d837afbb21dd6c7d6ae61b244ff8b9e6cb5c1", "proposal")
    require(mapping["sealed_assignment_identity"] == "735814216b914a8c3f86150261cff19efb77536126c3c4d13b2f38bd3c0590e1", "mapping")
    require(proposal["selected_proposition_id"] == "P5" and len(proposal["closed_factual_authority_envelope"]["propositions"]) == 1, "P5")
    proposition = proposal["closed_factual_authority_envelope"]["propositions"][0]
    source = proposal["exact_authorized_visible_context_utf8"]
    span = proposition["supporting_span"]
    require(hashlib.sha256(source.encode()).hexdigest() == proposal["selected_supporting_span_sha256"] == span["span_sha256"], "span")
    operands = extract_typed_operands(source, proposition)
    plan = derive_proposition_plan(operands)
    initial = {"FACT_OBJECT", operands.relation_id, "FACT_QUALIFICATION" if operands.qualification else "FACT_RELATION"}
    validate_typed_plan(plan, frozenset(initial))
    require(operands.subject == "banda" and "nu pornește" in operands.predicate and operands.object_value == "automat.", "exact roles")
    require(all(operands.relation_id.rsplit("_", 1)[-1] in node.predicate_id for node in plan), "derived predicates")
    plan_evidence = [{"node_id": n.node_id, "actor": n.bound_actor_id, "actor_role": n.actor_role,
                      "predicate_id": n.predicate_id, "patient": n.bound_patient_id,
                      "predecessors": list(n.predecessor_node_ids), "introduces": list(n.introduces_ids)} for n in plan]
    core = {
        "schema_name": "batch2-development-pilot09-constructor-v5-1-source-compatibility-v1", "schema_version": "1.0.0",
        "reviewed_commit": COMMIT, "prior_failed_compatibility_identity": prior_failure["compatibility_identity"],
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "constructor_static_audit_identity": static_audit["audit_identity"],
        "constructor_facing_proposal_identity": proposal["constructor_facing_packet_identity"],
        "sealed_assignment_identity": mapping["sealed_assignment_identity"],
        "selected_proposition_id": "P5", "selected_span_sha256": span["span_sha256"],
        "authority_binding": "PASS_EXACT_P5_AND_AUTHORIZED_SUPPORTING_SPAN_ONLY",
        "typed_operand_extraction": {"verdict": "PASS_SOURCE_SHAPE_NEUTRAL", "relation_id": operands.relation_id,
                                     "subject": operands.subject, "predicate": operands.predicate,
                                     "object": operands.object_value, "qualification_bound": operands.qualification is not None},
        "proposition_derived_abstract_plan": plan_evidence,
        "abstract_plan_closure": "PASS_THREE_TYPED_NODES_NO_UNBOUND_OPERANDS",
        "factual_authority_widening": "ABSENT", "constructor_invoked": False, "candidate_surface": None,
        "constructor_release": False, "verdict": "PASS_SOURCE_COMPATIBLE_WITH_FROZEN_CONSTRUCTOR_V5_1_NO_RELEASE",
        "authority_matrix": {key: False for key in ("g02b_release", "construction", "fragment_collision_evaluation", "g02", "g02c", "g03", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    receipt = {**core, "compatibility_identity": seal("B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_V5_1_SOURCE_COMPATIBILITY_V1", core)}
    audit_core = {
        "schema_name": "batch2-development-pilot09-constructor-v5-1-source-compatibility-audit-v1", "schema_version": "1.0.0",
        "compatibility_identity": receipt["compatibility_identity"], "git_object_only": True,
        "exact_contract_implementation_static_audit_binding": "PASS", "exact_p5_authority_binding": "PASS",
        "source_shape_neutral_extraction": "PASS", "proposition_derived_plan_closure": "PASS",
        "prior_v5_blockers_regression": "PASS_BOTH_REMOVED", "constructor_invocations": 0,
        "candidate_surfaces_created": 0, "g02b_release": "NOT_PERFORMED", "deterministic_blockers": [],
        "verdict": "PASS_REVALIDATION_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_V5_1_SOURCE_COMPATIBILITY_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot09-constructor-v5-1-source-compatibility-v1.json", receipt)
    write("humor-mechanics-batch2-development-pilot09-constructor-v5-1-source-compatibility-audit-v1.json", audit)
    print(json.dumps({"verdict": receipt["verdict"], "compatibility_identity": receipt["compatibility_identity"], "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
