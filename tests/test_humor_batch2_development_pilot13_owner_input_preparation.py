import ast
from pathlib import Path
def test_pilot13_preparation_script_is_content_free_and_has_no_constructor_path():
    path=Path(__file__).resolve().parents[1]/"scripts/prepare_humor_batch2_development_pilot13_owner_input_v5_3_3.py"; source=path.read_text(encoding="utf-8"); tree=ast.parse(source)
    assert "owner-source-pilot13-v1.txt" in source and "LEGITIMATE_END_TO_END_MECHANISM_TRIAL" in source
    assert "read_bytes" not in source and "invoke_clause_only_provider" not in source and "execute_release_facing_path" not in source
    assert not any(isinstance(n,ast.ImportFrom) and "constructor" in (n.module or "") for n in ast.walk(tree))
