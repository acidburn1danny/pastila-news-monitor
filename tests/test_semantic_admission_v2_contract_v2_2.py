from __future__ import annotations
import json
from pathlib import Path
from pastila_scout.semantic_admission_v2 import GateIdV2
from pastila_scout.semantic_admission_v2.core_adapter_v2_2 import CoreV12SemanticEvaluatorAdapterV22
from pastila_scout.semantic_admission_v2.models import GateResponseV2
from test_semantic_admission_v2_core_adapter import _f_request,_s_request

ROOT=Path(__file__).resolve().parents[1]
class _NoExecute:
    def execute(self,request):raise AssertionError("format probe attempted inference")

def test_v22_exact_pass_examples_satisfy_strict_contract():
    examples=[{"gate_id":"FACTUAL_SEMANTIC","decision":"PASS","reason_records":[]},{"gate_id":"STORY_SPECIFICITY","decision":"PASS","reason_records":[]}]
    for value in examples:
        raw=json.dumps(value,separators=(",",":"));GateResponseV2.model_validate_json(raw,strict=True)

def test_v22_prompts_render_unpadded_and_without_placeholders():
    f=CoreV12SemanticEvaluatorAdapterV22(project_root=ROOT,executor=_NoExecute(),gate_id=GateIdV2.FACTUAL_SEMANTIC)
    s=CoreV12SemanticEvaluatorAdapterV22(project_root=ROOT,executor=_NoExecute(),gate_id=GateIdV2.STORY_SPECIFICITY)
    for prompt in (f.render_prompt(_f_request()),s.render_prompt(_s_request())):
        assert prompt==prompt.strip() and not any(line.strip().startswith("```") for line in prompt.splitlines()) and "{candidate}" not in prompt
        assert "one-line unfenced JSON" in prompt
