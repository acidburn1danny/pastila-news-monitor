"""Minimal, standalone VNext SCOUT and SourcePacket orchestration."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path, PurePosixPath
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit

SCHEMA = "editor-vnext-source-packet"
SCHEMA_VERSION = 1
STOPWORDS = frozenset({"a", "al", "ale", "ai", "cu", "de", "din", "in", "la", "o", "pe", "si", "un", "unei", "unui"})
PROCEDURAL = ("aprobat", "adoptat", "anuntat", "ancheta", "condamnat", "contract", "decis", "dosar", "investigat", "propus", "semnat", "votat")
QUALIFICATION = ("ar putea", "a declarat", "a precizat", "conform", "estimeaza", "presupus", "sustine")


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def identity(value: dict, field: str) -> str:
    return hashlib.sha256(canonical({key: item for key, item in value.items() if key != field})).hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n")
    temporary.replace(path)


def normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", ascii_text))


def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), parts.path.rstrip("/") or "/", parts.query, ""))


def text_tokens(value: str) -> set[str]:
    return {token for token in normalize_text(value).split() if len(token) > 2 and token not in STOPWORDS}


def same_event(left: str, right: str) -> bool:
    a, b = text_tokens(left), text_tokens(right)
    if not a or not b:
        return False
    left_numbers = set(re.findall(r"\d+(?:[.,]\d+)*", left))
    right_numbers = set(re.findall(r"\d+(?:[.,]\d+)*", right))
    if left_numbers and right_numbers and left_numbers != right_numbers:
        return False
    overlap = len(a & b) / min(len(a), len(b))
    return overlap >= 0.60


def clean_text(value: str | None) -> str:
    return " ".join((value or "").split())


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def child_text(node: ET.Element, *names: str) -> str:
    wanted = {name.casefold() for name in names}
    for child in node.iter():
        if child is node:
            continue
        if local_name(child.tag) in wanted:
            text = clean_text("".join(child.itertext()))
            if text:
                return text
    return ""


def entry_link(node: ET.Element) -> str:
    for child in node.iter():
        if local_name(child.tag) == "link":
            href = clean_text(child.attrib.get("href"))
            if href:
                return href
            text = clean_text(child.text)
            if text:
                return text
    return child_text(node, "guid", "id")


def parse_time(value: str) -> str | None:
    value = clean_text(value)
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError, OverflowError):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC).isoformat().replace("+00:00", "Z")
        except ValueError:
            return None


@dataclass(frozen=True)
class CapturedArticle:
    source_id: str
    source_name: str
    source_url: str
    article_url: str
    title: str
    summary: str
    published_at: str | None
    categories: tuple[str, ...]
    capture_sha256: str


def parse_feed(payload: bytes, source: dict) -> list[CapturedArticle]:
    root = ET.fromstring(payload)
    nodes = [node for node in root.iter() if local_name(node.tag) in {"item", "entry"}]
    captured: list[CapturedArticle] = []
    feed_sha = hashlib.sha256(payload).hexdigest()
    for position, node in enumerate(nodes):
        title = child_text(node, "title")
        link = entry_link(node)
        summary = child_text(node, "description", "summary", "content")
        if not title or not link:
            continue
        article_core = {
            "source_id": source["id"], "source_name": source["name"], "source_url": source["url"],
            "article_url": normalize_url(link), "title": title, "summary": summary or title,
            "published_at": parse_time(child_text(node, "pubdate", "published", "updated")),
            "categories": tuple(source.get("categories", ())), "feed_sha256": feed_sha, "position": position,
        }
        captured.append(CapturedArticle(**{key: article_core[key] for key in CapturedArticle.__dataclass_fields__ if key != "capture_sha256"}, capture_sha256=hashlib.sha256(canonical(article_core)).hexdigest()))
    return captured[: int(source.get("max_articles_per_poll", 50))]


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object: {path}")
    return value


def verify_locked_runtime(root: Path) -> tuple[dict, dict]:
    lock = load_json(root / "dependency-lock.json")
    if identity(lock, "lock_identity") != lock.get("lock_identity"):
        raise ValueError("SCOUT dependency lock identity mismatch")
    expected = set()
    for item in lock["files"]:
        relative = PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("non-canonical dependency path")
        path = root.joinpath(*relative.parts)
        if path.is_symlink() or not path.is_file() or path.stat().st_size != item["size"] or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"SCOUT dependency mismatch: {relative}")
        expected.add(relative.as_posix())
    actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.name != "dependency-lock.json"}
    if actual != expected:
        raise ValueError("unlocked SCOUT runtime file")
    contract = load_json(root / "sourcepacket-contract.json")
    if identity(contract, "contract_identity") != contract.get("contract_identity"):
        raise ValueError("SourcePacket contract identity mismatch")
    return lock, contract


def open_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS sources (
            source_id TEXT PRIMARY KEY, name TEXT NOT NULL, feed_url TEXT NOT NULL,
            categories_json TEXT NOT NULL, config_sha256 TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT, canonical_title TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS articles (
            article_id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT NOT NULL REFERENCES sources(source_id),
            article_url TEXT NOT NULL UNIQUE, title TEXT NOT NULL, summary TEXT NOT NULL,
            published_at TEXT, captured_at TEXT NOT NULL, capture_sha256 TEXT NOT NULL,
            event_id INTEGER NOT NULL REFERENCES events(event_id)
        );
        CREATE INDEX IF NOT EXISTS idx_articles_event ON articles(event_id, source_id, article_id);
    """)
    return connection


