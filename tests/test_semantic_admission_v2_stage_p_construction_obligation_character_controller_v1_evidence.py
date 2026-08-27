from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_character_controller_v1.py"
DESIGN = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-character-controller-design-v1.json"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-character-controller-v1-candidate.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-v2-character-controller-v1-candidate-evidence/preflight.json"


def test_design_and_candidate_identities_reproduce():
    design = json.loads(DESIGN.read_bytes()); artifact = json.loads(ARTIFACT.read_bytes())
    design_parts = [design["artifact_id"], design["approved_tracker_identity"],
                    "FINITE_OR_STRUCTURED_JSON_STRING_OR_TERMINAL",
                    "SEMANTICALLY_FILTERED_ONE_CHARACTER_ADVANCE", "DESIGN_ONLY"]
    assert hashlib.sha256("\n".join(design_parts).encode()).hexdigest() == design["design_identity"]
    implementation = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    candidate_parts = [artifact["artifact_id"], artifact["approved_design_identity"],
                       implementation, artifact["case01_context_identity"],
                       artifact["receipt_schema_name"], artifact["receipt_schema_version"],
                       "ZERO_INFERENCE"]
    assert hashlib.sha256("\n".join(candidate_parts).encode()).hexdigest() == artifact["candidate_identity"]
    assert implementation == artifact["implementation_sha256"]


def test_no_projector_tokenizer_or_execution_import_authority_activity():
    tree = ast.parse(SOURCE.read_text("utf-8")); imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = ("projector", "tokenizer", "evaluator", "runner", "subprocess",
                 "provider", "wsl")
    assert not any(any(word in item.lower() for word in forbidden) for item in imports)
    design = json.loads(DESIGN.read_bytes()); artifact = json.loads(ARTIFACT.read_bytes())
    preflight = json.loads(PREFLIGHT.read_bytes())
    assert preflight["candidate_identity"] == artifact["candidate_identity"]
    assert all(value is False for value in design["authority"].values())
    assert all(value is False for value in artifact["authority"].values())
    for key in ("projector_objects", "tokenizer_loads", "evaluator_objects",
                "runner_objects", "subprocess_launches", "model_loads",
                "provider_calls", "inference_calls"):
        assert preflight[key] == 0
    assert preflight["probe_constructed"] is False
