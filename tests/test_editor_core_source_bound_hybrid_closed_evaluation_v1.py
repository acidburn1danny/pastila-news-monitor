import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("hybrid_eval", ROOT / "scripts/evaluate_editor_core_source_bound_hybrid_closed_v1.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_r2_wrapper_and_objective_helpers():
    text, parsed = MODULE.unwrap_r2('{"case_id": 1, "text": "Prima propoziție are informații. A doua propoziție este clară."}')
    assert parsed is True
    assert text.startswith("Prima")
    assert MODULE.functional_romanian_proxy(text) is True
    assert MODULE.obligation_hit("a doua propoziție", text) is True


def test_fail_closed_helpers():
    text, parsed = MODULE.unwrap_r2("not-json")
    assert parsed is False and text == "not-json"
    assert MODULE.functional_romanian_proxy("O singură propoziție.") is False
    assert MODULE.repeated("unu doi trei patru cinci șase unu doi trei patru cinci șase.") is True


def test_verified_hybrid_uses_binding_coverage_without_false_excluded_actor_drift():
    ledger = {
        "partition": "DEVELOPMENT", "failure_class": "TEST",
        "atoms": [
            {"selection": "REQUIRED", "actors_entities": ["Brașov"], "numbers": []},
            {"selection": "EXCLUDED", "actors_entities": ["Brașov"], "numbers": []},
        ],
        "obligations": [{"surface_requirement": "formulare care nu apare literal"}],
        "realization_contract": {
            "allowed_numbers": [], "required_epistemic_markers": [], "required_procedural_markers": []
        },
    }
    row = {"arm": "B2_HYBRID", "case_id": "x", "route": "HYBRID_ACCEPTED", "verified": True,
           "text": "Brașov are o situație descrisă clar. Verificarea rămâne în curs."}
    score = MODULE.score_row(ledger, row)
    assert score["material_drift"] is False
    assert score["required_obligations_hit"] == 1
    assert score["surface_obligations_hit"] == 0
