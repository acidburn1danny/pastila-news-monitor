import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_builder_is_byte_exact_and_audit_passes():
    artifacts = ROOT / "docs" / "artifacts"
    names = [
        "editor-core-factual-setup-r2-causal-diagnostic-v1-control-signal.jsonl",
        "editor-core-factual-setup-r2-causal-diagnostic-v1-challenger-signal.jsonl",
        "editor-core-factual-setup-r2-causal-diagnostic-v1-recipes.json",
        "editor-core-factual-setup-r2-causal-diagnostic-v1-evaluation.json",
        "editor-core-factual-setup-r2-causal-diagnostic-v1-protocol.json",
        "editor-core-factual-setup-r2-causal-diagnostic-v1-manifest.json",
    ]
    before = {name: (artifacts / name).read_bytes() for name in names}
    subprocess.run([sys.executable, str(ROOT / "scripts" / "build_editor_core_factual_setup_r2_causal_diagnostic_v1.py")], check=True)
    after = {name: (artifacts / name).read_bytes() for name in names}
    assert before == after
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "audit_editor_core_factual_setup_r2_causal_diagnostic_v1.py")], check=True, text=True, capture_output=True)
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "PASS"
    assert receipt["blockers"] == 0
    assert receipt["model_loaded"] is False
    assert receipt["optimizer_created"] is False
    assert receipt["training_performed"] is False


def test_fail_closed_on_signal_mutation():
    source = ROOT / "docs" / "artifacts" / "editor-core-factual-setup-r2-causal-diagnostic-v1-challenger-signal.jsonl"
    rows = source.read_text(encoding="utf-8").splitlines()
    first = json.loads(rows[0]); first["assistant_target_sha256"] = "0" * 64
    rows[0] = json.dumps(first, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    original = source.read_bytes()
    try:
        source.write_text("\n".join(rows) + "\n", encoding="utf-8")
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "audit_editor_core_factual_setup_r2_causal_diagnostic_v1.py")], text=True, capture_output=True)
        assert result.returncode != 0
        assert "target byte drift" in result.stderr
    finally:
        source.write_bytes(original)


def test_fail_closed_on_recipe_confound():
    source = ROOT / "docs" / "artifacts" / "editor-core-factual-setup-r2-causal-diagnostic-v1-recipes.json"
    original = source.read_bytes()
    value = json.loads(original)
    value["fixed"]["optimizer_steps"] = 18
    try:
        source.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        result = subprocess.run([sys.executable, str(ROOT / "scripts" / "audit_editor_core_factual_setup_r2_causal_diagnostic_v1.py")], text=True, capture_output=True)
        assert result.returncode != 0
        assert "recipes_identity mismatch" in result.stderr
    finally:
        source.write_bytes(original)
