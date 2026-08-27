from __future__ import annotations

from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2 import GateIdV2
from pastila_scout.semantic_admission_v2.core_adapter import CoreV12SemanticEvaluatorAdapter

ROOT = Path(__file__).resolve().parents[1]


class _ForbiddenExecutor:
    calls = 0

    def execute(self, request):
        self.calls += 1
        raise AssertionError("adapter normalization invoked executor")


def _f_request():
    return {"gate_id":"FACTUAL_SEMANTIC","factual_summary":"O autoritate a propus o schimbare administrativă importantă.","candidate":"Schimbarea aleargă, iar hârtia încă își caută pantofii."}


def _s_request():
    value = _f_request(); value["gate_id"]="STORY_SPECIFICITY"
    value["controls"]=[{"case_id":"C1","factual_summary":"Un râu va avea un debit ușor mai scăzut.","factual_summary_sha256":"0"*64,"authority_identity":"a1"},
                       {"case_id":"C2","factual_summary":"O pană de curent a afectat mai multe cartiere.","factual_summary_sha256":"1"*64,"authority_identity":"a2"}]
    return value


def test_gate_f_adapter_renders_exact_prompt_without_execution():
    executor=_ForbiddenExecutor();adapter=CoreV12SemanticEvaluatorAdapter(project_root=ROOT,executor=executor,gate_id=GateIdV2.FACTUAL_SEMANTIC)
    prompt=adapter.render_prompt(_f_request())
    assert "FACTUAL SUMMARY:" in prompt and _f_request()["candidate"] in prompt
    assert "{candidate}" not in prompt
    assert executor.calls==0


def test_gate_s_prompt_contains_only_requested_governed_controls():
    adapter=CoreV12SemanticEvaluatorAdapter(project_root=ROOT,executor=_ForbiddenExecutor(),gate_id=GateIdV2.STORY_SPECIFICITY)
    prompt=adapter.render_prompt(_s_request())
    assert "[C1]" in prompt and "[C2]" in prompt
    assert "HMCV1-SASC" not in prompt


def test_gate_mismatch_and_bad_controls_are_rejected_before_executor():
    executor=_ForbiddenExecutor(); adapter=CoreV12SemanticEvaluatorAdapter(project_root=ROOT,executor=executor,gate_id=GateIdV2.FACTUAL_SEMANTIC)
    with pytest.raises(ValueError,match="does not match"):
        adapter.render_prompt(_s_request())
    assert executor.calls == 0
