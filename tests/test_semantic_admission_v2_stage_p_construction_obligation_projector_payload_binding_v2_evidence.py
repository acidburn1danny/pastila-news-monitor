from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_projector_payload_binding_v2.py"
DESIGN=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-projector-payload-rebinding-design-v2.json"
BINDING=ROOT/"docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-projector-payload-binding-v2.json"


def _load(path): return json.loads(path.read_bytes())
def _identity(value): return hashlib.sha256("\n".join(value["identity_derivation"]["ordered_utf8_fields"]).encode()).hexdigest()


def test_design_binding_and_source_identities_reproduce():
    design=_load(DESIGN);binding=_load(BINDING)
    assert _identity(design)==design["canonical_identity"]
    assert _identity(binding)==binding["canonical_identity"]
    assert binding["approved_design_identity"]==design["canonical_identity"]
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==binding["implementation_sha256"]


def test_payload_module_has_no_execution_import_and_receipt_has_no_activity():
    tree=ast.parse(SOURCE.read_text("utf-8"));imports=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): imports.extend(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom): imports.append(node.module or "")
    assert not any(any(word in name for word in ("subprocess","transformers","torch","peft")) for name in imports)
    binding=_load(BINDING); verification=binding["verification"]
    for key in ("executor_invoke_calls","subprocess_or_wsl_runner_launches","tokenizer_loads",
                "model_loads","inference_calls","probe_constructions","probe_executions"):
        assert verification[key]==0
    assert all(value is False for value in binding["authority"].values())
