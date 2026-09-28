import json
from pathlib import Path

from scripts.aggregate_editor_vnext_voice_blind_review_v1 import ANSWER, BOUNDARY, canonical
import hashlib

RESULT = Path("docs/artifacts/editor-vnext-voice-blind-review-terminal-result-v1.json")


def load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_result_identity_reproduces():
    value = load(); core = {key: item for key, item in value.items() if key != "unsealed_result_identity"}
    assert hashlib.sha256(canonical(core)).hexdigest() == value["unsealed_result_identity"]


def test_frozen_bindings_and_terminal_verdict():
    value = load()
    assert value["boundary_identity"] == BOUNDARY and value["answer_key_identity"] == ANSWER
    assert value["scoring_closure_identity"] == "a94d44bcf6e677d62a7715a1631544e7f6659a59d277fd674e46bc51f25ac768"
    assert value["overall_verdict"] == "STOP_ALL_CANDIDATES" and value["selected_candidate"] is None
    assert {item["verdict"] for item in value["terminal"].values()} == {"STOP"}


def test_factual_stop_counts_and_no_promotion():
    value = load(); expected = {"V0_R2_MINISTRAL_CONTROL": 27, "V1_QWEN3_8B_NON_THINKING": 44, "V2_QWEN25_7B_INSTRUCT": 3}
    assert {candidate: result["factual_safety"]["STOP_FACTUAL_DRIFT"] for candidate, result in value["per_candidate"].items()} == expected
    assert value["execution"] == {"new_inference": False, "automated_semantic_rescoring": False, "receipts_modified": False, "promotion": False, "training": False, "optimizer": False}
    assert value["legacy_dependency_count"] == 0


def test_exact_candidate_inventory_and_seed_closure():
    value = load(); assert set(value["per_candidate"]) == set(value["mapping"])
    assert all(candidate["outputs"] == 72 and set(candidate["per_seed"]) == {"161803", "271828", "314159"} for candidate in value["per_candidate"].values())
