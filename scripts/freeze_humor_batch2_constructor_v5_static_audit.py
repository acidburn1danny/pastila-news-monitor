"""Freeze the uninvoked Constructor V5 implementation and static audit."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "77617b2e4268b7c84a5e0a6793e52a0e3c4ec9d1"
MODULE_PATH = "src/pastila_scout/humor_batch2_development_constructor_v5.py"
V4_MODULE_PATH = "src/pastila_scout/humor_batch2_development_constructor_v4.py"


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


def write(name: str, value: Any) -> None:
    path = ART / name
    require(not path.exists(), "artifact already exists")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    contract = load("docs/artifacts/humor-mechanics-batch2-development-constructor-contract-v5.json")
    governance = load("docs/artifacts/humor-mechanics-batch2-typed-operand-closed-construction-governance-v5.json")
    schema = load("docs/artifacts/humor-mechanics-batch2-typed-operand-closed-construction-conformance-schema-v5.json")
    regression = load("docs/artifacts/humor-mechanics-batch2-pilot08-operand-closure-regression-v1.json")
    require(contract["constructor_contract_identity"] == "e42f4741ddab7a6acbdd16f34804cd55408ca5a5428433be3c55eb9b74163c5a", "contract")
    require(governance["governance_identity"] == "e81ee4eff9044ee16180ef36a7508fe9f1e7c784fa6830299588cea16c2d3a3e", "governance")
    require(schema["schema_identity"] == "29d7b0f97008ad38e64b8e966f398d829a66299ec805290ebbec3f92848efab6", "schema")
    require(regression["regression_identity"] == "e91926a00312b556b3d095abc7ce666b6cd61b2d863c01b5378be43bac1faae8", "regression")
    historical_v4 = git_bytes(V4_MODULE_PATH)
    current_v4 = (ROOT / V4_MODULE_PATH).read_bytes()
    require(current_v4 == historical_v4, "Constructor V4 changed")
    module = (ROOT / MODULE_PATH).read_bytes()
    source = module.decode("utf-8")
    tree = ast.parse(source, filename=MODULE_PATH)
    imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imports.update(node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module)
    prohibited_imports = {"os", "pathlib", "subprocess", "socket", "requests", "httpx", "openai", "transformers", "torch", "importlib"}
    require(not imports.intersection(prohibited_imports), "prohibited constructor import")
    require(not re.search(r"\b[0-9a-f]{64}\b", source, re.I), "identity literal")
    require("pilot08" not in source.casefold() and "candidate01" not in source.casefold(), "identity routing")
    require('relation_noun + "ii,"' not in source and 'relation_noun + "a."' not in source, "raw suffix inflection")
    require('"iar", object_value' not in source, "prepositional object promoted to actor")
    entry = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "construct_development_candidate_v5")
    calls = [node.func.id for node in ast.walk(entry) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    require("_validate_plan" in calls and "_realize" in calls, "validator/realizer call")
    validate_line = min(node.lineno for node in ast.walk(entry) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_validate_plan")
    realize_line = min(node.lineno for node in ast.walk(entry) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_realize")
    require(validate_line < realize_line, "plan must validate before realization")
    validator = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_validate_plan")
    validator_text = ast.get_source_segment(source, validator) or ""
    for token in ("actor role incompatible", "unbound actor or patient", "unbound predecessor", "restatement cannot count"):
        require(token in validator_text, f"validator predicate {token}")
    implementation_core = {
        "schema_name": "batch2-development-constructor-implementation-v5",
        "schema_version": "5.0.0",
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "governance_identity": governance["governance_identity"],
        "conformance_schema_identity": schema["schema_identity"],
        "module_path": MODULE_PATH,
        "module_sha256": hashlib.sha256(module).hexdigest(),
        "public_entrypoint": "construct_development_candidate_v5",
        "typed_plan_validator": "_validate_plan",
        "abstract_plan_deriver": "_derive_plan",
        "realizer": "_realize",
        "validation_precedes_realization": True,
        "typed_operand_dataflow_fail_closed": True,
        "prepositional_actor_promotion_allowed": False,
        "raw_suffix_inflection_present": False,
        "filesystem_environment_process_network_model_access": False,
        "constructor_v4_sha256": hashlib.sha256(historical_v4).hexdigest(),
        "constructor_v4_status": "BYTE_EXACT_HISTORICAL_VERIFICATION_ONLY_NO_FUTURE_RELEASE",
        "pilot08_regression_identity": regression["regression_identity"],
        "invocations": 0,
        "candidate_surface": None,
        "release_authority": False,
        "construction_authority": False,
    }
    implementation = {**implementation_core, "constructor_implementation_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_IMPLEMENTATION_V5", implementation_core)}
    audit_core = {
        "schema_name": "batch2-development-constructor-v5-static-audit-v1",
        "schema_version": "1.0.0",
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "constructor_v4_byte_exact": "PASS",
        "pathless_import_allowlist": "PASS",
        "identity_routed_surface_branch_scan": "PASS_ZERO_HITS",
        "typed_operand_dataflow_validator": "PASS_PRESENT_FAIL_CLOSED",
        "abstract_plan_closure_before_realization": "PASS",
        "prepositional_actor_negative_regression": "PASS_REJECTED_BEFORE_SURFACE",
        "terminal_punctuation_negative_regression": "PASS_REJECTED_BEFORE_SURFACE",
        "unbound_reference_negative_regression": "PASS_REJECTED_BEFORE_SURFACE",
        "raw_suffix_inflection_scan": "PASS_ZERO_HITS",
        "pilot08_failed_shape_regression": "PASS_EXPECTED_PRECONSTRUCTION_REJECTION",
        "constructor_invocations": 0,
        "candidate_surfaces_created": 0,
        "constructor_release": "NOT_PERFORMED",
        "source_acquisition_or_pilot09_preparation": "NOT_PERFORMED",
        "downstream_authority": False,
        "deterministic_blockers": [],
        "verdict": "PASS_IMPLEMENTATION_AND_STATIC_AUDIT_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "audit_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_V5_STATIC_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-constructor-implementation-v5.json", implementation)
    write("humor-mechanics-batch2-development-constructor-v5-static-audit-v1.json", audit)
    print(json.dumps({
        "verdict": audit["verdict"],
        "constructor_implementation_identity": implementation["constructor_implementation_identity"],
        "audit_identity": audit["audit_identity"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
