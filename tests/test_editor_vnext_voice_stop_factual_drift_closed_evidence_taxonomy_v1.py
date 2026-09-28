import json
from pathlib import Path

from scripts.analyze_editor_vnext_voice_stop_factual_drift_closed_evidence_taxonomy_v1 import (
    CAUSAL,
    CONCRETE,
    EPISTEMIC,
    FIGURATIVE,
    LIMITATION,
    NUMERIC,
    canonical,
)


RESULT = Path("docs/artifacts/editor-vnext-voice-stop-factual-drift-closed-evidence-taxonomy-v1.json")


def load():
    return json.loads(RESULT.read_text(encoding="utf-8"))


def test_result_identity_and_frozen_bindings():
    value = load()
    identity = value.pop("taxonomy_result_identity")
    import hashlib

    assert hashlib.sha256(canonical(value)).hexdigest() == identity
    assert value["bindings"]["frozen_terminal_result_identity"] == (
        "5f521de2625e73db9d6958536b57799b190a0583fc26e2c03fea1fbaf8923ea3"
    )
    assert value["frozen_state"]["overall_verdict"] == "STOP_ALL_CANDIDATES"
    assert value["frozen_state"]["selected_candidate"] is None
    assert value["frozen_state"]["legacy_dependency_count"] == 0


def test_74_stop_closure_and_candidate_distribution():
    value = load()
    evidence = value["closed_evidence"]
    assert evidence["review_items"] == evidence["score_receipts"] == evidence["inference_outputs"] == 216
    assert evidence["stop_factual_drift"] == 74
    assert evidence["per_candidate"] == {
        "V0_R2_MINISTRAL_CONTROL": 27,
        "V1_QWEN3_8B_NON_THINKING": 44,
        "V2_QWEN25_7B_INSTRUCT": 3,
    }


def test_taxonomy_and_evidence_limitations_are_closed():
    taxonomy = load()["taxonomy"]
    assert taxonomy["receipt_weighted_total"] == {
        CONCRETE: 24,
        NUMERIC: 9,
        EPISTEMIC: 9,
        CAUSAL: 15,
        FIGURATIVE: 12,
        LIMITATION: 5,
    }
    assert len(taxonomy["evidence_limitation_receipts"]) == 5
    assert len(taxonomy["mixed_label_byte_identical_groups"]) == 1
    mixed = taxonomy["mixed_label_byte_identical_groups"][0]
    assert mixed["candidate"] == "V1_QWEN3_8B_NON_THINKING"
    assert mixed["case_id"] == "VOICE-V1-18"
    assert mixed["labels"] == {"PASS": 1, "STOP_FACTUAL_DRIFT": 2}
    assert len(mixed["receipts"]) == 2


def test_checkpoint_declares_no_evidence_mutation():
    frozen = load()["frozen_state"]
    for field in (
        "receipts_modified",
        "scores_modified",
        "verdicts_modified",
        "inference_outputs_modified",
        "rescoring",
        "new_inference",
    ):
        assert frozen[field] is False
