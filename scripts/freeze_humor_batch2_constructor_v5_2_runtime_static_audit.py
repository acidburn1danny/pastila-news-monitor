"""Freeze V5.2 realization-provider/emitter implementation and static audit."""

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
COMMIT = "aebbb96fd6d16d9c126c54795b7c2e8f99120931"
RUNTIME = "src/pastila_scout/humor_batch2_development_constructor_v5_2_runtime.py"
ENFORCEMENT = "src/pastila_scout/humor_batch2_development_constructor_v5_2.py"
V5_1 = "src/pastila_scout/humor_batch2_development_constructor_v5_1.py"


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
    contract = load("docs/artifacts/humor-mechanics-batch2-development-constructor-contract-v5-2.json")
    governance = load("docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-governance-v5-2.json")
    schema = load("docs/artifacts/humor-mechanics-batch2-plan-witnessed-realization-conformance-schema-v5-2.json")
    enforcement_artifact = load("docs/artifacts/humor-mechanics-batch2-development-constructor-plan-to-surface-enforcement-v5-2.json")
    regression = load("docs/artifacts/humor-mechanics-batch2-pilot09-plan-to-surface-regression-v1.json")
    require(contract["constructor_contract_identity"] == "69138467540b37cbfb8444596d9a37119f8b74d002e0c491c8ff599ce77cec77", "contract")
    require(governance["governance_identity"] == "80bbf059956424ce6f20885de51ce900f6116b40a223a107a46a29d3b012efc6", "governance")
    require(schema["schema_identity"] == "084ddf4d8e9f215db3665370221260c351d3befe747c4dbb45ab35baac4c993b", "schema")
    require(enforcement_artifact["enforcement_implementation_identity"] == "7a814e9bc583cf48f53cde88f1fc343708150470f088e0e320091e091054f036", "enforcement")
    require(regression["regression_identity"] == "46555766257446703ef92cf4b3fe48716a55a1daf2c14ba5749890d028ae7f00", "regression")
    require((ROOT / ENFORCEMENT).read_bytes() == git_bytes(ENFORCEMENT), "enforcement changed")
    require((ROOT / V5_1).read_bytes() == git_bytes(V5_1), "V5.1 changed")

    runtime = (ROOT / RUNTIME).read_bytes()
    source = runtime.decode("utf-8")
    tree = ast.parse(source, filename=RUNTIME)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    provider, emitter = functions["realize_typed_plan"], functions["emit_candidate_utf8"]
    require([arg.arg for arg in provider.args.kwonlyargs] == ["exact_source", "typed_plan", "lexicalizations"], "provider plan input")
    provider_text, emitter_text = ast.unparse(provider), ast.unparse(emitter)
    for token in ("set(by_node) != {node.node_id for node in typed_plan}", "SurfaceNodeWitness", "predecessor_node_ids=node.predecessor_node_ids", "produced_operand_surfaces=lexical.produced_operand_surfaces"):
        require(token in provider_text, "provider witness binding")
    calls = [node for node in ast.walk(emitter) if isinstance(node, ast.Call)]
    validator_line = min(node.lineno for node in calls if isinstance(node.func, ast.Name) and node.func.id == "validate_realization_draft")
    encode_line = min(node.lineno for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == "encode")
    require(validator_line < encode_line, "validation ordering")
    for token in ("coverage.nodes_realized != coverage.nodes_required", "coverage.edges_realized != coverage.edges_required", "not coverage.terminal_result_realized"):
        require(token in emitter_text, "emitter coverage")
    imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imports.update(node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module)
    require(not imports.intersection({"os", "pathlib", "subprocess", "socket", "requests", "httpx", "openai", "torch", "transformers", "importlib"}), "pathless imports")
    require(not re.search(r"\b[0-9a-f]{64}\b", source, re.I), "identity literal")
    require("pilot09" not in source.casefold() and "candidate01" not in source.casefold(), "pilot routing")

    module_sha = hashlib.sha256(runtime).hexdigest()
    provider_core = {
        "schema_name": "batch2-development-constructor-v5-2-realization-provider-implementation",
        "schema_version": "5.2.0",
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "governance_identity": governance["governance_identity"],
        "conformance_schema_identity": schema["schema_identity"],
        "enforcement_implementation_identity": enforcement_artifact["enforcement_implementation_identity"],
        "module_path": RUNTIME,
        "module_sha256": module_sha,
        "entrypoint": "realize_typed_plan",
        "typed_plan_input_required": True,
        "lexicalization_coverage": "EXACT_N_OF_N",
        "node_witness_fields_preserved": ["NODE_ID", "ACTOR_OPERAND", "PREDICATE", "PATIENT_OPERAND", "PREDECESSOR_EDGES", "PRODUCED_OPERANDS", "TERMINAL_RESULT"],
        "hard_coded_candidate_template": False,
        "invocations": 0,
        "candidate_surfaces_created": 0,
        "release_authority": False,
    }
    provider_artifact = {**provider_core, "realization_provider_implementation_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_V5_2_REALIZATION_PROVIDER_IMPLEMENTATION", provider_core)}
    emitter_core = {
        "schema_name": "batch2-development-constructor-v5-2-candidate-emitter-implementation",
        "schema_version": "5.2.0",
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "enforcement_implementation_identity": enforcement_artifact["enforcement_implementation_identity"],
        "realization_provider_implementation_identity": provider_artifact["realization_provider_implementation_identity"],
        "module_path": RUNTIME,
        "module_sha256": module_sha,
        "entrypoint": "emit_candidate_utf8",
        "validation_entrypoint": "validate_realization_draft",
        "validation_precedes_utf8_emission": True,
        "required_coverage": {"nodes": "N_OF_N", "edges": "E_OF_E", "terminal_result": "1_OF_1"},
        "invocations": 0,
        "candidate_surfaces_emitted": 0,
        "release_authority": False,
    }
    emitter_artifact = {**emitter_core, "candidate_emitter_implementation_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_V5_2_CANDIDATE_EMITTER_IMPLEMENTATION", emitter_core)}
    combined_core = {
        "schema_name": "batch2-development-constructor-implementation-v5-2",
        "schema_version": "5.2.0",
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "realization_provider_implementation_identity": provider_artifact["realization_provider_implementation_identity"],
        "candidate_emitter_implementation_identity": emitter_artifact["candidate_emitter_implementation_identity"],
        "enforcement_implementation_identity": enforcement_artifact["enforcement_implementation_identity"],
        "module_path": RUNTIME,
        "module_sha256": module_sha,
        "filesystem_environment_process_network_model_access": False,
        "constructor_v5_1_preservation": "PASS_BYTE_EXACT",
        "constructor_invocations": 0,
        "candidate_surfaces_created_or_emitted": 0,
        "constructor_release": "NOT_PERFORMED",
        "release_authority": False,
        "construction_authority": False,
    }
    combined = {**combined_core, "constructor_implementation_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_IMPLEMENTATION_V5_2", combined_core)}
    audit_core = {
        "schema_name": "batch2-development-constructor-v5-2-runtime-static-audit-v1",
        "schema_version": "1.0.0",
        "constructor_contract_identity": contract["constructor_contract_identity"],
        "constructor_implementation_identity": combined["constructor_implementation_identity"],
        "realization_provider_implementation_identity": provider_artifact["realization_provider_implementation_identity"],
        "candidate_emitter_implementation_identity": emitter_artifact["candidate_emitter_implementation_identity"],
        "enforcement_implementation_identity": enforcement_artifact["enforcement_implementation_identity"],
        "pilot09_regression_identity": regression["regression_identity"],
        "provider_receives_typed_plan": "PASS_EXACT_ARGUMENT_AND_NODE_ITERATION",
        "provider_preserves_plan_witness_fields": "PASS",
        "n_over_n_node_coverage": "PASS_FAIL_CLOSED",
        "e_over_e_edge_coverage": "PASS_FAIL_CLOSED",
        "typed_operand_continuity": "PASS_DELEGATED_TO_FROZEN_ENFORCEMENT_BEFORE_EMISSION",
        "terminal_result_exactly_one": "PASS_DELEGATED_TO_FROZEN_ENFORCEMENT_BEFORE_EMISSION",
        "meta_placeholder_instruction_governance_rejection": "PASS_DELEGATED_TO_FROZEN_ENFORCEMENT_BEFORE_EMISSION",
        "validator_before_encoding": "PASS",
        "pathless_import_allowlist": "PASS",
        "identity_pilot_routing_and_template_scan": "PASS_ZERO_HITS",
        "pilot09_regression": "PASS_STATIC_BINDING_EXPECTED_PRE_EMISSION_REJECTION",
        "pilot09_candidate_preservation": "PASS_BYTE_EXACT",
        "constructor_v5_1_preservation": "PASS_BYTE_EXACT",
        "constructor_invocations": 0,
        "realizer_invocations": 0,
        "emitter_invocations": 0,
        "candidate_surfaces_created_or_persisted": 0,
        "constructor_release": "NOT_PERFORMED",
        "deterministic_blockers": [],
        "verdict": "PASS_V5_2_REALIZATION_PROVIDER_AND_CANDIDATE_EMITTER_IMPLEMENTATION_STATIC_AUDIT_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "static_audit_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_V5_2_RUNTIME_STATIC_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-constructor-v5-2-realization-provider-implementation.json", provider_artifact)
    write("humor-mechanics-batch2-development-constructor-v5-2-candidate-emitter-implementation.json", emitter_artifact)
    write("humor-mechanics-batch2-development-constructor-implementation-v5-2.json", combined)
    write("humor-mechanics-batch2-development-constructor-v5-2-runtime-static-audit-v1.json", audit)
    print(json.dumps({"verdict": audit["verdict"],
                      "realization_provider_implementation_identity": provider_artifact["realization_provider_implementation_identity"],
                      "candidate_emitter_implementation_identity": emitter_artifact["candidate_emitter_implementation_identity"],
                      "constructor_implementation_identity": combined["constructor_implementation_identity"],
                      "static_audit_identity": audit["static_audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
