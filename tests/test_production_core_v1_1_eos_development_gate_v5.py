import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_production_core_v1_1_eos_development_gate_v5.py"
LAUNCHER = ROOT / "scripts/launch_production_core_v1_1_eos_development_gate_v5.sh"


def module():
    spec = importlib.util.spec_from_file_location("development_gate_v5", RUNNER)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_gate_source_is_parseable_and_has_no_qualification_inputs():
    source = RUNNER.read_text("utf-8")
    ast.parse(source)
    assert "qualification" not in source.lower().replace("qualification_attempt_consumed", "")
    assert '"qualification_attempt_consumed": False' in source
    assert "do_sample=False" in source
    assert '"FAIL_CLOSED"' in source
    gate_expression = source[source.index("passed = all(") : source.index("core = {")]
    assert 'row["exact_target"]' not in gate_expression


def test_repetition_gate_rejects_four_occurrences():
    value = module()
    phrase = "unu doi trei patru cinci sase sapte opt"
    assert value.repeated_ngram_ceiling(" ".join([phrase] * 3)) == 3
    assert value.repeated_ngram_ceiling(" ".join([phrase] * 4)) == 4


def test_launcher_is_offline_read_only_and_identity_bound():
    source = LAUNCHER.read_text("utf-8")
    assert "unshare --mount --net" in source
    assert "HF_HUB_OFFLINE=1" in source
    assert "TRANSFORMERS_OFFLINE=1" in source
    assert "mount -o remount,bind,ro" in source
    assert "ADAPTER_SHA256" in source and "DEVELOPMENT_SHA256" in source


def test_disposition_is_collision_safe_and_durable():
    source = (
        ROOT / "scripts/materialize_production_core_v1_1_eos_development_disposition_v5.py"
    ).read_text("utf-8")
    assert "target.exists() or target.is_symlink()" in source
    assert 'target.open("xb")' in source
    assert "fsync" in source
