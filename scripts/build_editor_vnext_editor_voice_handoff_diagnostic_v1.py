"""Build deterministic fixtures and result for the EDITOR to VOICE handoff diagnostic."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.vnext_editor_voice_handoff_v1 import identify, make_editor_setup_packet, make_voice_input


ROOT = Path(__file__).resolve().parents[1]


def write(path: Path, value: object) -> None:
    path.write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")


def main() -> None:
    text_a = "Consiliul local din Brașov a aprobat 127 de milioane de lei pentru centrul medical Arin."
    text_b = "Ministerul a precizat că finanțarea este aprobată, dar contractul nu a fost încă semnat."
    source = {
        "schema": "editor-vnext-source-packet", "schema_version": 1, "event_id": "fixture:arin",
        "sources": [
            {"source_id": "fixture_public", "article_url": "https://fixture.invalid/public/arin", "text": text_a, "text_sha256": hashlib.sha256(text_a.encode()).hexdigest()},
            {"source_id": "fixture_ministry", "article_url": "https://fixture.invalid/ministry/arin", "text": text_b, "text_sha256": hashlib.sha256(text_b.encode()).hexdigest()},
        ],
    }
    source = identify(source, "packet_identity")
    receipt = identify({
        "schema": "editor-vnext-v0-terminal-receipt", "schema_version": 1,
        "source_packet_identity": source["packet_identity"], "structural_valid": True,
        "runtime_lock_identity": "58b22d87a50f9eb28592043e1fdeb1ba6eb841b2e103b65f30ebd710785731ca",
    }, "receipt_identity")
    fixture = {
        "schema": "editor-vnext-editor-voice-handoff-fixtures", "schema_version": 1,
        "source_packet": source, "editor_receipt": receipt,
        "setup_text": "Consiliul local din Brașov a aprobat 127 de milioane de lei pentru centrul medical Arin. Ministerul a precizat că finanțarea este aprobată, dar contractul nu a fost încă semnat.",
        "human_acceptance": {"reviewer_id": "fixture-reviewer", "reviewed_at": "2026-09-28T12:00:00Z", "review_receipt_identity": "f" * 64},
    }
    fixture = identify(fixture, "fixture_identity")
    setups = {
        state: make_editor_setup_packet(source, receipt, None if state == "ABSTAIN" else (text_a if state == "SOURCE_PRESERVING_FALLBACK" else fixture["setup_text"]), state,
            human_acceptance=fixture["human_acceptance"] if state == "HUMAN_ACCEPTED" else None)
        for state in ("DEVELOPMENT_UNREVIEWED", "SOURCE_PRESERVING_FALLBACK", "ABSTAIN", "HUMAN_ACCEPTED")
    }
    result = identify({
        "schema": "editor-vnext-editor-voice-handoff-diagnostic-result", "schema_version": 1,
        "status": "PASS_DIAGNOSTIC_ONLY", "fixture_identity": fixture["fixture_identity"],
        "setup_packet_identities": {key: value["editor_setup_packet_identity"] for key, value in setups.items()},
        "voice_input_identities": {key: make_voice_input(value)["voice_input_identity"] for key, value in setups.items() if key != "ABSTAIN"},
        "enforcement_enabled": False, "production_acceptance_policy_changed": False,
        "legacy_dependency_count": 0,
        "terminal_rule": "CONTINUE_TO_VOICE_RUNTIME_INVENTORY_WITH_DEVELOPMENT_ONLY_BOUNDARY",
    }, "result_identity")
    artifacts = ROOT / "docs/artifacts"
    write(artifacts / "editor-vnext-editor-voice-handoff-fixtures-v1.json", fixture)
    write(artifacts / "editor-vnext-editor-voice-handoff-result-v1.json", result)
    print(json.dumps({"status": result["status"], "result_identity": result["result_identity"]}, sort_keys=True))


if __name__ == "__main__":
    main()
