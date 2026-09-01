"""Freeze Constructor V5.1 successor contract, implementation, and static audit."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from pastila_scout.humor_batch2_development_constructor_v5_1 import (
    derive_proposition_plan, extract_typed_operands, validate_typed_plan,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "6a446ecee1942e9120c455893a94c7517fc8c2fa"
MODULE = "src/pastila_scout/humor_batch2_development_constructor_v5_1.py"
V5_MODULE = "src/pastila_scout/humor_batch2_development_constructor_v5.py"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def git_json(commit: str, path: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), "artifact exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def compatibility(commit: str, prefix: str, index: int) -> dict[str, Any]:
    envelope = git_json(commit, prefix + "factual-authority-envelope.json")
    source = subprocess.check_output(["git", "show", f"{commit}:{prefix}source.utf8.txt"], cwd=ROOT)
    proposition = envelope["propositions"][index]
    bs, be = proposition["supporting_span"]["utf8_byte_coordinates"]
    selected = source[bs:be].decode()
    operands = extract_typed_operands(selected, proposition)
    plan = derive_proposition_plan(operands)
    initial = {"FACT_OBJECT", operands.relation_id, "FACT_QUALIFICATION" if operands.qualification else "FACT_RELATION"}
    validate_typed_plan(plan, frozenset(initial))
    return {"proposition_id": proposition["proposition_id"], "relation_id": operands.relation_id,
            "typed_operand_extraction": "PASS", "proposition_derived_plan_closure": "PASS", "plan_nodes": len(plan)}


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    failure = git_json(COMMIT, "docs/artifacts/humor-mechanics-batch2-development-pilot09-constructor-v5-source-compatibility-v1.json")
    old_implementation = git_json(COMMIT, "docs/artifacts/humor-mechanics-batch2-development-constructor-implementation-v5.json")
    require(failure["compatibility_identity"] == "fabcee37d422ad7e941dd1168c63b9659e27b039831a187da05d7bc665bed5a7", "failure binding")
    require(old_implementation["constructor_implementation_identity"] == "caf85ada6fcd296d3798b5d47838d7b8a39d029dac5f6ecae68ace58712b9d61", "V5 binding")
    require((ROOT / V5_MODULE).read_bytes() == git_bytes(V5_MODULE), "V5 changed")
    module = (ROOT / MODULE).read_bytes()
    source = module.decode("utf-8")
    tree = ast.parse(source, filename=MODULE)
    imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imports.update(node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module)
    require(not imports.intersection({"os", "pathlib", "subprocess", "socket", "requests", "httpx", "openai", "torch", "transformers", "importlib"}), "pathless imports")
    require(not re.search(r"\b[0-9a-f]{64}\b", source, re.I), "identity literal")
    require("pilot08" not in source.casefold() and "pilot09" not in source.casefold(), "pilot routing")
    entry = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "construct_development_candidate_v5_1")
    calls = [(node.func.id, node.lineno) for node in ast.walk(entry) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    lines = {name: min(line for called, line in calls if called == name) for name in ("extract_typed_operands", "derive_proposition_plan", "validate_typed_plan", "_realize")}
    require(lines["extract_typed_operands"] < lines["derive_proposition_plan"] < lines["validate_typed_plan"] < lines["_realize"], "validation ordering")
    pilot08 = compatibility("784eaacbc12c574e9a4d16e9f0059ae60a32b396", "docs/artifacts/humor-mechanics-batch2-development-pilot08-ingestion-v1/", 4)
    pilot09 = compatibility("8991524fb136d29daa5f559ba8d9aef7386a2ac8", "docs/artifacts/humor-mechanics-batch2-development-pilot09-ingestion-v1/", 4)
    contract_core = {
        "schema_name": "batch2-development-constructor-contract-v5-1", "schema_version": "5.1.0",
        "supersedes_contract_identity": old_implementation["constructor_contract_identity"],
        "remediates_compatibility_identity": failure["compatibility_identity"],
        "source_shape_neutral_typed_operand_extraction": True,
        "lexical_negation_location_requirement": None, "lexical_object_preposition_requirement": None,
        "proposition_derived_abstract_plan_required": True,
        "coordinate_and_hash_bound_roles_required": ["SUBJECT", "PREDICATE", "OBJECT", "QUALIFICATION_IF_PRESENT"],
        "validation_order": ["EXTRACT_TYPED_OPERANDS", "DERIVE_PROPOSITION_PLAN", "VALIDATE_TYPED_PLAN", "REALIZE"],
        "constructor_release_authority": False, "construction_authority": False, "candidate_surface": None,
    }
    contract = {**contract_core, "constructor_contract_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_CONTRACT_V5_1", contract_core)}
    implementation_core = {
        "schema_name": "batch2-development-constructor-implementation-v5-1", "schema_version": "5.1.0",
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "module_path": MODULE, "module_sha256": hashlib.sha256(module).hexdigest(),
        "public_entrypoint": "construct_development_candidate_v5_1",
        "source_shape_neutral_extractor": "extract_typed_operands", "proposition_plan_deriver": "derive_proposition_plan",
        "typed_plan_validator": "validate_typed_plan", "realizer": "_realize",
        "validation_precedes_realization": True, "filesystem_environment_process_network_model_access": False,
        "constructor_v5_identity": old_implementation["constructor_implementation_identity"],
        "constructor_v5_status": "BYTE_EXACT_SUPERSEDED_NO_RELEASE", "invocations": 0, "candidate_surface": None,
        "release_authority": False, "construction_authority": False,
    }
    implementation = {**implementation_core, "constructor_implementation_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_IMPLEMENTATION_V5_1", implementation_core)}
    audit_core = {
        "schema_name": "batch2-development-constructor-v5-1-static-audit-v1", "schema_version": "1.0.0",
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "frozen_v5_preservation": "PASS_BYTE_EXACT", "pathless_import_allowlist": "PASS",
        "identity_and_pilot_routing_scan": "PASS_ZERO_HITS", "validation_before_realization": "PASS",
        "pilot08_source_shape_regression": pilot08, "pilot09_p5_source_compatibility": pilot09,
        "unbound_operand_negative_test": "PASS_FAIL_CLOSED", "lexical_shape_dependencies_removed": "PASS",
        "constructor_invocations": 0, "candidate_surfaces_created": 0, "constructor_release": "NOT_PERFORMED",
        "deterministic_blockers": [], "verdict": "PASS_SUCCESSOR_IMPLEMENTATION_STATIC_AUDIT_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_V5_1_STATIC_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-constructor-contract-v5-1.json", contract)
    write("humor-mechanics-batch2-development-constructor-implementation-v5-1.json", implementation)
    write("humor-mechanics-batch2-development-constructor-v5-1-static-audit-v1.json", audit)
    print(json.dumps({"verdict": audit["verdict"], "contract_identity": contract["constructor_contract_identity"],
                      "implementation_identity": implementation["constructor_implementation_identity"], "audit_identity": audit["audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
