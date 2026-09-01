import ast
from pathlib import Path
def test_validator_has_no_downstream_import_or_write_to_owner_inputs():
    path=Path(__file__).resolve().parents[1]/"scripts/validate_humor_batch2_development_pilot13_preingestion_v1.py";source=path.read_text(encoding="utf-8");tree=ast.parse(source)
    assert "proposition_binding_selection_or_sufficiency_performed" in source and "downstream_suitability_evaluated" in source
    assert "write_bytes" not in source and "owner-source-pilot13-v1.txt\").write" not in source
    assert not any(isinstance(n,ast.ImportFrom) and "constructor" in (n.module or "") for n in ast.walk(tree))
