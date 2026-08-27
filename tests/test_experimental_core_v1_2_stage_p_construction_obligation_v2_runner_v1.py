from __future__ import annotations
import ast
from pathlib import Path
import pytest
import pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1 as runner

ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/"src/pastila_scout/experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1.py"
def test_import_is_passive_and_runtime_imports_are_deferred(monkeypatch):
 calls=[];monkeypatch.setattr(runner.importlib,"import_module",lambda name:calls.append(name))
 assert runner.RUNNER_IDENTITY;assert calls==[]
 with pytest.raises(ValueError,match="REQUEST_FILE_REQUIRED"):runner.validate_request_only_v1(request_path=ROOT/"missing-v2-runner-request.json")
 assert calls==[]
def test_source_has_validation_before_private_deferred_import_and_no_execution_surface():
 text=SOURCE.read_text("utf-8");tree=ast.parse(text)
 top_imports=[]
 for node in tree.body:
  if isinstance(node,ast.Import):top_imports.extend(a.name for a in node.names)
  elif isinstance(node,ast.ImportFrom):top_imports.append(node.module or "")
 assert not {"torch","transformers","peft"}.intersection(top_imports)
 assert "parse_runner_request_v1(raw_request=raw)" in text
 for word in ("from_pretrained",".generate(","build_invocation",".execute(","subprocess","wsl_execution"):assert word not in text
 assert "if __name__" not in text and "main(" not in text
