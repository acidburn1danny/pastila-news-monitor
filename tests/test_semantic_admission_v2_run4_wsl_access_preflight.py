from pathlib import Path

from scripts.preflight_semantic_admission_v2_run4_wsl_access_v1 import CONSTRAINED, ORDINARY, ROOT


def test_preflight_binds_existing_exact_runners() -> None:
    assert ROOT == Path(__file__).resolve().parents[1]
    assert CONSTRAINED.is_file()
    assert ORDINARY.is_file()


def test_preflight_source_is_zero_inference_and_does_not_authorize_run4() -> None:
    source = (ROOT / "scripts/preflight_semantic_admission_v2_run4_wsl_access_v1.py").read_text(encoding="utf-8")
    assert '"model_calls": 0' in source
    assert '"provider_calls": 0' in source
    assert '"run4_execution_authorized": False' in source
    assert ".generate(" not in source
