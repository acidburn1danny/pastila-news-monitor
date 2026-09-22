"""Fixture-only scoring; synthetic ratings are never human decisions."""

from __future__ import annotations

import json
import sys
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_editor_core_bridge_blind_scoring import audit_prepared, prepare  # noqa: E402
from record_editor_core_bridge_blind_score import record, reference_handoff, verify  # noqa: E402
from serve_editor_core_bridge_blind_scoring import handler_for, validate_handoff  # noqa: E402
from test_editor_core_bridge_causal_route import fixture_responses  # noqa: E402


def roots(tmp_path):
    paths = [tmp_path / part for part in ("responses", "packets", "reference", "custody", "scores", "reference_scores")]
    for path in paths:
        path.mkdir()
    fixture_responses(paths[0])
    prepare(*paths[:4], permutation=lambda: [0, 1])
    return paths


def primary_score():
    return {"factual": {"X": "PASS", "Y": "PASS"}, "editorial": {"X": "PASS", "Y": "PASS"},
            "romanian": {"X": "PASS", "Y": "PASS"}, "winner": "TIE", "note": ""}


def reference_score():
    return {"factual": {"R2": "PASS"}, "editorial": {"R2": "PASS"},
            "romanian": {"R2": "PASS"}, "note": ""}


def test_fixture_handoff_and_append_only_closure(tmp_path):
    _, packets, reference, custody, scores, reference_scores = roots(tmp_path)
    assert audit_prepared(packets, reference, custody)["primary_count"] == 72
    reviewer = "FIXTURE_ONLY_REVIEWER"
    with pytest.raises(ValueError, match="incomplete"):
        reference_handoff(packets, scores, reference, reviewer)
    for packet in packets.iterdir():
        record(packet, scores, "primary", reviewer, primary_score())
    with pytest.raises(FileExistsError):
        record(next(packets.iterdir()), scores, "primary", reviewer, primary_score())
    closure = verify(packets, scores, "primary", reviewer, lock=True)
    assert closure["count"] == 72
    assert verify(packets, scores, "primary", reviewer) == closure
    handoff = reference_handoff(packets, scores, reference, reviewer)
    assert handoff["primary_closure_identity"] == closure["closure_identity"]
    for packet in reference.iterdir():
        record(packet, reference_scores, "reference", reviewer, reference_score(),
               primary_packets=packets, primary_scores=scores)
    assert verify(reference, reference_scores, "reference", reviewer, lock=True)["count"] == 24


def test_fixture_mutation_replay_wrong_identity_and_incomplete(tmp_path):
    _, packets, reference, _, scores, reference_scores = roots(tmp_path)
    first = next(packets.iterdir())
    record(first, scores, "primary", "FIXTURE_ONLY_REVIEWER", primary_score())
    with pytest.raises(ValueError, match="incomplete"):
        verify(packets, scores, "primary", "FIXTURE_ONLY_REVIEWER", lock=True)
    with pytest.raises(ValueError, match="primary closure"):
        record(next(reference.iterdir()), reference_scores, "reference", "FIXTURE_ONLY_REVIEWER",
               reference_score())
    with pytest.raises(ValueError, match="reason"):
        bad = primary_score()
        bad["factual"]["X"] = "FAIL"
        record(list(packets.iterdir())[1], scores, "primary", "FIXTURE_ONLY_REVIEWER", bad)
    receipt = scores / f"{json.loads(first.read_bytes())['packet_id']}.score.json"
    saved = receipt.read_bytes()
    obj = json.loads(saved)
    obj["reviewer_id"] = "OTHER_REVIEWER"
    receipt.write_bytes(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    with pytest.raises(ValueError, match="binding"):
        from record_editor_core_bridge_blind_score import _validate_record
        _validate_record(receipt, first, "primary", "FIXTURE_ONLY_REVIEWER")
    receipt.write_bytes(saved)
    with pytest.raises(ValueError, match="binding"):
        from record_editor_core_bridge_blind_score import _validate_record
        _validate_record(receipt, list(packets.iterdir())[1], "primary", "FIXTURE_ONLY_REVIEWER")


def test_fixture_packet_tamper_and_unexpected_file(tmp_path):
    _, packets, reference, custody, scores, _ = roots(tmp_path)
    first = next(packets.iterdir())
    saved = first.read_bytes()
    with pytest.raises(ValueError, match="packet identity"):
        changed = json.loads(first.read_bytes())
        changed["operator"] = "mutated"
        first.write_bytes(json.dumps(changed, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
        record(first, scores, "primary", "FIXTURE_ONLY_REVIEWER", primary_score())
    with pytest.raises(ValueError, match="packet identity"):
        audit_prepared(packets, reference, custody)
    first.write_bytes(saved)
    (scores / "unexpected.txt").write_text("x")
    with pytest.raises(ValueError, match="incomplete/extra"):
        verify(packets, scores, "primary", "FIXTURE_ONLY_REVIEWER")


def test_fixture_browser_handoff_save_resume_and_token(tmp_path):
    _, packets, _, _, scores, _ = roots(tmp_path)
    validate_handoff(packets, scores, "primary", None, None)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(
        packets, scores, "primary", "FIXTURE_ONLY_REVIEWER", "fixture-token", None, None))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", server.server_port)
        conn.request("GET", "/?token=wrong")
        assert conn.getresponse().status == 403
        conn.request("GET", "/?token=fixture-token")
        response = conn.getresponse()
        body = response.read().decode()
        assert response.status == 200 and "Revizie editorială blind" in body
        assert "a1-seed" not in body.lower() and "a2-seed" not in body.lower()
        from urllib.parse import urlencode
        form = {f"{name}_{label}": "PASS" for name in ("factual", "editorial", "romanian")
                for label in ("X", "Y")}
        form["winner"] = "TIE"
        conn.request("POST", "/save?token=fixture-token", urlencode(form),
                     {"Content-Type": "application/x-www-form-urlencoded"})
        assert conn.getresponse().status == 303
        assert len(list(scores.glob("*.score.json"))) == 1
        conn.request("GET", "/?token=fixture-token")
        response = conn.getresponse()
        assert response.status == 200 and "2 / 72" in response.read().decode()
        conn.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
