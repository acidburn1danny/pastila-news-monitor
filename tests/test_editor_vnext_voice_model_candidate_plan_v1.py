import json
from pathlib import Path

from scripts.audit_editor_vnext_voice_model_candidate_plan_v1 import audit
from scripts.build_editor_vnext_voice_model_candidate_plan_v1 import build


def test_plan_reproduces_and_is_planning_only():
    assert audit()["status"] == "PASS"
    assert json.loads(Path("docs/artifacts/editor-vnext-voice-model-candidate-plan-v1.json").read_text(encoding="utf-8")) == build()


def test_shortlist_is_bounded_text_only_and_exact():
    value = build(); candidates = value["candidates"]
    assert [item["candidate_id"] for item in candidates] == ["V0_R2_MINISTRAL_CONTROL", "V1_QWEN3_8B_NON_THINKING", "V2_QWEN25_7B_INSTRUCT"]
    assert candidates[1]["revision"] == "b968826d9c46dd6066d109eabc6255188de91218"
    assert candidates[2]["revision"] == "a09a35458c702b33eeacc393d103063234e8bc28"
    assert value["acquisition"]["authorized"] is False and value["bakeoff"]["authorized"] is False


def test_factual_and_promotion_gates_are_fail_closed():
    value = build(); rules = value["terminal_rules"]
    assert "any setup mutation" in rules["STOP"]
    assert "any unsupported concrete factual claim" in rules["STOP"]
    assert rules["authority"].startswith("DEVELOPMENT_RESEARCH_ONLY")
    assert value["contracts"]["output"]["factual_setup_field_forbidden"] is True


def test_external_local_models_are_not_misclassified_as_vnext_dependencies():
    state = build()["local_dependency_state"]
    assert state["R2"] == "IN_VNEXT_ACTIVE_CLOSURE"
    assert all("NOT_AN_ALLOWED_RUNTIME_DEPENDENCY" in state[key] for key in ("QWEN3_8B", "QWEN25_7B"))
