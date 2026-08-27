import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = (
    ROOT / ".pastilaacida-voice-v2-production-import-isolation-remediation-v1-evidence"
)


def load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_production_probe_is_proof_free_and_proof_api_remains_available():
    evidence = load("01-zero-call-import-proof.json")
    assert evidence["production_import_observation"]["loaded_forbidden"] == []
    assert evidence["production_import_observation"]["program_count"] == 12
    assert evidence["explicit_proof_import_observation"]["api_available"] is True


def test_only_expression_coverage_blocker_remains():
    residual = load("03-residual-gap-register.json")
    assert residual["open_blocking_gaps"] == 1
    assert residual["gaps"][0]["status"] == "RESOLVED_IN_THIS_SLICE"
    assert residual["gaps"][1]["status"] == "BLOCKED_BY_EXPLICIT_NEXT_CONTRACT"


def test_activation_and_calls_remain_zero():
    manifest = load("manifest.json")
    assert manifest["production_activation"] == {"expressions": 0, "surfaces": 0}
    assert manifest["model_provider_model_load_calls"] == [0, 0, 0]
