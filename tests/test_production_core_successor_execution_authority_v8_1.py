from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/launch_production_core_candidate_qualification_v4.py"


def test_v8_1_launcher_is_separate_fixed_and_fail_closed():
    source = LAUNCHER.read_text("utf-8")
    assert "production-core-candidate-execution-authority-v8-1.json" in source
    assert "production-core-candidate-execution-authority-v7.json" not in source
    assert "EXPECTED_EXECUTION_AUTHORITY_IDENTITY" not in source
    assert "SIGNING_PUBLIC_KEY_SHA256" in source
    assert "detached authority signature invalid" in source
    assert "signed authority binding mismatch" in source
    assert "FROZEN_SUCCESSOR_V8_1_LAUNCH_BINDING_REPAIR_ZERO_ATTEMPTS" in source
    assert source.count("scripts/launch_production_core_candidate_qualification_v4.py") == 2
    assert "predecessor_root_cause_addendum_identity" in source
    assert "lifecycle_completed_contract" in source


def test_v8_1_preflight_receipt_uses_exact_runtime_source_closure():
    source = (
        ROOT / "src/pastila_scout/production_core_candidate_execution_authority_v3.py"
    ).read_text("utf-8")
    assert '"scripts/launch_production_core_candidate_qualification_v4.py"' in source
    assert '"scripts/launch_production_core_candidate_qualification_v3.py"' not in source
    assert '"scripts/materialize_production_core_successor_execution_authority_v7.py"' not in source
