"""Minimal localhost capture tool for the frozen VNext VOICE blind review."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

BOUNDARY_ID = "104252702c6bb27585e3615ffec0667aa519649a54275e641aeb7be826096d0e"
FORBIDDEN = {"candidate_id", "model_name", "model_revision", "tokenizer_identity", "candidate_receipt", "dispatch_identity"}
QUALITY = ("romanian_naturalness", "relevance", "sarcasm_irony_roast", "pastila_acida_style", "non_generic", "restraint", "target_choice")
REPETITION_BOOL = ("exact_duplicate", "normalized_phrase_reuse", "cross_case_template_reuse")
FACTUAL = {"PASS", "STOP_FACTUAL_DRIFT", "ABSTENTION_VALID"}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def identified(value: dict, field: str) -> dict:
    core = {key: item for key, item in value.items() if key != field}
    return {**core, field: hashlib.sha256(canonical(core)).hexdigest()}


def load_boundary(root: Path) -> tuple[dict, list[dict], dict]:
    boundary = json.loads((root / "editor-vnext-voice-blind-review-scoring-boundary-v1.json").read_text(encoding="utf-8"))
    schema = json.loads((root / "editor-vnext-voice-score-receipt-schema-v1.json").read_text(encoding="utf-8"))
    items = [json.loads(line) for line in (root / "editor-vnext-voice-blind-review-items-v1.jsonl").read_bytes().splitlines()]
    assert boundary["review_boundary_identity"] == BOUNDARY_ID
    assert boundary["blindness"]["answer_key"] == "SEALED" and boundary["blindness"]["answer_key_runtime_access"] == "FORBIDDEN"
    assert boundary["inventory"] == {"outputs": 216, "review_items": 216, "human_scores": 0}
    assert len(items) == len({item["blind_output_identity"] for item in items}) == 216
    assert schema["candidate_fields_forbidden"] and schema["atomic_no_overwrite"] and schema["content_addressed"]
    assert all(not (FORBIDDEN & item.keys()) for item in items)
    items.sort(key=lambda item: hashlib.sha256((BOUNDARY_ID + ":" + item["blind_output_identity"]).encode()).hexdigest())
    return boundary, items, schema


def validate_submission(item: dict, form: dict[str, str], reviewer_alias: str) -> dict:
    if not reviewer_alias.strip():
        raise ValueError("reviewer alias is required")
    factual = form.get("factual_safety", "")
    if factual not in FACTUAL:
        raise ValueError("invalid factual-safety verdict")
    quality = {field: int(form[field]) for field in QUALITY}
    if any(value < 1 or value > 5 for value in quality.values()):
        raise ValueError("quality scores must be integers from 1 through 5")
    repetition = {field: form.get(field) == "true" for field in REPETITION_BOOL}
    repetition["human_perceived_repetition"] = int(form["human_perceived_repetition"])
    if repetition["human_perceived_repetition"] not in range(1, 6):
        raise ValueError("human-perceived repetition must be 1 through 5")
    repetition["seed_stability_finding"] = form.get("seed_stability_finding", "")
    if repetition["seed_stability_finding"] not in {"STABLE", "VARIABLE", "NOT_ASSESSABLE"}:
        raise ValueError("invalid seed-stability finding")
    receipt = {
        "schema": "editor-vnext-voice-score-receipt", "schema_version": 1,
        "review_boundary_identity": BOUNDARY_ID,
        "blind_output_identity": item["blind_output_identity"], "case_identity": item["case_identity"],
        "seed_alias": item["seed_alias"], "factual_safety": factual, "quality": quality,
        "repetition": repetition, "completion_state": "COMPLETE",
        "reviewer_alias": reviewer_alias.strip(), "reviewed_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    assert not (FORBIDDEN & receipt.keys())
    return identified(receipt, "reviewer_receipt_identity")


def write_receipt(receipts: Path, receipt: dict) -> Path:
    receipts.mkdir(parents=True, exist_ok=True)
    target = receipts / f'{receipt["blind_output_identity"]}.json'
    temporary = receipts / f'.{receipt["blind_output_identity"]}.tmp'
    if target.exists() or temporary.exists():
        raise FileExistsError(target)
    payload = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
    with temporary.open("xb") as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    try:
        os.link(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def preflight(root: Path, receipts: Path) -> dict:
    _, items, _ = load_boundary(root)
    existing = list(receipts.glob("*.json")) if receipts.exists() else []
    expected = {item["blind_output_identity"] for item in items}
    if any(path.stem not in expected for path in existing):
        raise ValueError("unexpected receipt identity")
    complete = 0
    for path in existing:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if receipt.get("completion_state") != "COMPLETE" or receipt.get("review_boundary_identity") != BOUNDARY_ID:
            raise ValueError("invalid existing receipt")
        if identified(receipt, "reviewer_receipt_identity")["reviewer_receipt_identity"] != receipt.get("reviewer_receipt_identity"):
            raise ValueError("receipt identity drift")
        complete += 1
    return {"status": "PASS_CAPTURE_READY", "boundary_identity": BOUNDARY_ID, "items": 216, "receipts": complete,
            "remaining": 216 - complete, "answer_key": "SEALED", "candidate_mapping_disclosed": False,
            "automated_scoring": False, "legacy_dependency_count": 0}


def page(item: dict, index: int, complete: int, reviewer: str) -> bytes:
    options = "".join(f'<option value="{n}">{n}</option>' for n in range(1, 6))
    quality = "".join(f'<label>{html.escape(field)} <select name="{field}" required>{options}</select></label>' for field in QUALITY)
    checks = "".join(f'<label><input type="checkbox" name="{field}" value="true"> {html.escape(field)}</label>' for field in REPETITION_BOOL)
    body = f'''<!doctype html><meta charset="utf-8"><title>VOICE blind review</title>
<style>body{{font:16px system-ui;max-width:920px;margin:30px auto}}article{{padding:16px;background:#f3f3f3}}label{{display:block;margin:10px 0}}textarea{{width:100%}}.scores{{columns:2}}</style>
<h1>Blind review {index + 1}/216</h1><p>Complete: {complete}; answer key: SEALED.</p>
<article><b>Factual setup</b><p>{html.escape(item['factual_setup'])}</p><b>Commentary</b><p>{html.escape(item['commentary'])}</p><p>Abstained: {str(item['abstained']).lower()}</p></article>
<form method="post" action="/receipt"><input type="hidden" name="blind_output_identity" value="{item['blind_output_identity']}">
<p>Reviewer: <b>{html.escape(reviewer)}</b></p><input type="hidden" name="reviewer_alias" value="{html.escape(reviewer)}">
<label>Factual safety <select name="factual_safety" required><option>PASS</option><option>STOP_FACTUAL_DRIFT</option><option>ABSTENTION_VALID</option></select></label>
<div class="scores">{quality}</div><fieldset><legend>Repetition</legend>{checks}
<label>Human perceived repetition (1 low, 5 high) <select name="human_perceived_repetition" required>{options}</select></label>
<label>Seed stability <select name="seed_stability_finding"><option>NOT_ASSESSABLE</option><option>STABLE</option><option>VARIABLE</option></select></label></fieldset>
<button type="submit">Complete immutable receipt</button></form>'''
    return body.encode()


def handler_for(root: Path, receipts: Path, reviewer_alias: str):
    if not reviewer_alias.strip(): raise ValueError("bound reviewer alias is required")
    _, items, _ = load_boundary(root)
    by_identity = {item["blind_output_identity"]: item for item in items}
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state = preflight(root, receipts); done = {p.stem for p in receipts.glob("*.json")} if receipts.exists() else set()
            pending = [(i, item) for i, item in enumerate(items) if item["blind_output_identity"] not in done]
            if not pending:
                payload = b"216/216 complete. STOP before unseal."
            else:
                i, item = pending[0]; payload = page(item, i, state["receipts"], reviewer_alias)
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)
        def do_POST(self):
            if self.path != "/receipt": self.send_error(404); return
            length = int(self.headers.get("Content-Length", "0")); form = {k: v[-1] for k, v in parse_qs(self.rfile.read(length).decode(), keep_blank_values=True).items()}
            try:
                item = by_identity[form.pop("blind_output_identity")]; form["reviewer_alias"] = reviewer_alias; receipt = validate_submission(item, form, reviewer_alias); write_receipt(receipts, receipt)
            except (KeyError, ValueError, FileExistsError) as error:
                self.send_error(409, str(error)); return
            self.send_response(303); self.send_header("Location", "/"); self.end_headers()
        def log_message(self, *_): pass
    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--boundary-root", type=Path, required=True); parser.add_argument("--receipts-root", type=Path, required=True)
    parser.add_argument("--preflight", action="store_true"); parser.add_argument("--reviewer-alias"); parser.add_argument("--host", default="127.0.0.1"); parser.add_argument("--port", type=int, default=8765); args = parser.parse_args()
    state = preflight(args.boundary_root, args.receipts_root)
    if args.preflight: print(json.dumps(state, sort_keys=True)); return
    if args.host not in {"127.0.0.1", "localhost"}: raise SystemExit("review server must bind localhost")
    if not args.reviewer_alias: raise SystemExit("--reviewer-alias is required when serving")
    print(json.dumps(state, sort_keys=True)); ThreadingHTTPServer((args.host, args.port), handler_for(args.boundary_root, args.receipts_root, args.reviewer_alias)).serve_forever()


if __name__ == "__main__": main()
