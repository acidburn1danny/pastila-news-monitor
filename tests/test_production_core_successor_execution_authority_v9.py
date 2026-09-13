from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/launch_production_core_candidate_qualification_v9.py"


def test_v9_launcher_is_detached_signed_and_fail_closed():
    source = LAUNCHER.read_text("utf-8")
    assert "production-core-candidate-execution-authority-v9.json" in source
    assert "production-core-candidate-execution-authority-v8-1.json" not in source
    assert "SIGNING_PUBLIC_KEY_SHA256" in source
    assert "detached authority signature invalid" in source
    assert "signed authority binding mismatch" in source
    assert "FROZEN_SUCCESSOR_V9_DUAL_STRUCTURAL_REMEDIATION_ZERO_ATTEMPTS" in source
    assert "candidate_execution_authorized\") is not False" in source
    assert "attempt_consumption_authorized\") is not False" in source


def test_v9_runtime_source_closure_uses_v9_launcher_only():
    source = (ROOT / "src/pastila_scout/production_core_candidate_execution_authority_v3.py").read_text("utf-8")
    assert '"scripts/launch_production_core_candidate_qualification_v9.py"' in source
    assert '"scripts/launch_production_core_candidate_qualification_v4.py"' not in source
