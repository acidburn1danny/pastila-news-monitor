from __future__ import annotations

import ast
import hashlib
import json
import runpy
from pathlib import Path


SCRIPT = Path("scripts/verify_construction_obligation_v2_tokenizer_piece_adapter_v1.py")
RECEIPT = Path("docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-tokenizer-piece-adapter-load-verification-v1.json")


def test_historical_identity_is_rederived_exactly_without_loading_tokenizer():
    namespace = runpy.run_path(str(SCRIPT), run_name="verification_import_only")
    model = namespace["MODEL"]
    expected = "sha256:" + hashlib.sha256(f"{model}\n131072".encode()).hexdigest()
    assert namespace["historical_tokenizer_identity"](vocabulary_size=131072) == expected
    assert expected == "sha256:a91ae3f74fbc3b81c29c29c5e1567c4b018169af288989d5fca0089876f98a1c"


def test_harness_imports_no_model_provider_or_execution_api():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported_modules = {
        node.module for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not imported_modules.intersection({"torch", "peft", "subprocess"})
    called_names = {
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not called_names.intersection({"generate", "run", "Popen"})
    transformers_imports = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "transformers"
        for alias in node.names
    ]
    assert transformers_imports == ["AutoTokenizer", "__version__"]


def test_sealed_receipt_identity_and_zero_execution_authority():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    fields = receipt["identity_derivation"]["ordered_utf8_fields"]
    assert hashlib.sha256("\n".join(fields).encode()).hexdigest() == receipt["canonical_identity"]
    assert receipt["result"]["status"] == "PASS_TOKENIZER_LOAD_ONLY"
    assert receipt["result"]["excluded_non_eos_token_count"] == 999
    assert receipt["bounded_remediation"]["semantic_or_identity_change"] is False
    assert all(value is False for value in receipt["authority"].values())
