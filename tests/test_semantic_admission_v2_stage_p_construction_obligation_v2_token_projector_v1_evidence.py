from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_token_projector_v1.py"
TEST = ROOT / "tests/test_semantic_admission_v2_stage_p_construction_obligation_v2_token_projector_v1.py"
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-token-projector-v1-candidate.json"
PREFLIGHT = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-v2-token-projector-v1-candidate-evidence/preflight.json"


def test_candidate_identity_and_files_reproduce() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    material = "\n".join(artifact["identity_derivation"]["ordered_utf8_fields"])
    assert hashlib.sha256(material.encode()).hexdigest() == artifact["canonical_identity"]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == artifact["implementation_sha256"]
    assert hashlib.sha256(TEST.read_bytes()).hexdigest() == artifact["focused_test_sha256"]
    assert json.loads(PREFLIGHT.read_bytes())["candidate_identity"] == artifact["canonical_identity"]


def test_source_has_no_execution_or_tokenizer_loading_imports() -> None:
    tree = ast.parse(SOURCE.read_text("utf-8")); imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    forbidden = ("transformers", "tokenizers", "provider", "runner", "executor",
                 "probe", "subprocess", "torch")
    assert not any(any(word in item.lower() for word in forbidden) for item in imports)


def test_preflight_and_authority_are_zero_execution() -> None:
    artifact = json.loads(ARTIFACT.read_bytes())
    preflight = json.loads(PREFLIGHT.read_bytes())
    assert all(value is False for value in artifact["authority"].values())
    for field in ("tokenizer_loads", "model_loads", "model_calls", "provider_calls",
                  "inference_calls", "runner_executions", "executor_executions",
                  "probe_constructions", "probe_executions", "stage_c_entries",
                  "retry_repair_selection_fallback"):
        assert preflight[field] == 0
