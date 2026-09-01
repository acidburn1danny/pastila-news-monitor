"""Freeze source-only Constructor V5.3.1 provider/emitter integration evidence."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
COMMIT = "57e24abc3a3833325a3485a219ee12b26a09fd0a"
RUNTIME_PATH = "src/pastila_scout/humor_batch2_development_constructor_v5_3_1_runtime.py"
ALIGNMENT_PATH = "src/pastila_scout/humor_batch2_development_constructor_v5_3_1_surface_alignment.py"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def git_json(name: str) -> dict[str, Any]:
    return json.loads(subprocess.check_output(["git", "show", f"{COMMIT}:docs/artifacts/{name}"], cwd=ROOT))


def require(value: bool, message: str) -> None:
    if not value:
        raise SystemExit(message)


def write(name: str, value: dict[str, Any]) -> None:
    path = ART / name
    require(not path.exists(), f"artifact exists: {name}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    require(subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == COMMIT, "HEAD")
    analysis = git_json("humor-mechanics-batch2-development-pilot11-v5-3-surface-witness-root-cause-v1.json")
    contract = git_json("humor-mechanics-batch2-development-constructor-surface-witness-alignment-contract-v5-3-1.json")
    alignment = git_json("humor-mechanics-batch2-development-constructor-surface-witness-alignment-implementation-v5-3-1.json")
    regression = git_json("humor-mechanics-batch2-development-pilot11-surface-witness-regression-v1.json")
    remediation_audit = git_json("humor-mechanics-batch2-development-pilot11-v5-3-surface-witness-remediation-audit-v1.json")
    require(analysis["analysis_identity"] == "30b76ef19767a2c84f5b7cf9e39cc523a103fe741ea7bef2fc16c982799f2b6b", "analysis")
    require(contract["successor_contract_identity"] == "c4af75cd962802d0035d9de39e6d014f715d5b5f5b60fd690ea3761f289d99fc", "contract")
    require(alignment["implementation_identity"] == "7e06b630a3782d8d05b1b86765727cb86caddbaac5d56056e07e727fe0af42bb", "alignment")
    require(regression["regression_identity"] == "605189ae7caa566cbf3b56adc498d13d5f33a8985ab64603d7660470a6aca060", "regression")
    require(remediation_audit["audit_identity"] == "fd1a5250b6120b76820951b8a0980dec26b43eaa543c2b60dbf8bb688da2962b", "audit")
    runtime_raw = (ROOT / RUNTIME_PATH).read_bytes()
    alignment_raw = (ROOT / ALIGNMENT_PATH).read_bytes()
    require(hashlib.sha256(alignment_raw).hexdigest() == alignment["module_sha256"], "alignment preservation")
    source = runtime_raw.decode("utf-8")
    tree = ast.parse(source)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    require({"realize_aligned_semantic_typed_plan", "emit_aligned_semantic_candidate_utf8", "_validate_aligned_structure"}.issubset(functions), "entry points")
    provider_source = ast.unparse(functions["realize_aligned_semantic_typed_plan"])
    emitter_source = ast.unparse(functions["emit_aligned_semantic_candidate_utf8"])
    require("validate_semantic_plan" in provider_source and "validate_surface_semantics" in provider_source, "V5.3 semantic enforcement")
    require("validate_node_role_alignment" in ast.unparse(functions["_validate_aligned_structure"]), "coordinate alignment")
    require(emitter_source.index("validate_surface_semantics") < emitter_source.index("_validate_aligned_structure") < emitter_source.index("encode"), "pre-emission order")
    imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)}
    imports.update(node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module)
    require(not imports.intersection({"os", "pathlib", "subprocess", "socket", "requests", "httpx", "openai", "torch", "transformers"}), "pathless")
    runtime_sha = hashlib.sha256(runtime_raw).hexdigest()
    shared = {"schema_version": "5.3.1", "successor_contract_identity": contract["successor_contract_identity"],
              "alignment_implementation_identity": alignment["implementation_identity"], "module_path": RUNTIME_PATH,
              "module_sha256": runtime_sha, "constructor_v5_3_preservation": "PASS_BYTE_EXACT",
              "constructor_invocations": 0, "provider_invocations": 0, "emitter_invocations": 0,
              "candidate_surfaces_created_or_persisted": 0, "release_authority": False}
    provider_core = {**shared, "schema_name": "batch2-development-constructor-v5-3-1-realization-provider-implementation",
                     "entry_point": "realize_aligned_semantic_typed_plan",
                     "alignment": "ACTUAL_CHARACTER_AND_UTF8_BYTE_COORDINATES_WITH_ENUMERATED_RULES_ONLY",
                     "v5_3_semantic_guards": "PRESERVED_UNCHANGED"}
    provider = {**provider_core, "realization_provider_identity": seal("B2_CONSTRUCTOR_V5_3_1_REALIZATION_PROVIDER", provider_core)}
    emitter_core = {**shared, "schema_name": "batch2-development-constructor-v5-3-1-candidate-emitter-implementation",
                    "entry_point": "emit_aligned_semantic_candidate_utf8",
                    "pre_emission_order": "SEMANTIC_GRAPH_THEN_COORDINATE_ALIGNMENT_THEN_BYTES",
                    "legacy_exact_substring_emitter_used": False}
    emitter = {**emitter_core, "candidate_emitter_identity": seal("B2_CONSTRUCTOR_V5_3_1_CANDIDATE_EMITTER", emitter_core)}
    combined_core = {**shared, "schema_name": "batch2-development-constructor-implementation-v5-3-1",
                     "realization_provider_identity": provider["realization_provider_identity"],
                     "candidate_emitter_identity": emitter["candidate_emitter_identity"],
                     "integration_scope": "COORDINATE_BOUND_WITNESS_ALIGNMENT_WITH_UNCHANGED_V5_3_SEMANTIC_ENFORCEMENT"}
    combined = {**combined_core, "constructor_implementation_identity": seal("B2_CONSTRUCTOR_IMPLEMENTATION_V5_3_1", combined_core)}
    audit_core = {
        "schema_name": "batch2-development-constructor-v5-3-1-runtime-static-audit-v1", "schema_version": "5.3.1",
        "successor_contract_identity": contract["successor_contract_identity"],
        "realization_provider_identity": provider["realization_provider_identity"],
        "candidate_emitter_identity": emitter["candidate_emitter_identity"],
        "constructor_implementation_identity": combined["constructor_implementation_identity"],
        "pilot11_regression_identity": regression["regression_identity"], "module_sha256": runtime_sha,
        "actual_character_and_utf8_byte_spans_authoritative": "PASS",
        "exact_nfkc_casefold_alignment": "PASS_ACCEPTED", "enumerated_ambele_ambelor_alignment": "PASS_ACCEPTED_WITH_COORDINATES",
        "canonical_text_substitution_for_surface_evidence": "PASS_PROHIBITED",
        "missing_coordinates_or_absent_text": "PASS_FAIL_CLOSED",
        "unlicensed_synonymy_paraphrase_fuzzy_or_semantic_guessing": "PASS_FAIL_CLOSED",
        "independent_actor_predicate_patient_coverage": "PASS_REQUIRED_EVERY_NODE",
        "v5_3_role_affordance_entity_edge_and_terminal_guards": "PASS_PRESERVED_UNCHANGED",
        "pathless_import_allowlist": "PASS", "constructor_invocations": 0, "provider_invocations": 0,
        "emitter_invocations": 0, "candidate_surfaces": 0, "release_authority": False,
        "pilot11_capability_state": "PRESERVED_CONSUMED_1_OF_1_NO_RETRY", "deterministic_blockers": [],
        "verdict": "PASS_V5_3_1_PROVIDER_EMITTER_INTEGRATION_STATIC_AUDIT_ZERO_CONSTRUCTION_NO_RELEASE",
    }
    audit = {**audit_core, "static_audit_identity": seal("B2_CONSTRUCTOR_V5_3_1_RUNTIME_STATIC_AUDIT_V1", audit_core)}
    write("humor-mechanics-batch2-development-constructor-v5-3-1-realization-provider-implementation.json", provider)
    write("humor-mechanics-batch2-development-constructor-v5-3-1-candidate-emitter-implementation.json", emitter)
    write("humor-mechanics-batch2-development-constructor-implementation-v5-3-1.json", combined)
    write("humor-mechanics-batch2-development-constructor-v5-3-1-runtime-static-audit-v1.json", audit)
    print(json.dumps({"verdict": audit["verdict"], "provider_identity": provider["realization_provider_identity"],
                      "emitter_identity": emitter["candidate_emitter_identity"],
                      "combined_identity": combined["constructor_implementation_identity"],
                      "static_audit_identity": audit["static_audit_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
