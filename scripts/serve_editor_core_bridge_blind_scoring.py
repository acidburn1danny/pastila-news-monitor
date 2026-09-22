"""Local browser form for one blind scoring phase; never opens sealed arm map."""

from __future__ import annotations

import argparse
import html
import json
import os
import secrets
import stat
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from record_editor_core_bridge_blind_score import _packet, record, reference_handoff, verify


def validate_handoff(packets: Path, scores: Path, phase: str,
                     primary_packets: Path | None, primary_scores: Path | None) -> None:
    roots = [packets, scores]
    if phase == "reference":
        if primary_packets is None or primary_scores is None:
            raise ValueError("primary closure roots required")
        roots.extend([primary_packets, primary_scores])
    if any(p.is_symlink() or not p.is_dir() for p in roots):
        raise ValueError("handoff root")
    resolved = [p.resolve() for p in roots]
    if any(a == b or a in b.parents or b in a.parents
           for i, a in enumerate(resolved) for b in resolved[i + 1:]):
        raise ValueError("handoff custody overlap")
    if os.name == "posix" and stat.S_IMODE(scores.stat().st_mode) != 0o700:
        raise ValueError("scores directory permissions")
    count = 72 if phase == "primary" else 24
    paths = list(packets.iterdir())
    if len(paths) != count:
        raise ValueError("packet inventory")
    for path in paths:
        _packet(path, phase)


def render(packet: dict, phase: str, index: int, total: int, token: str) -> bytes:
    escape = html.escape
    options = packet["options"] if phase == "primary" else [{"label": "R2", "response": packet["response"]}]
    fields = []
    for item in options:
        label = item["label"]
        fields.append(f"<h3>Text {escape(label)}</h3><pre>{escape(item['response'])}</pre>")
        for name, title in (("factual", "Fidelitate față de cerință și sursă"),
                            ("editorial", "Calitate editorială"), ("romanian", "Română naturală")):
            fields.append(f"<fieldset><legend>{escape(title)} — {escape(label)}</legend>")
            for value in ("PASS", "FAIL", "INDETERMINATE"):
                fields.append(f'<label><input type="radio" name="{name}_{label}" value="{value}" required>{value}</label> ')
            fields.append("</fieldset>")
    if phase == "primary":
        fields.append("<fieldset><legend>Care text răspunde mai bine, fără risc factual suplimentar?</legend>")
        for value in ("X", "Y", "TIE", "INDETERMINATE"):
            fields.append(f'<label><input type="radio" name="winner" value="{value}" required>{value}</label> ')
        fields.append("</fieldset>")
    request = escape(json.dumps(packet["request"], ensure_ascii=False, indent=2))
    body = ("<!doctype html><html lang='ro'><meta charset='utf-8'><title>Revizie editorială blind</title>"
            "<style>body{max-width:850px;margin:2rem auto;font:18px/1.5 sans-serif;padding:0 1rem}"
            "pre{white-space:pre-wrap;background:#f4f4f4;padding:1rem}fieldset{margin:1rem 0}"
            "button{font-size:1.1rem;padding:.7rem 1.3rem}</style>"
            f"<h1>Revizie editorială blind — {index} / {total}</h1>"
            "<p>Folosește doar cerința și sursa de mai jos. Nu căuta răspunsuri din alte cazuri. "
            "După salvare, cazul se blochează.</p>"
            f"<h2>Cerință și sursă</h2><pre>{request}</pre>"
            f"<form method='post' action='/save?token={escape(token)}'>" + "".join(fields)
            + "<label>Notă scurtă (obligatorie doar dacă ai marcat FAIL factual sau INDETERMINATE):"
            "<br><textarea name='note' rows='3' cols='70' maxlength='2000'></textarea></label><br>"
            "<button type='submit'>Finalizează cazul și continuă</button></form></html>")
    return body.encode("utf-8")


def handler_for(packets_root: Path, scores_root: Path, phase: str, reviewer: str, token: str,
                primary_packets: Path | None, primary_scores: Path | None):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            return parse_qs(urlsplit(self.path).query).get("token") == [token]

        def _pending(self):
            for path in sorted(packets_root.iterdir()):
                packet = _packet(path, phase)
                if not (scores_root / f"{packet['packet_id']}.score.json").exists():
                    return path, packet
            return None, None

        def do_GET(self):
            if not self._authorized() or urlsplit(self.path).path != "/":
                return self._send(403, b"Forbidden")
            if phase == "reference":
                reference_handoff(primary_packets, primary_scores, packets_root, reviewer)
            path, packet = self._pending()
            if packet is None:
                closure = verify(packets_root, scores_root, phase, reviewer, lock=True)
                return self._send(200, f"<h1>Faza finalizată</h1><p>{closure['count']} cazuri blocate.</p>".encode())
            completed = len(list(scores_root.glob("*.score.json")))
            return self._send(200, render(packet, phase, completed + 1, 72 if phase == "primary" else 24, token))

        def do_POST(self):
            if not self._authorized() or urlsplit(self.path).path != "/save":
                return self._send(403, b"Forbidden")
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 10000:
                return self._send(400, b"Invalid form size")
            form = parse_qs(self.rfile.read(length).decode("utf-8"), strict_parsing=True)
            path, packet = self._pending()
            if packet is None:
                return self._send(409, b"Phase complete")
            labels = ("X", "Y") if phase == "primary" else ("R2",)
            try:
                if any(len(values) != 1 for values in form.values()):
                    raise ValueError("duplicate form fields")
                score = {name: {label: form[f"{name}_{label}"][0] for label in labels}
                         for name in ("factual", "editorial", "romanian")}
                score["note"] = form.get("note", [""])[0]
                if phase == "primary":
                    score["winner"] = form["winner"][0]
                expected = {f"{name}_{label}" for name in ("factual", "editorial", "romanian") for label in labels}
                expected |= {"note"} if "note" in form else set()
                if phase == "primary":
                    expected.add("winner")
                if set(form) != expected:
                    raise ValueError("unexpected form field")
                record(path, scores_root, phase, reviewer, score,
                       primary_packets=primary_packets, primary_scores=primary_scores)
            except (KeyError, ValueError, FileExistsError) as exc:
                return self._send(400, f"<h1>Răspuns nesalvat</h1><p>{html.escape(str(exc))}</p>".encode())
            self.send_response(303)
            self.send_header("Location", f"/?token={token}")
            self.send_header("Content-Length", "0")
            self.end_headers()

    return Handler


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--packets", type=Path, required=True)
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--phase", choices=("primary", "reference"), required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--primary-packets", type=Path)
    parser.add_argument("--primary-scores", type=Path)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    validate_handoff(args.packets, args.scores, args.phase, args.primary_packets, args.primary_scores)
    if args.phase == "reference":
        reference_handoff(args.primary_packets, args.primary_scores, args.packets, args.reviewer)
    token = secrets.token_urlsafe(24)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_for(
        args.packets, args.scores, args.phase, args.reviewer, token, args.primary_packets, args.primary_scores))
    print(f"http://127.0.0.1:{server.server_port}/?token={token}", flush=True)
    server.serve_forever()
