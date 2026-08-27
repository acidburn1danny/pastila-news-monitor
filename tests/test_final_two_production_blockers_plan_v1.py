import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".pastilaacida-voice-v2-final-two-production-blockers-plan-v1-evidence"


def load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_plan_keeps_both_gaps_blocking_and_activation_zero():
    manifest = load("manifest.json")
    residual = load("05-residual-gap-register.json")
    assert manifest["open_blocking_gaps"] == 2
    assert residual["open_blocking_gaps"] == 2
    assert manifest["production_activation"] == {"expressions": 0, "surfaces": 0}


def test_import_diagnosis_names_exact_eager_chain():
    diagnosis = load("01-production-import-isolation-diagnosis.json")
    assert diagnosis["root_import_chain"][-2:] == [
        "pastila_scout.voice_deterministic_v2.renderer",
        "pastila_scout.voice_deterministic_v2.library",
    ]
    assert diagnosis["production_renderer_status"] == "CLEAN_NO_STATIC_PROOF_IMPORT"


def test_fallback_contract_requires_genuine_two_to_one_pool():
    contract = load("03-eeup-02-alternate-fallback-proof-contract.json")
    required = " ".join(contract["required_sequence"])
    assert "exactly the two genuine" in required
    assert "excludes the previously used member" in required
    assert (
        contract["expected_remaining_member_if_semantics_support_it"]["surface_id"]
        == "SURFACE_BOUNDED_POOL_01_V1"
    )


def test_next_action_closes_import_boundary_first():
    manifest = load("manifest.json")
    sequence = load("04-execution-sequence-and-gates.json")
    assert manifest["exact_next_governed_action"] == sequence["phase_1"]["action"]
    assert sequence["phase_3"]["activation_precondition"] == "OPEN_BLOCKING_GAPS = 0"
