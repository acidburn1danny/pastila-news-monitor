from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_constraint_v2.py"
DESIGN = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-full-ledger-dfa-design-v1.json"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-full-ledger-character-dfa-v1-candidate.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-v2-full-ledger-character-dfa-v1-candidate-evidence/preflight.json"


def test_design_and_candidate_identities_reproduce():
    design = json.loads(DESIGN.read_bytes()); artifact = json.loads(ARTIFACT.read_bytes())
    design_parts = [design["artifact_id"], design["source_v2_candidate_identity"],
                    design["approved_reference_dfa_identity"],
                    "INHERIT_V1_SEMANTIC_OBLIGATIONS_REPLACE_FOUR_PROVENANCE_TRANSITIONS",
                    "DESIGN_ONLY"]
    assert hashlib.sha256("\n".join(design_parts).encode()).hexdigest() == design["design_identity"]
    implementation = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    candidate_parts = [artifact["artifact_id"], artifact["approved_design_identity"],
                       implementation, artifact["case01_context_identity"],
                       artifact["v2_ledger_json_schema_sha256"], "ZERO_INFERENCE"]
    assert hashlib.sha256("\n".join(candidate_parts).encode()).hexdigest() == artifact["candidate_identity"]
    assert implementation == artifact["implementation_sha256"]


def test_no_downstream_execution_import_or_authority():
    tree = ast.parse(SOURCE.read_text("utf-8")); imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = ("tracker", "controller", "projector", "evaluator", "runner",
                 "subprocess", "provider", "tokenizer", "wsl")
    assert not any(any(word in item.lower() for word in forbidden) for item in imports)
    design = json.loads(DESIGN.read_bytes()); artifact = json.loads(ARTIFACT.read_bytes())
    assert all(value is False for value in design["authority"].values())
    assert all(value is False for value in artifact["authority"].values())


def test_preflight_is_zero_inference_and_bound_to_candidate():
    artifact = json.loads(ARTIFACT.read_bytes()); preflight = json.loads(PREFLIGHT.read_bytes())
    assert preflight["candidate_identity"] == artifact["candidate_identity"]
    for key in ("tracker_objects", "controller_objects", "projector_objects",
                "evaluator_objects", "runner_objects", "subprocess_launches",
                "tokenizer_loads", "model_loads", "provider_calls", "inference_calls"):
        assert preflight[key] == 0
    assert preflight["probe_constructed"] is False
