import importlib.util
from pathlib import Path


SCRIPT = Path("scripts/evaluate_editor_core_r2_factorized_fact_plan_closed_v1.py")
SPEC = importlib.util.spec_from_file_location("factorized_closed_eval", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def plan():
    return {
        "oracle_setup_target": "Consiliul a aprobat 127 de lei. Contractul nu a fost încă semnat.",
        "selected_facts": [
            {"surface_requirement": "127 de lei"},
            {"surface_requirement": "nu a fost încă semnat"},
        ],
        "authority_inventory": [
            {"text": "Consiliul a aprobat 127 de lei."},
            {"text": "Contractul nu a fost încă semnat."},
            {"text": "Stadionul primește 19 lei."},
        ],
        "epistemic_status": {"markers": []},
        "procedural_status": {"markers": ["nu a fost încă"]},
    }


def test_valid_contract_setup_gets_factual_and_sufficiency_credit():
    raw = '{"schema_version":1,"sentence_budget":2,"text":"Consiliul a aprobat 127 de lei. Contractul nu a fost încă semnat."}'
    score = MODULE.score_setup(raw, plan())
    assert score["contract_valid"]
    assert score["text_extracted"]
    assert score["factual_safety_pass"]
    assert score["sufficiency_pass"]


def test_non_contract_json_fails_closed_without_semantic_credit():
    raw = '{"schema_version":1,"answer":"Consiliul a aprobat 127 de lei. Contractul nu a fost încă semnat."}'
    score = MODULE.score_setup(raw, plan())
    assert not score["contract_valid"]
    assert not score["text_extracted"]
    assert not score["factual_safety_pass"]
    assert not score["sufficiency_pass"]
    assert score["structural_errors"] == ["MISSING_CONTRACT_TEXT"]


def test_distractor_number_and_novel_actor_fail_safety():
    raw = '{"text":"Birocrația a aprobat 127 și 19 lei. Contractul nu a fost încă semnat."}'
    score = MODULE.score_setup(raw, plan())
    assert score["distractor_numbers"] == ["19"]
    assert score["novel_actor_terms"] == ["birocrația"]
    assert not score["factual_safety_pass"]


def test_identity_hash_excludes_identity_field_by_construction():
    core = {"schema": "x", "rows": 48}
    identity = MODULE.sha256_bytes(MODULE.canonical(core))
    assert identity == MODULE.sha256_bytes(MODULE.canonical({"rows": 48, "schema": "x"}))
