from __future__ import annotations

import ast
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_provider_identity_v1 import (
    MODEL_IDENTITY,
    STAGE_P_GRAMMAR_IDENTITY,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_provider_identity_v1.py"


def test_frozen_provider_neutral_identities_are_exact() -> None:
    assert MODEL_IDENTITY == "pastila-editor-core-v1.2-experimental"
    assert STAGE_P_GRAMMAR_IDENTITY == "sha256:019040dc2e424a57671221e1800d5b9dab100b31f6a23c85fca59cfebb541007"


def test_identity_module_has_no_execution_or_provider_imports() -> None:
    tree = ast.parse(SOURCE.read_text("utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module or "")
    assert not any(
        any(word in name for word in ("provider", "executor", "subprocess", "experimental_core", "transformers"))
        for name in imports
    )