def assign_event(connection: sqlite3.Connection, title: str, now: str) -> int:
    for row in connection.execute("SELECT event_id, canonical_title FROM events ORDER BY event_id"):
        if same_event(title, row["canonical_title"]):
            return int(row["event_id"])
    cursor = connection.execute("INSERT INTO events(canonical_title, created_at) VALUES (?, ?)", (title, now))
    return int(cursor.lastrowid)


def capture(connection: sqlite3.Connection, source: dict, payload: bytes, now: str) -> dict:
    source_core = {key: source[key] for key in ("id", "name", "url", "categories")}
    connection.execute(
        "INSERT INTO sources VALUES (?, ?, ?, ?, ?) ON CONFLICT(source_id) DO UPDATE SET name=excluded.name, feed_url=excluded.feed_url, categories_json=excluded.categories_json, config_sha256=excluded.config_sha256",
        (source["id"], source["name"], source["url"], json.dumps(source["categories"], ensure_ascii=False), hashlib.sha256(canonical(source_core)).hexdigest()),
    )
    inserted, duplicates = 0, 0
    for article in parse_feed(payload, source):
        if connection.execute("SELECT 1 FROM articles WHERE article_url=?", (article.article_url,)).fetchone():
            duplicates += 1
            continue
        event_id = assign_event(connection, article.title, now)
        connection.execute(
            "INSERT INTO articles(source_id,article_url,title,summary,published_at,captured_at,capture_sha256,event_id) VALUES (?,?,?,?,?,?,?,?)",
            (article.source_id, article.article_url, article.title, article.summary, article.published_at, now, article.capture_sha256, event_id),
        )
        inserted += 1
    connection.commit()
    return {"source_id": source["id"], "inserted": inserted, "duplicates": duplicates}


