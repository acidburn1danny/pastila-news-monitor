import json
import threading
import uuid
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from scripts.serve_editor_vnext_voice_blind_human_review_v1 import BOUNDARY_ID, FORBIDDEN, handler_for, load_boundary, preflight, validate_submission, write_receipt

ROOT = Path("docs/artifacts")


def form():
    value = {field: "3" for field in ("romanian_naturalness", "relevance", "sarcasm_irony_roast", "pastila_acida_style", "non_generic", "restraint", "target_choice")}
    return {**value, "factual_safety": "PASS", "human_perceived_repetition": "2", "seed_stability_finding": "NOT_ASSESSABLE"}


def test_frozen_boundary_loads_blind():
    boundary, items, _ = load_boundary(ROOT)
    assert boundary["review_boundary_identity"] == BOUNDARY_ID and len(items) == 216
    assert all(not (FORBIDDEN & item.keys()) for item in items)
    raw = [json.loads(line)["blind_output_identity"] for line in (ROOT / "editor-vnext-voice-blind-review-items-v1.jsonl").read_bytes().splitlines()]
    assert [item["blind_output_identity"] for item in items] != raw
    assert [item["blind_output_identity"] for item in items] == [item["blind_output_identity"] for item in load_boundary(ROOT)[1]]


def test_preflight_zero_review():
    path = Path(f".voice-human-review-test-{uuid.uuid4().hex}"); path.mkdir()
    try: assert preflight(ROOT, path)["receipts"] == 0 and preflight(ROOT, path)["answer_key"] == "SEALED"
    finally: path.rmdir()


def test_human_submission_is_content_addressed_and_has_no_candidate():
    item = load_boundary(ROOT)[1][0]; receipt = validate_submission(item, form(), "human-reviewer")
    assert receipt["completion_state"] == "COMPLETE" and len(receipt["reviewer_receipt_identity"]) == 64
    assert not (FORBIDDEN & receipt.keys())


def test_scores_are_strictly_validated():
    item = load_boundary(ROOT)[1][0]; invalid = form(); invalid["relevance"] = "6"
    try: validate_submission(item, invalid, "human-reviewer")
    except ValueError: pass
    else: raise AssertionError("invalid score accepted")


def test_atomic_no_overwrite():
    root = Path(f".voice-human-review-test-{uuid.uuid4().hex}"); root.mkdir(); item = load_boundary(ROOT)[1][0]
    try:
        receipt = validate_submission(item, form(), "human-reviewer"); target = write_receipt(root, receipt)
        before = target.read_bytes()
        try: write_receipt(root, receipt)
        except FileExistsError: pass
        else: raise AssertionError("receipt overwrite accepted")
        assert target.read_bytes() == before and preflight(ROOT, root)["receipts"] == 1
    finally:
        for path in root.iterdir(): path.unlink()
        root.rmdir()


def test_no_scoring_or_unseal_capability():
    source = Path("scripts/serve_editor_vnext_voice_blind_human_review_v1.py").read_text(encoding="utf-8")
    assert "answer_key.json" not in source and "dispatch manifest" not in source
    assert "winner" not in source.lower() and "model selection" not in source.lower()


def test_localhost_blind_render_contains_no_candidate_metadata():
    receipts = Path(f".voice-human-review-test-{uuid.uuid4().hex}"); receipts.mkdir()
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(ROOT, receipts, "Daniel")); thread = threading.Thread(target=server.serve_forever); thread.start()
    try:
        body = urllib.request.urlopen(f"http://127.0.0.1:{server.server_port}/", timeout=5).read().decode()
        assert "Blind review" in body and "answer key: SEALED" in body and "Reviewer: <b>Daniel</b>" in body
        assert not any(field in body for field in FORBIDDEN)
    finally:
        server.shutdown(); server.server_close(); thread.join(); receipts.rmdir()
