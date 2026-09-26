import ast
from pathlib import Path
ROOT=Path(__file__).parents[1]
def test_continuation_is_exactly_four_slots_and_no_retry_loop():
 p=ROOT/"scripts/supervise_editor_core_factual_setup_r2_anchored_contrastive_safety_continuation_v1.py"; text=p.read_text(); tree=ast.parse(text)
 assert 'SLOTS=(("P0_POSITIVE_ONLY_K1_R2_KL",314159)' in text
 assert "range(" not in text and "retry" not in text.lower()
 assert any(isinstance(n,ast.Call) and getattr(n.func,"attr",None)=="run" for n in ast.walk(tree))
