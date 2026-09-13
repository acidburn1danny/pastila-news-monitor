import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_production_core_successor_development_gate_v9.py"
LAUNCHER = ROOT / "scripts/launch_production_core_successor_development_gate_v9.sh"


def module():
    spec = importlib.util.spec_from_file_location("development_gate_v9", RUNNER)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_v9_gate_is_fail_closed_and_has_no_qualification_inputs():
    source = RUNNER.read_text("utf-8")
    ast.parse(source)
    assert "qualification" not in source.lower().replace("qualification_attempt_consumed", "")
    assert 'len(rows) in {48, 72}' in source
    assert '"RUNNER_SHA256"' in source
    assert '"LAUNCHER_SHA256"' in source
    assert '"qualification_attempt_consumed": False' in source
    assert '"FAIL_CLOSED"' in source


def test_v9_gate_repetition_boundary():
    value = module()
    phrase = "unu doi trei patru cinci sase sapte opt"
    assert value.repeated_ngram_ceiling(" ".join([phrase] * 3)) == 3
    assert value.repeated_ngram_ceiling(" ".join([phrase] * 4)) == 4


def test_v9_launcher_binds_sources_and_is_offline_read_only():
    source = LAUNCHER.read_text("utf-8")
    assert "unshare --mount --net" in source
    assert "HF_HUB_OFFLINE=1" in source and "TRANSFORMERS_OFFLINE=1" in source
    assert "mount -o remount,bind,ro" in source
    assert "LAUNCHER_SHA256" in source and "RUNNER_SHA256" in source
