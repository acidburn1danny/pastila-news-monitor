import json
from pathlib import Path
R=Path(__file__).parents[1]
def test_authority_is_bounded():
 a=json.loads((R/'docs/artifacts/editor-core-text-realizer-base-bakeoff-v1-execution-authority.json').read_text())
 assert set(a['candidates'])=={'C0_R2_MINISTRAL','C1_QWEN3_8B','C2_QWEN25_7B'}
 assert a['slots']==6 and not a['retry_authorized'] and not a['semantic_scoring_authorized']
