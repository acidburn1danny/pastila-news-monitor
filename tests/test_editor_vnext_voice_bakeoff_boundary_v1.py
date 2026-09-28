import json
from pathlib import Path
import pytest
from scripts.build_editor_vnext_voice_bakeoff_boundary_v1 import CANDIDATE_LOCK, INVARIANTS, PLAN_ID, R2_LOCK, SEEDS, audit, identified

ART=Path("docs/artifacts")
def load(name): return json.loads((ART/name).read_text(encoding="utf-8"))
def test_audit_and_matrix():
    assert audit(Path("."))["slots"]==216
def test_exact_bindings():
    p=load("editor-vnext-voice-bakeoff-boundary-v1.json")
    assert p["bindings"]["plan_identity"]==PLAN_ID; assert p["bindings"]["candidate_lock_identity"]==CANDIDATE_LOCK; assert p["bindings"]["r2_lock_identity"]==R2_LOCK
    assert p["matrix"]=={"cases":24,"candidates":3,"seeds":SEEDS,"slots":216}
def test_answer_key_excluded_from_runtime_slots():
    slots=[json.loads(x) for x in (ART/"editor-vnext-voice-bakeoff-boundary-v1-slots.jsonl").read_text().splitlines()]
    assert all("candidate_id" not in x and x["answer_key_excluded"] for x in slots)
def test_factual_invariants_and_stop():
    p=load("editor-vnext-voice-bakeoff-boundary-v1.json"); assert p["factual_invariants"]==INVARIANTS; assert "SETUP_MUTATION" in p["terminal_rules"]["STOP"]
def test_tampering_is_detected():
    p=load("editor-vnext-voice-bakeoff-boundary-v1.json"); p["matrix"]["slots"]=215
    assert identified(p,"boundary_identity")["boundary_identity"] != p["boundary_identity"]
def test_no_model_execution_authority():
    p=load("editor-vnext-voice-bakeoff-boundary-v1.json"); assert p["runtime"]["model_load_authorized"] is False and p["runtime"]["quantization"]["execute"] is False
