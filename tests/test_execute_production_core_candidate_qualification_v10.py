import ast,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WRAPPER=ROOT/"scripts/execute_production_core_candidate_qualification_v10.py";SOURCE=ROOT/"scripts/execute_production_core_candidate_qualification_v3.py"
def test_wrapper_pins_v3_and_projects_only_v10_authority():
 text=WRAPPER.read_text("utf-8");ast.parse(text)
 assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=="9869bfcb65da5a189013f1b56ca3f914c86872bad59c2997d1d4c59ab97239f7"
 for witness in ("production-core-successor-comparative-qualification-generation-v10.json","production-core-successor-candidate-object-manifest-v10.json","production-core-successor-candidate-generation-qualification-v10.json","pastila-editor-core-v1.1-json-successor-v10-system-prompt.txt","V10 candidate manifest mapping mismatch"):
  assert witness in text
 assert "build_attempt(" not in text
def test_composed_prompt_hashes_are_pinned():
 text=WRAPPER.read_text("utf-8")
 assert "91c84e9ab10cbecdfdd7e255b133c56263feb546d55d7e1ea01362f9be5567bb" in text
 assert "70e125c8fa6e58f3864419bec34f6685a95bcb7bbfb9455838aaf593d01fac36" in text
