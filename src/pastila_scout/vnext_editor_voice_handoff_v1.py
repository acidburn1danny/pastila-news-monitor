"""Minimal, diagnostic-only EDITOR to VOICE handoff boundary."""
from __future__ import annotations

import hashlib
import json
from typing import Any


STATES = {
    "DEVELOPMENT_UNREVIEWED",
    "SOURCE_PRESERVING_FALLBACK",
    "ABSTAIN",
    "HUMAN_ACCEPTED",
}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def identify(value: dict[str, Any], field: str) -> dict[str, Any]:
    body = {key: item for key, item in value.items() if key != field}
    return {**body, field: hashlib.sha256(canonical(body)).hexdigest()}


def validate_source_packet(packet: dict[str, Any]) -> None:
    if packet.get("schema") != "editor-vnext-source-packet" or packet.get("schema_version") != 1:
        raise ValueError("invalid SourcePacket schema")
    expected = identify(packet, "packet_identity")["packet_identity"]
    if packet.get("packet_identity") != expected:
        raise ValueError("SourcePacket identity mismatch")
    if not packet.get("sources"):
        raise ValueError("SourcePacket has no sources")
    for source in packet["sources"]:
        text = source.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("source text missing")
        if source.get("text_sha256") != hashlib.sha256(text.encode()).hexdigest():
            raise ValueError("source text identity mismatch")


def make_editor_setup_packet(
    source_packet: dict[str, Any], editor_receipt: dict[str, Any], setup_text: str | None,
    state: str, *, human_acceptance: dict[str, str] | None = None,
) -> dict[str, Any]:
    validate_source_packet(source_packet)
    if state not in STATES:
        raise ValueError("unknown acceptance state")
    if editor_receipt.get("source_packet_identity") != source_packet["packet_identity"]:
        raise ValueError("editor receipt is not bound to SourcePacket")
    if editor_receipt.get("structural_valid") is not True:
        raise ValueError("editor structural boundary did not pass")
    if state == "ABSTAIN":
        if setup_text not in (None, ""):
            raise ValueError("ABSTAIN cannot carry setup text")
    elif not isinstance(setup_text, str) or not setup_text.strip():
        raise ValueError("non-abstention state requires setup text")
    if state == "SOURCE_PRESERVING_FALLBACK":
        allowed = {source["text"] for source in source_packet["sources"]}
        if setup_text not in allowed:
            raise ValueError("fallback must preserve one complete source text byte-for-byte")
    if state == "HUMAN_ACCEPTED":
        required = {"reviewer_id", "reviewed_at", "review_receipt_identity"}
        if not human_acceptance or set(human_acceptance) != required or not all(human_acceptance.values()):
            raise ValueError("HUMAN_ACCEPTED requires an explicit external review receipt")
    elif human_acceptance is not None:
        raise ValueError("human acceptance metadata is only valid for HUMAN_ACCEPTED")
    packet = {
        "schema": "editor-vnext-editor-setup-packet", "schema_version": 1,
        "source_packet_identity": source_packet["packet_identity"],
        "editor_receipt_identity": editor_receipt["receipt_identity"],
        "editor_runtime_lock_identity": editor_receipt["runtime_lock_identity"],
        "acceptance_state": state,
        "setup_text": setup_text,
        "setup_text_sha256": hashlib.sha256((setup_text or "").encode()).hexdigest(),
        "human_acceptance": human_acceptance,
        "production_factual_acceptance_authority": state == "HUMAN_ACCEPTED",
    }
    return identify(packet, "editor_setup_packet_identity")


def make_voice_input(setup: dict[str, Any]) -> dict[str, Any]:
    if identify(setup, "editor_setup_packet_identity")["editor_setup_packet_identity"] != setup.get("editor_setup_packet_identity"):
        raise ValueError("EditorSetupPacket identity mismatch")
    if setup["acceptance_state"] == "ABSTAIN":
        raise ValueError("ABSTAIN cannot enter VOICE")
    voice = {
        "schema": "editor-vnext-voice-input", "schema_version": 1,
        "editor_setup_packet_identity": setup["editor_setup_packet_identity"],
        "factual_setup": setup["setup_text"],
        "factual_setup_sha256": setup["setup_text_sha256"],
        "acceptance_state": setup["acceptance_state"],
        "development_only": setup["acceptance_state"] != "HUMAN_ACCEPTED",
        "voice_may_add_factual_claims": False,
        "voice_must_preserve_factual_setup": True,
    }
    return identify(voice, "voice_input_identity")
