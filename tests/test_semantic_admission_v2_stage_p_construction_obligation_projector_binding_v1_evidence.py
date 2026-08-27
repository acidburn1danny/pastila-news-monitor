from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_projector_binding_v1.py"
ARTIFACT_ROOT = ROOT / "docs/artifacts"
FILES = [
    "semantic-admission-v2-stage-p-construction-obligation-token-projector-v1-approval-freeze.json",
    "semantic-admission-v2-stage-p-construction-obligation-projector-interface-design-v1.json",
    "semantic-admission-v2-stage-p-construction-obligation-projector-interface-binding-v1.json",
]


def _load(name): return json.loads((ARTIFACT_ROOT / name).read_bytes())
def _identity(value): return hashlib.sha256("\n".join(value["identity_derivation"]["ordered_utf8_fields"]).encode()).hexdigest()


def test_all_interface_identities_reproduce_and_source_is_bound():
    values = [_load(name) for name in FILES]
    assert all(_identity(value) == value["canonical_identity"] for value in values)
    binding = values[-1]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == binding["implementation_sha256"]
    assert binding["approved_design_identity"] == values[1]["canonical_identity"]
    assert binding["approved_projector_freeze_identity"] == values[0]["canonical_identity"]


def test_binding_module_has_no_execution_or_model_imports_and_no_authority():
    tree = ast.parse(SOURCE.read_text("utf-8")); imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom): imports.append(node.module or "")
    forbidden = ("subprocess", "experimental_core", "durable_executor", "transformers", "torch", "peft")
    assert not any(any(word in name for word in forbidden) for name in imports)
    design = _load(FILES[1]); binding = _load(FILES[2])
    assert all(value is False for value in design["authority"].values())
    assert all(value is False for value in binding["authority"].values())
    for key in ("executor_objects", "subprocess_or_wsl_launches", "tokenizer_loads",
                "model_loads", "provider_calls", "inference_calls",
                "probe_constructions", "probe_executions"):
        assert binding["verification"][key] == 0
