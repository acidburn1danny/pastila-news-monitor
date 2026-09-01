"""Source-only compatibility/static-plan validation for Pilot 09 and frozen Constructor V5."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "ef0e5964c14719b16ebaa9cc2843c86d1490de4c"
MODULE = "src/pastila_scout/humor_batch2_development_constructor_v5.py"
IMPLEMENTATION_ID = "caf85ada6fcd296d3798b5d47838d7b8a39d029dac5f6ecae68ace58712b9d61"
PROPOSAL = "docs/artifacts/humor-mechanics-batch2-development-pilot09-constructor-facing-rebalancing-assignment-proposal-v5.json"
MAPPING = "docs/artifacts/humor-mechanics-batch2-development-pilot09-sealed-rebalancing-assignment-v5.json"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def load(path: str) -> dict[str, Any]:
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
    proposal, mapping = load(PROPOSAL), load(MAPPING)
    implementation = load("docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v5.json")
    static_audit = load("docs/artifacts/humor-mechanics-batch2-development-constructor-v5-static-audit-v1.json")
    module = git_bytes(MODULE)
    source = module.decode("utf-8")
    tree = ast.parse(source)
    require(implementation["constructor_implementation_identity"] == IMPLEMENTATION_ID, "implementation")
    require(hashlib.sha256(module).hexdigest() == implementation["module_sha256"], "module")
    require(static_audit["verdict"] == "PASS_IMPLEMENTATION_AND_STATIC_AUDIT_ZERO_CONSTRUCTION_NO_RELEASE", "static audit")
    require(proposal["constructor_facing_packet_identity"] == "2fc8967cb7fba1667524a8683c4d837afbb21dd6c7d6ae61b244ff8b9e6cb5c1", "proposal")
    require(mapping["sealed_assignment_identity"] == "735814216b914a8c3f86150261cff19efb77536126c3c4d13b2f38bd3c0590e1", "mapping")
    require(proposal["selected_proposition_id"] == "P5" and len(proposal["closed_factual_authority_envelope"]["propositions"]) == 1, "P5 only")
    proposition = proposal["closed_factual_authority_envelope"]["propositions"][0]
    exact = proposal["exact_authorized_visible_context_utf8"]
    span = proposition["supporting_span"]
    require(hashlib.sha256(exact.encode()).hexdigest() == span["span_sha256"], "span")
    cs = span["character_coordinates"][0]
    def component(name: str) -> str:
        item = proposition[name]
        start, end = item["character_coordinates"]
        return exact[start - cs:end - cs]
    subject, predicate, object_value = component("subject"), component("predicate"), component("object")
    qualification = component("qualification")
    current_shape = bool(qualification) and "nu" in subject.casefold() and "pentru" in object_value.casefold()
    require("_validate_plan" in source and "_derive_plan" in source, "validators")
    plan_function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_derive_plan")
    plan_source = ast.get_source_segment(source, plan_function) or ""
    pilot09_semantics = all(token in (subject + predicate + object_value + qualification).casefold() for token in ("banda", "nu pornește", "automat"))
    plan_matches = "AUTOMATIC_NONSTART" in plan_source and "SENSOR_NONDETECTION" in plan_source
    blockers = []
    if not current_shape:
        blockers.append("FROZEN_V5_PREFLIGHT_HARDCODES_PILOT08_SUBJECT_OBJECT_LEXICAL_SHAPE")
    if not plan_matches:
        blockers.append("FROZEN_V5_ABSTRACT_PLAN_MODELS_RETURN_REAPPLICATION_CHECK_NOT_P5_TRIGGER_NONSTART")
    require(pilot09_semantics and blockers, "expected deterministic incompatibility")
    core = {
        "schema_name": "batch2-development-pilot09-constructor-v5-source-compatibility-v1",
        "schema_version": "1.0.0",
        "reviewed_commit": COMMIT,
        "constructor_implementation_identity": IMPLEMENTATION_ID,
        "constructor_module_sha256": implementation["module_sha256"],
        "constructor_static_audit_identity": static_audit["audit_identity"],
        "constructor_facing_proposal_identity": proposal["constructor_facing_packet_identity"],
        "sealed_assignment_identity": mapping["sealed_assignment_identity"],
        "selected_proposition_id": "P5",
        "selected_span_sha256": span["span_sha256"],
        "typed_component_binding": {"subject": subject, "predicate": predicate, "object": object_value, "qualification_present": bool(qualification)},
        "typed_operand_dataflow_validator_present": True,
        "abstract_plan_validator_precedes_realization": implementation["validation_precedes_realization"],
        "source_shape_accepted_by_frozen_preflight": current_shape,
        "abstract_plan_semantically_closes_over_p5": plan_matches,
        "constructor_invoked": False,
        "candidate_surface": None,
        "constructor_release": False,
        "deterministic_blockers": blockers,
        "verdict": "FAIL_FROZEN_V5_SOURCE_INCOMPATIBLE_NO_RELEASE",
        "authority_matrix": {key: False for key in ("constructor_release", "construction", "fragment_collision_evaluation", "g02", "g02c", "g03", "g04b_pool_certification", "model_exposure", "training", "runtime_integration", "production_routing")},
    }
    receipt = {**core, "compatibility_identity": seal("B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_V5_SOURCE_COMPATIBILITY_V1", core)}
    audit_core = {
        "schema_name": "batch2-development-pilot09-constructor-v5-source-compatibility-audit-v1",
        "schema_version": "1.0.0",
        "compatibility_identity": receipt["compatibility_identity"],
        "git_object_only": True,
        "exact_proposal_and_p5_binding": "PASS",
        "frozen_implementation_binding": "PASS",
        "typed_operand_validator_static_presence": "PASS",
        "abstract_plan_closure_for_p5": "FAIL_SEMANTIC_MISMATCH",
        "constructor_invocations": 0,
        "candidate_surfaces_created": 0,
        "repair_performed": False,
        "repair_boundary": "SEPARATE_SUCCESSOR_IMPLEMENTATION_AUTHORIZATION_REQUIRED",
        "verdict": "PASS_FAIL_CLOSED_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_PILOT09_CONSTRUCTOR_V5_SOURCE_COMPATIBILITY_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-pilot09-constructor-v5-source-compatibility-v1.json", receipt)
    write("humor-mechanics-batch2-development-pilot09-constructor-v5-source-compatibility-audit-v1.json", audit)
    print(json.dumps({"verdict": receipt["verdict"], "compatibility_identity": receipt["compatibility_identity"], "audit_identity": audit["audit_identity"], "blockers": blockers}, sort_keys=True))


if __name__ == "__main__":
    main()
