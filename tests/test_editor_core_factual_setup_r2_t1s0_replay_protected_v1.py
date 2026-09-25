import json
import subprocess
import sys
import importlib.util
import pytest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "audit_editor_core_factual_setup_r2_t1s0_replay_protected_v1.py"
ART = ROOT / "docs" / "artifacts"
P = "editor-core-factual-setup-r2-t1s0-replay-protected-v1"


def test_successor_design_audit_passes() -> None:
    result = subprocess.run([sys.executable, str(AUDIT)], cwd=ROOT, check=True, text=True, capture_output=True)
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "PASS" and receipt["blockers"] == 0
    assert receipt["targeted_rows_byte_identical"] == 48
    assert receipt["replay_rows_protected"] == receipt["critical_spans"] == 24


def test_protocol_is_development_research_only() -> None:
    protocol = json.loads((ART / f"{P}-protocol.json").read_text("utf-8"))
    assert protocol["parent"] == "R2_STEP_9"
    assert protocol["real_runs_authorized"] is False
    assert protocol["optimizer_steps_authorized"] == 0
    assert protocol["parent_selection_authority"] is False
    assert "PARENT_SELECTION" in protocol["claims_forbidden"]


def _audit_module():
    spec = importlib.util.spec_from_file_location("replay_protected_audit", AUDIT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_adversarial_span_metadata_and_target_drift_fail_closed() -> None:
    module = _audit_module()
    rows = [json.loads(x) for x in (ART / f"{P}-protected-signal.jsonl").read_text("utf-8").splitlines()]
    replay = next(row for row in rows if row["split"] == "REPLAY_PROTECTION")
    sources = [json.loads(x) for x in (ART / "editor-core-factual-setup-corrective-v1-training.jsonl").read_text("utf-8").splitlines()]
    assistant = next(x for x in sources if x["example_id"] == replay["example_id"])["messages"][-1]["content"]
    replay["critical_spans"][0]["start"] = 0
    with pytest.raises(AssertionError):
        module.validate_span(assistant, replay["critical_spans"][0])


def test_adversarial_seed_or_authority_drift_fails_closed() -> None:
    module = _audit_module()
    value = json.loads((ART / f"{P}-protocol.json").read_text("utf-8"))
    recipes = json.loads((ART / "editor-core-factual-setup-r2-causal-diagnostic-v1-recipes.json").read_text("utf-8"))
    evaluation = json.loads((ART / "editor-core-factual-setup-r2-causal-diagnostic-v1-evaluation.json").read_text("utf-8"))
    value["seeds"] = [1, 2, 3]
    value["training_authorized"] = True
    with pytest.raises(AssertionError):
        module.validate_protocol(value, recipes, evaluation)
