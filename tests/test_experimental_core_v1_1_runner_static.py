import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "src/pastila_scout/experimental_core_v1_1_runner.py"
RUNNER_SHA256 = "0293ffdf3be8bd606094eea487a2b32e6f7ca5b7b42741addaca97a8e6df7478"


def test_core_v1_1_runner_bytes_are_frozen():
    assert hashlib.sha256(RUNNER.read_bytes()).hexdigest() == RUNNER_SHA256


def test_core_v1_1_runner_remains_explicit_local_execution_source():
    source = RUNNER.read_text("utf-8")
    tree = ast.parse(source)
    main_guards = [
        node
        for node in tree.body
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
    ]

    assert len(main_guards) == 1
    assert "local_files_only=True" in source
    assert 'prompt_path.read_text("utf-8")' in source
    assert "torch.inference_mode()" in source
    assert "tokenizer.decode(tokens, skip_special_tokens=True)" in source
