import copy
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.vnext_editor_voice_handoff_v1 import identify, make_editor_setup_packet, make_voice_input


def load_fixture():
    return json.loads(Path("docs/artifacts/editor-vnext-editor-voice-handoff-fixtures-v1.json").read_text(encoding="utf-8"))


def test_all_declared_states_and_voice_boundary():
    fixture = load_fixture()
    source, receipt = fixture["source_packet"], fixture["editor_receipt"]
    dev = make_editor_setup_packet(source, receipt, fixture["setup_text"], "DEVELOPMENT_UNREVIEWED")
    assert make_voice_input(dev)["development_only"] is True
    fallback = make_editor_setup_packet(source, receipt, source["sources"][0]["text"], "SOURCE_PRESERVING_FALLBACK")
    assert make_voice_input(fallback)["factual_setup"] == source["sources"][0]["text"]
    abstain = make_editor_setup_packet(source, receipt, None, "ABSTAIN")
    with pytest.raises(ValueError, match="ABSTAIN"):
        make_voice_input(abstain)
    human = make_editor_setup_packet(source, receipt, fixture["setup_text"], "HUMAN_ACCEPTED", human_acceptance=fixture["human_acceptance"])
    assert make_voice_input(human)["development_only"] is False


def test_identity_and_binding_attacks_fail_closed():
    fixture = load_fixture()
    for mutation, message in [
        (("source", "text"), "source text identity"),
        (("receipt", "source_packet_identity"), "not bound"),
    ]:
        source, receipt = copy.deepcopy(fixture["source_packet"]), copy.deepcopy(fixture["editor_receipt"])
        if mutation[0] == "source":
            source["sources"][0][mutation[1]] += " tampered"
            source = identify(source, "packet_identity")
        else:
            receipt[mutation[1]] = "0" * 64
        with pytest.raises(ValueError, match=message):
            make_editor_setup_packet(source, receipt, fixture["setup_text"], "DEVELOPMENT_UNREVIEWED")


def test_fallback_and_human_acceptance_are_narrow():
    fixture = load_fixture(); source, receipt = fixture["source_packet"], fixture["editor_receipt"]
    with pytest.raises(ValueError, match="preserve"):
        make_editor_setup_packet(source, receipt, "A shortened fallback.", "SOURCE_PRESERVING_FALLBACK")
    with pytest.raises(ValueError, match="external review"):
        make_editor_setup_packet(source, receipt, fixture["setup_text"], "HUMAN_ACCEPTED")


def test_contract_and_decision_table_keep_enforcement_disabled():
    contract = json.loads(Path("docs/artifacts/editor-vnext-editor-voice-handoff-contract-v1.json").read_text(encoding="utf-8"))
    table = json.loads(Path("docs/artifacts/editor-vnext-editor-voice-handoff-decision-table-v1.json").read_text(encoding="utf-8"))
    assert contract["enforcement_enabled"] is False
    assert contract["forbidden_components"] == ["EVIDENCE_PACKET", "FACTUAL_LEDGER", "MODEL_JUDGE", "NLI", "SELECTOR"]
    assert table["DEVELOPMENT_UNREVIEWED"]["production_publish"] is False
    assert table["SOURCE_PRESERVING_FALLBACK"]["production_publish"] is False
    assert table["ABSTAIN"]["voice_allowed"] is False
    assert table["HUMAN_ACCEPTED"]["automatic"] is False
