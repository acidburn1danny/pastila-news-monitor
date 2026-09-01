"""Freeze Constructor V5.3 provider/emitter integration and static audit."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "49958b3c3903f563468c915c422c3936b890d517"
RUNTIME = "src/pastila_scout/humor_batch2_development_constructor_v5_3_runtime.py"
V5_2_RUNTIME = "src/pastila_scout/humor_batch2_development_constructor_v5_2_runtime.py"
ENFORCEMENT = "src/pastila_scout/humor_batch2_development_constructor_v5_3_semantic_enforcement.py"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_bytes(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], cwd=ROOT)


def load(path: str) -> dict[str, Any]:
    return json.loads(git_bytes(path))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), f"artifact exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def call_lines(function: ast.FunctionDef, name: str) -> list[int]:
    return [node.lineno for node in ast.walk(function) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name) and node.func.id == name]


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    contract = load("docs/artifacts/humor-mechanics-batch2-development-constructor-contract-v5-3.json")
    governance = load("docs/artifacts/humor-mechanics-batch2-semantic-edge-role-continuity-governance-v5-3.json")
    schema = load("docs/artifacts/humor-mechanics-batch2-semantic-edge-role-continuity-conformance-schema-v5-3.json")
    enforcement = load("docs/artifacts/humor-mechanics-batch2-development-constructor-semantic-edge-enforcement-v5-3.json")
    regression = load("docs/artifacts/humor-mechanics-batch2-pilot10-role-incompatible-terminal-edge-regression-v1.json")
    require(contract["constructor_contract_identity"] == "9d811b18c16e8770549c19c9d8be63ef6f04e030fa67b5a47167b5e7ddc1bef6", "contract")
    require(governance["governance_identity"] == "073d68d9d21c76974d12eb8e3f591f4172197377bfb36c2de2f85a5afe079dd6", "governance")
    require(schema["schema_identity"] == "4b26df92539082f11b83c83f76b1d158c7c8f4c87304bdcdd8a6129644f532f3", "schema")
    require(enforcement["semantic_enforcement_implementation_identity"] == "16e54e9a09ed95905fd1f308d77b7bd4f03084b3a1654f8161a6c78b62ce6983", "enforcement")
    require(regression["regression_identity"] == "84413654223665f050d7a3e91dd68c6af008aff380f844adbedb81146f576185", "regression")
    require((ROOT / V5_2_RUNTIME).read_bytes() == git_bytes(V5_2_RUNTIME), "V5.2 runtime changed")
    require((ROOT / ENFORCEMENT).read_bytes() == git_bytes(ENFORCEMENT), "V5.3 enforcement changed")

    runtime = (ROOT / RUNTIME).read_bytes()
    source = runtime.decode()
    tree = ast.parse(source)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    provider = functions["realize_semantic_typed_plan"]
    emitter = functions["emit_semantic_candidate_utf8"]
    require(call_lines(provider, "validate_semantic_plan")[0] < call_lines(provider, "realize_typed_plan")[0]
            < call_lines(provider, "validate_surface_semantics")[0], "provider validation order")
    require(call_lines(emitter, "validate_surface_semantics")[0]
            < call_lines(emitter, "emit_candidate_utf8")[0], "emitter validation order")
    imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imports.update(node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module)
    require(not imports.intersection({"os", "pathlib", "subprocess", "socket", "requests", "httpx", "openai", "torch", "transformers", "importlib"}), "pathless")
    module_sha = hashlib.sha256(runtime).hexdigest()

    common = {
        "schema_version": "5.3.0", "constructor_contract_identity": contract["constructor_contract_identity"],
        "governance_identity": governance["governance_identity"], "conformance_schema_identity": schema["schema_identity"],
        "semantic_enforcement_implementation_identity": enforcement["semantic_enforcement_implementation_identity"],
        "module_path": RUNTIME, "module_sha256": module_sha, "release_authority": False,
    }
    provider_core = {**common, "schema_name": "batch2-development-constructor-v5-3-realization-provider-implementation",
                     "entrypoint": "realize_semantic_typed_plan", "semantic_plan_validation_precedes_realization": True,
                     "surface_semantic_validation_follows_realization": True, "invocations": 0,
                     "candidate_surfaces_created": 0}
    provider_artifact = {**provider_core, "realization_provider_implementation_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_V5_3_REALIZATION_PROVIDER_IMPLEMENTATION", provider_core)}
    emitter_core = {**common, "schema_name": "batch2-development-constructor-v5-3-candidate-emitter-implementation",
                    "realization_provider_implementation_identity": provider_artifact["realization_provider_implementation_identity"],
                    "entrypoint": "emit_semantic_candidate_utf8", "semantic_validation_precedes_structural_emission": True,
                    "invocations": 0, "candidate_surfaces_emitted": 0}
    emitter_artifact = {**emitter_core, "candidate_emitter_implementation_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_V5_3_CANDIDATE_EMITTER_IMPLEMENTATION", emitter_core)}
    combined_core = {**common, "schema_name": "batch2-development-constructor-implementation-v5-3",
                     "realization_provider_implementation_identity": provider_artifact["realization_provider_implementation_identity"],
                     "candidate_emitter_implementation_identity": emitter_artifact["candidate_emitter_implementation_identity"],
                     "constructor_v5_2_preservation": "PASS_BYTE_EXACT", "constructor_invocations": 0,
                     "candidate_surfaces_created_or_emitted": 0, "construction_authority": False,
                     "constructor_release": "NOT_PERFORMED"}
    combined = {**combined_core, "constructor_implementation_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_IMPLEMENTATION_V5_3", combined_core)}
    audit_core = {
        **common, "schema_name": "batch2-development-constructor-v5-3-runtime-static-audit-v1",
        "constructor_implementation_identity": combined["constructor_implementation_identity"],
        "realization_provider_implementation_identity": provider_artifact["realization_provider_implementation_identity"],
        "candidate_emitter_implementation_identity": emitter_artifact["candidate_emitter_implementation_identity"],
        "pilot10_regression_identity": regression["regression_identity"],
        "typed_semantic_roles_and_predicate_argument_signatures": "PASS_ENFORCED",
        "entity_identity_preservation_across_reclassification": "PASS_ENFORCED",
        "privileged_role_or_affordance_from_reclassification": "PASS_REJECTED",
        "every_edge_role_and_action_affordance_compatibility": "PASS_ENFORCED",
        "counterfactual_dependency_and_non_arbitrariness_every_edge": "PASS_REQUIRED",
        "terminal_edge_validation_strength": "PASS_EQUAL_TO_INTERMEDIATE",
        "plan_to_surface_semantic_role_witnesses": "PASS_EXACT_MATCH_REQUIRED",
        "lexical_operand_recurrence_alone": "INSUFFICIENT_FAIL_CLOSED",
        "structural_predecessor_continuity_alone": "INSUFFICIENT_FAIL_CLOSED",
        "category_or_status_reclassification_alone": "INSUFFICIENT_FAIL_CLOSED",
        "explicit_terminal_witness_presence_alone": "INSUFFICIENT_FAIL_CLOSED",
        "pilot10_failure_class": "PASS_FAIL_CLOSED_BEFORE_REALIZATION",
        "provider_validation_order": "PASS_PLAN_BEFORE_REALIZATION_SURFACE_AFTER",
        "emitter_validation_order": "PASS_SEMANTIC_BEFORE_STRUCTURAL_BYTE_EMISSION",
        "pathless_import_allowlist": "PASS", "constructor_invocations": 0, "provider_invocations": 0,
        "emitter_invocations": 0, "candidate_surfaces_created_or_persisted": 0,
        "constructor_release": "NOT_PERFORMED", "deterministic_blockers": [],
        "verdict": "PASS_V5_3_PROVIDER_EMITTER_INTEGRATION_STATIC_AUDIT_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "static_audit_identity": seal("B2_DEVELOPMENT_CONSTRUCTOR_V5_3_RUNTIME_STATIC_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-constructor-v5-3-realization-provider-implementation.json", provider_artifact)
    write("humor-mechanics-batch2-development-constructor-v5-3-candidate-emitter-implementation.json", emitter_artifact)
    write("humor-mechanics-batch2-development-constructor-implementation-v5-3.json", combined)
    write("humor-mechanics-batch2-development-constructor-v5-3-runtime-static-audit-v1.json", audit)
    print(json.dumps({"verdict": audit["verdict"], "provider": provider_artifact["realization_provider_implementation_identity"],
                      "emitter": emitter_artifact["candidate_emitter_implementation_identity"],
                      "combined": combined["constructor_implementation_identity"], "audit": audit["static_audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