def fetch(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Pastila-VNext-Scout/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def poll(connection: sqlite3.Connection, config: dict, timeout: float) -> list[dict]:
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    results = []
    for source in config["sources"]:
        if source.get("enabled", True):
            results.append(capture(connection, source, fetch(source["url"], timeout), now))
    return results


def event_rows(connection: sqlite3.Connection) -> list[dict]:
    return [dict(row) for row in connection.execute("""
        SELECT e.event_id,e.canonical_title,COUNT(a.article_id) article_count,
               COUNT(DISTINCT a.source_id) source_count
        FROM events e JOIN articles a USING(event_id)
        GROUP BY e.event_id ORDER BY e.event_id
    """)]


def critical_literals(text: str) -> dict:
    normalized = normalize_text(text)
    return {
        "numbers_dates_amounts": sorted(set(re.findall(r"\d+(?:[.,]\d+)*", text))),
        "procedural": [term for term in PROCEDURAL if term in normalized],
        "attribution_modality": [term for term in QUALIFICATION if term in normalized],
    }


def build_source_packet(connection: sqlite3.Connection, event_id: int) -> dict:
    rows = connection.execute("""
        SELECT a.*,s.name source_name,s.feed_url,s.categories_json
        FROM articles a JOIN sources s USING(source_id)
        WHERE event_id=? ORDER BY a.article_id
    """, (event_id,)).fetchall()
    if not rows:
        raise ValueError("unknown event")
    seen_sources: set[str] = set()
    spans = []
    for row in rows:
        if row["source_id"] in seen_sources:
            continue
        seen_sources.add(row["source_id"])
        text = clean_text(row["summary"] or row["title"])
        raw = text.encode()
        spans.append({
            "span_id": f"scout-event:{event_id}:s{len(spans)+1}", "position": len(spans),
            "source_id": row["source_id"], "source_name": row["source_name"],
            "source_feed_url": row["feed_url"], "article_url": row["article_url"],
            "title": row["title"], "published_at": row["published_at"], "captured_at": row["captured_at"],
            "capture_sha256": row["capture_sha256"], "byte_start": 0, "byte_end": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(), "critical_literals": critical_literals(text), "text": text,
        })
    packet = {
        "schema": SCHEMA, "schema_version": SCHEMA_VERSION, "event_id": f"scout-event:{event_id}",
        "completeness": "ALL_CAPTURED_UNIQUE_SOURCES", "source_count": len(spans), "spans": spans,
    }
    packet["packet_identity"] = identity(packet, "packet_identity")
    return packet


def fixture_acceptance(runtime_root: Path, fixture_path: Path, output_root: Path, invoke_editor: bool) -> dict:
    stage = output_root.with_name(output_root.name + ".stage")
    if output_root.exists() or stage.exists():
        raise ValueError("acceptance output root must be new")
    stage.mkdir(parents=True)
    try:
        fixture = load_json(fixture_path)
        database = stage / "ephemeral-scout.db"
        with open_database(database) as connection:
            for item in fixture["feeds"]:
                capture(connection, item["source"], item["xml"].encode(), fixture["captured_at"])
            events = event_rows(connection)
            selected = [item for item in events if item["source_count"] == fixture["selected_source_count"]]
            if len(selected) != 1:
                raise ValueError("fixture grouping did not produce one selectable event")
            packet = build_source_packet(connection, selected[0]["event_id"])
        packet_path = stage / "source-packet.json"
        atomic_json(packet_path, packet)
        result = {"status": "PASS_SCOUT_SOURCEPACKET", "events": events, "selected_event_id": packet["event_id"], "packet_identity": packet["packet_identity"], "source_count": packet["source_count"]}
        if invoke_editor:
            product_root = runtime_root.parents[1]
            editor_output = stage / "editor"
            command = [str(product_root / "platform/python-ml-v1/bin/python"), "-B", str(product_root / "runtime/editor-v0-v1/runtime.py"),
                       "--runtime-root", str(product_root / "runtime/editor-v0-v1"), "--closure-root", str(product_root / "components/r2-reference-v1"),
                       "--source-packet", str(packet_path), "--output-root", str(editor_output)]
            subprocess.run(command, check=True)
            receipt = load_json(editor_output / "terminal-receipt.json")
            result.update({"status": "PASS_SCOUT_TO_EDITOR_E2E", "editor_status": receipt["status"], "structural_valid": receipt["structural_valid"], "editor_receipt_identity": receipt["receipt_identity"]})
        result["receipt_identity"] = identity(result, "receipt_identity")
        atomic_json(stage / "acceptance-receipt.json", result)
        stage.replace(output_root)
        return result
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pastila-vnext-scout")
    parser.add_argument("--runtime-root", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    poll_parser = sub.add_parser("poll"); poll_parser.add_argument("--database", type=Path, required=True); poll_parser.add_argument("--timeout", type=float, default=20.0)
    events_parser = sub.add_parser("events"); events_parser.add_argument("--database", type=Path, required=True)
    handoff_parser = sub.add_parser("handoff"); handoff_parser.add_argument("--database", type=Path, required=True); handoff_parser.add_argument("--event-id", type=int, required=True); handoff_parser.add_argument("--output", type=Path, required=True)
    acceptance_parser = sub.add_parser("acceptance"); acceptance_parser.add_argument("--fixture", type=Path, required=True); acceptance_parser.add_argument("--output-root", type=Path, required=True); acceptance_parser.add_argument("--invoke-editor", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    runtime_root = args.runtime_root.resolve()
    lock, contract = verify_locked_runtime(runtime_root)
    product_root = runtime_root.parents[1]
    if lock["product_root"] != "/root/pastila-vnext/v1" or runtime_root != (product_root / lock["runtime_path"]).resolve():
        raise ValueError("SCOUT runtime layout or canonical product-root declaration drift")
    for relative in (lock["python_dependency"], lock["editor_runtime_path"], lock["r2_component_path"]):
        if not (product_root / relative).exists():
            raise ValueError(f"missing product dependency: {relative}")
    if args.command == "acceptance":
        print(json.dumps(fixture_acceptance(runtime_root, args.fixture, args.output_root.resolve(), args.invoke_editor), sort_keys=True)); return 0
    config = load_json(runtime_root / "sources.json")
    with open_database(args.database.resolve()) as connection:
        if args.command == "poll":
            print(json.dumps(poll(connection, config, args.timeout), ensure_ascii=False)); return 0
        if args.command == "events":
            print(json.dumps(event_rows(connection), ensure_ascii=False)); return 0
        packet = build_source_packet(connection, args.event_id)
        if args.output.exists():
            raise ValueError("handoff output already exists")
        atomic_json(args.output.resolve(), packet); print(packet["packet_identity"]); return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
