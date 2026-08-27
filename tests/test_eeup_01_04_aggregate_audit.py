import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".pastilaacida-voice-v2-eeup-01-04-aggregate-closure-audit-v1-evidence"


def load(name: str) -> dict:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def test_all_cases_are_accounted_without_reinterpreting_eeup_02() -> None:
    cases = load("02-eeup-case-ledger.json")
    assert len(cases["cases"]) == 4
    eeup_02 = next(x for x in cases["cases"] if x["case"] == "EEUP-02")
    assert eeup_02["outcome"] in {"FĂRĂ COMENTARIU", "FÄ‚RÄ‚ COMENTARIU"}
    assert eeup_02["planned_alternate_fallback_proved"] is False


def test_residual_register_blocks_activation_truthfully() -> None:
    register = load("03-residual-blocking-gap-register.json")
    assert register["open_blocking_gaps"] == 2
    assert register["production_readiness"] == "NOT_READY_FOR_PRODUCTION_ACTIVATION"
    assert {
        x["gap_id"]
        for x in register["gaps"]
        if x["status"] == "BLOCKED_BY_EXPLICIT_NEXT_CONTRACT"
    } == {
        "UGP-EXPRESSION-COVERAGE-01",
        "PRODUCTION-IMPORT-ISOLATION-REGRESSION-01",
    }
    assert load("manifest.json")["production_activation"] == {
        "expressions": 0,
        "surfaces": 0,
    }
