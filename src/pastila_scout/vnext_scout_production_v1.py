"""Production-closure candidate for VNext SCOUT, isolated from active product."""
from __future__ import annotations

import gzip
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .vnext_foundation_v1 import (
    BoundaryError,
    atomic_json,
    canonical_json,
    object_identity,
    sha256_bytes,
)
from .vnext_state_sqlite_v1 import SQLiteStateStore
from .vnext_workflow_v1 import TransitionRequest

SCHEMA_VERSION = 1
GROUPING_VERSION = "scout-complete-link-title-v1"
MAX_COMPRESSED_BYTES = 2_000_000
MAX_DECOMPRESSED_BYTES = 4_000_000
MAX_ARTICLES_PER_SOURCE = 60
STOPWORDS = frozenset({"a", "ai", "al", "ale", "cu", "de", "din", "in", "la", "o", "pe", "si", "un", "unei", "unui"})
TRACKING_KEYS = frozenset({"fbclid", "gclid", "mc_cid", "mc_eid"})
_SHA256 = re.compile(r"[0-9a-f]{64}")


class ScoutError(BoundaryError):
    pass


class SourceConfigError(ScoutError):
    pass


class CaptureError(ScoutError):
    pass


class FeedParseError(ScoutError):
    pass


@dataclass(frozen=True)
class SourceDefinition:
    source_id: str
    name: str
    url: str
    categories: tuple[str, ...]
    maximum_articles: int = 50


@dataclass(frozen=True)
class FetchResponse:
    payload: bytes
    final_url: str
    content_type: str
    content_encoding: str | None = None


@dataclass(frozen=True)
class CapturedArticle:
    capture_identity: str
    source_identity: str
    source_name: str
    source_feed_url: str
    article_url: str
    title: str
    source_text: str
    published_at: str | None
    captured_at: str
    categories: tuple[str, ...]
    feed_identity: str


@dataclass(frozen=True)
class CaptureFailure:
    source_identity: str
    failure_class: str
    detail: str


@dataclass(frozen=True)
class EventGroup:
    event_identity: str
    grouping_identity: str
    captures: tuple[CapturedArticle, ...]


Transport = Callable[[SourceDefinition, float], FetchResponse]


def _validate_legacy_scout_packet(packet: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    """Validate the historical pre-selection-receipt packet for frozen evidence only."""
    if packet.get("schema") != "vnext-source-packet" or packet.get("schema_version") != SCHEMA_VERSION:
        raise ScoutError("SourcePacket schema mismatch")
    if packet.get("selection_authority") != "EXPLICIT_EVENT_ID" or packet.get("completeness") != "ONE_BEST_CAPTURE_PER_GROUPED_SOURCE":
        raise ScoutError("SourcePacket authority/completeness mismatch")
    claimed = packet.get("packet_identity")
    if not isinstance(claimed, str) or _SHA256.fullmatch(claimed) is None:
        raise ScoutError("SourcePacket identity invalid")
    if object_identity({key: value for key, value in packet.items() if key != "packet_identity"}) != claimed:
        raise ScoutError("SourcePacket identity mismatch")
    if not isinstance(packet.get("event_identity"), str) or not packet["event_identity"]:
        raise ScoutError("SourcePacket event identity missing")
    spans = packet.get("spans")
    if not isinstance(spans, list) or not spans or packet.get("source_count") != len(spans):
        raise ScoutError("SourcePacket spans/source_count mismatch")
    sources: set[str] = set()
    span_ids: set[str] = set()
    for position, span in enumerate(spans):
        if not isinstance(span, Mapping) or span.get("position") != position:
            raise ScoutError("SourcePacket span ordering mismatch")
        source = span.get("source_identity"); span_id = span.get("span_id"); text = span.get("text")
        if not isinstance(source, str) or not source or source in sources or not isinstance(span_id, str) or not span_id or span_id in span_ids:
            raise ScoutError("SourcePacket source/span identity invalid")
        if not isinstance(text, str) or not text.strip():
            raise ScoutError("SourcePacket text invalid")
        sources.add(source); span_ids.add(span_id)
        encoded = text.encode("utf-8")
        if span.get("byte_start") != 0 or span.get("byte_end") != len(encoded) or span.get("text_sha256") != sha256_bytes(encoded):
            raise ScoutError("SourcePacket text binding mismatch")
        if span.get("content_scope") != "FEED_ENTRY_SOURCE_TEXT":
            raise ScoutError("SourcePacket content scope mismatch")
        for key in ("capture_identity", "source_name", "source_feed_url", "article_url", "title", "captured_at"):
            if not isinstance(span.get(key), str) or not span[key]:
                raise ScoutError(f"SourcePacket {key} missing")
    return tuple(spans)


def validate_selection_receipt(
    receipt: Mapping[str, object],
    *,
    event_identity: str,
    workflow_identity: str | None = None,
) -> None:
    """Validate the minimal content-addressed authority for explicit user selection."""
    required = {
        "schema", "schema_version", "workflow_identity", "event_identity", "actor",
        "authorization_identity", "transition_receipt_identity", "receipt_identity",
    }
    if set(receipt) != required:
        raise ScoutError("selection receipt shape mismatch")
    if receipt.get("schema") != "vnext-source-selection-receipt" or receipt.get("schema_version") != 1:
        raise ScoutError("selection receipt schema mismatch")
    if receipt.get("event_identity") != event_identity:
        raise ScoutError("selection receipt event mismatch")
    if workflow_identity is not None and receipt.get("workflow_identity") != workflow_identity:
        raise ScoutError("selection receipt workflow mismatch")
    for key in ("workflow_identity", "actor"):
        if not isinstance(receipt.get(key), str) or not str(receipt[key]).strip():
            raise ScoutError(f"selection receipt {key} missing")
    for key in ("authorization_identity", "transition_receipt_identity", "receipt_identity"):
        if not isinstance(receipt.get(key), str) or _SHA256.fullmatch(str(receipt[key])) is None:
            raise ScoutError(f"selection receipt {key} invalid")
    if receipt["receipt_identity"] != object_identity(
        {key: value for key, value in receipt.items() if key != "receipt_identity"}
    ):
        raise ScoutError("selection receipt identity mismatch")


def validate_scout_packet(packet: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    """Validate the canonical active SourcePacket and its explicit selection authority."""
    if packet.get("schema") != "vnext-source-packet" or packet.get("schema_version") != SCHEMA_VERSION:
        raise ScoutError("SourcePacket schema mismatch")
    if packet.get("selection_authority") != "EXPLICIT_USER_EVENT_ID":
        raise ScoutError("SourcePacket authority mismatch")
    claimed = packet.get("packet_identity")
    if not isinstance(claimed, str) or _SHA256.fullmatch(claimed) is None:
        raise ScoutError("SourcePacket identity invalid")
    if object_identity({key: value for key, value in packet.items() if key != "packet_identity"}) != claimed:
        raise ScoutError("SourcePacket identity mismatch")
    event_identity = packet.get("event_identity")
    if not isinstance(event_identity, str) or not event_identity:
        raise ScoutError("SourcePacket event identity missing")
    receipt = packet.get("selection_receipt")
    if not isinstance(receipt, Mapping):
        raise ScoutError("SourcePacket selection receipt missing")
    validate_selection_receipt(receipt, event_identity=event_identity)
    legacy = dict(packet)
    legacy["selection_authority"] = "EXPLICIT_EVENT_ID"
    legacy.pop("selection_receipt", None)
    legacy["packet_identity"] = object_identity(
        {key: value for key, value in legacy.items() if key != "packet_identity"}
    )
    return _validate_legacy_scout_packet(legacy)


def _clean(value: str | None) -> str:
    if not value:
        return ""
    without_tags = re.sub(r"(?is)<(?:script|style)\b.*?</(?:script|style)>", " ", value)
    return " ".join(html.unescape(re.sub(r"(?s)<[^>]+>", " ", without_tags)).split())


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _child_text(node: ET.Element, *names: str) -> str:
    wanted = {name.casefold() for name in names}
    for child in node.iter():
        if child is not node and _local_name(child.tag) in wanted:
            value = _clean("".join(child.itertext()))
            if value:
                return value
    return ""


def _entry_link(node: ET.Element) -> str:
    for child in node.iter():
        if _local_name(child.tag) != "link":
            continue
        relation = child.attrib.get("rel", "alternate").casefold()
        candidate = child.attrib.get("href") or child.text or ""
        if relation in {"alternate", ""} and _clean(candidate):
            return _clean(candidate)
    return _child_text(node, "guid", "id")


def normalize_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme.casefold() not in {"http", "https"} or not parts.netloc:
        raise FeedParseError("article URL must be absolute HTTP(S)")
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if key.casefold() not in TRACKING_KEYS and not key.casefold().startswith("utm_")
    ]
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), parts.path or "/", urlencode(sorted(query)), ""))


def _parse_time(value: str) -> str | None:
    value = _clean(value)
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _decode_payload(response: FetchResponse) -> bytes:
    if len(response.payload) > MAX_COMPRESSED_BYTES:
        raise CaptureError("compressed feed exceeds byte limit")
    encoding = (response.content_encoding or "").casefold().strip()
    try:
        payload = gzip.decompress(response.payload) if encoding == "gzip" or response.payload.startswith(b"\x1f\x8b") else response.payload
    except (OSError, EOFError) as exc:
        raise CaptureError("invalid gzip feed") from exc
    if len(payload) > MAX_DECOMPRESSED_BYTES:
        raise CaptureError("decompressed feed exceeds byte limit")
    if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise FeedParseError("DTD/entity declarations are forbidden")
    return payload


def http_transport(source: SourceDefinition, timeout: float) -> FetchResponse:
    if urlsplit(source.url).scheme.casefold() != "https":
        raise CaptureError("source feed must use HTTPS")
    request = urllib.request.Request(
        source.url,
        headers={"User-Agent": "Pastila-VNext-Scout/1", "Accept-Encoding": "gzip"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read(MAX_COMPRESSED_BYTES + 1)
        final_url = response.url
        content_type = response.headers.get_content_type()
        encoding = response.headers.get("Content-Encoding")
    if urlsplit(final_url).scheme.casefold() != "https":
        raise CaptureError("source redirect left HTTPS")
    return FetchResponse(payload, final_url, content_type, encoding)


def load_sources(value: Mapping[str, object]) -> tuple[SourceDefinition, ...]:
    if value.get("schema") != "pastila-vnext-scout-sources" or value.get("schema_version") != 1:
        raise SourceConfigError("source-set schema mismatch")
    expected = object_identity({key: item for key, item in value.items() if key != "sources_identity"})
    if value.get("sources_identity") != expected:
        raise SourceConfigError("source-set identity mismatch")
    raw_sources = value.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise SourceConfigError("non-empty sources required")
    result: list[SourceDefinition] = []
    seen: set[str] = set()
    for raw in raw_sources:
        if not isinstance(raw, Mapping) or raw.get("adapter") != "rss" or raw.get("enabled") is not True:
            continue
        source_id = str(raw.get("id", ""))
        categories = raw.get("categories")
        maximum = int(raw.get("max_articles_per_poll", 50))
        if not source_id or source_id in seen or not isinstance(categories, list) or not 1 <= maximum <= MAX_ARTICLES_PER_SOURCE:
            raise SourceConfigError(f"invalid source: {source_id}")
        url = str(raw.get("url", ""))
        if urlsplit(url).scheme.casefold() != "https":
            raise SourceConfigError(f"non-HTTPS source: {source_id}")
        seen.add(source_id)
        result.append(SourceDefinition(source_id, str(raw.get("name", "")), url, tuple(map(str, categories)), maximum))
    if not result:
        raise SourceConfigError("no enabled RSS sources")
    return tuple(result)


def parse_feed(source: SourceDefinition, response: FetchResponse, captured_at: str) -> tuple[CapturedArticle, ...]:
    payload = _decode_payload(response)
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise FeedParseError(f"invalid XML: {exc}") from exc
    entries = [node for node in root.iter() if _local_name(node.tag) in {"item", "entry"}]
    feed_identity = sha256_bytes(payload)
    articles: list[CapturedArticle] = []
    seen_urls: set[str] = set()
    for entry in entries:
        title = _child_text(entry, "title")
        link = _entry_link(entry)
        if not title or not link:
            continue
        article_url = normalize_url(link)
        if article_url in seen_urls:
            continue
        seen_urls.add(article_url)
        source_text = _child_text(entry, "description", "summary", "content", "encoded") or title
        core = {
            "schema": "vnext-scout-capture",
            "schema_version": SCHEMA_VERSION,
            "source_identity": source.source_id,
            "source_name": source.name,
            "source_feed_url": source.url,
            "article_url": article_url,
            "title": title,
            "source_text": source_text,
            "published_at": _parse_time(_child_text(entry, "pubdate", "published", "updated", "date")),
            "captured_at": captured_at,
            "categories": list(source.categories),
            "feed_identity": feed_identity,
        }
        articles.append(CapturedArticle(
            capture_identity=object_identity(core),
            source_identity=source.source_id,
            source_name=source.name,
            source_feed_url=source.url,
            article_url=article_url,
            title=title,
            source_text=source_text,
            published_at=core["published_at"],
            captured_at=captured_at,
            categories=source.categories,
            feed_identity=feed_identity,
        ))
        if len(articles) >= source.maximum_articles:
            break
    if not articles:
        raise FeedParseError("feed has no valid title/link entries")
    return tuple(articles)


def capture_sources(
    sources: Sequence[SourceDefinition],
    *,
    transport: Transport,
    captured_at: str,
    timeout: float = 20.0,
    maximum_workers: int = 8,
) -> tuple[tuple[CapturedArticle, ...], tuple[CaptureFailure, ...]]:
    if maximum_workers < 1 or maximum_workers > 16:
        raise CaptureError("maximum_workers must be between 1 and 16")

    def capture_one(source: SourceDefinition) -> tuple[tuple[CapturedArticle, ...], CaptureFailure | None]:
        try:
            return parse_feed(source, transport(source, timeout), captured_at), None
        except Exception as exc:  # noqa: BLE001 - one broken source must not suppress healthy sources
            return (), CaptureFailure(source.source_id, type(exc).__name__, str(exc)[:240])

    articles: list[CapturedArticle] = []
    failures: list[CaptureFailure] = []
    with ThreadPoolExecutor(max_workers=min(maximum_workers, len(sources) or 1)) as executor:
        for captured, failure in executor.map(capture_one, sources):
            articles.extend(captured)
            if failure is not None:
                failures.append(failure)
    return (
        tuple(sorted(articles, key=lambda item: (item.source_identity, item.article_url))),
        tuple(sorted(failures, key=lambda item: item.source_identity)),
    )


def _tokens(value: str) -> frozenset[str]:
    normalized = " ".join(re.findall(r"[a-z0-9]+", value.casefold().translate(str.maketrans("ăâîșț", "aaist"))))
    return frozenset(token for token in normalized.split() if len(token) > 2 and token not in STOPWORDS)


def _named_tokens(value: str) -> frozenset[str]:
    words = re.findall(r"[A-ZĂÂÎȘȚ][\wĂÂÎȘȚăâîșț-]+", value)
    if words and value.lstrip().startswith(words[0]):
        words = words[1:]
    return frozenset("".join(_tokens(word)) for word in words if _tokens(word))


def same_event(left: CapturedArticle, right: CapturedArticle) -> bool:
    if left.source_identity == right.source_identity:
        return False
    left_numbers = frozenset(re.findall(r"\d+(?:[.,]\d+)*", left.title))
    right_numbers = frozenset(re.findall(r"\d+(?:[.,]\d+)*", right.title))
    if left_numbers and right_numbers and left_numbers != right_numbers:
        return False
    left_names, right_names = _named_tokens(left.title), _named_tokens(right.title)
    if left_names and right_names and not (left_names & right_names):
        return False
    a, b = _tokens(left.title), _tokens(right.title)
    if len(a & b) < 3:
        return False
    return len(a & b) / min(len(a), len(b)) >= 0.60


def group_articles(articles: Sequence[CapturedArticle]) -> tuple[EventGroup, ...]:
    groups: list[list[CapturedArticle]] = []
    for article in sorted(articles, key=lambda item: (item.published_at or "", item.capture_identity)):
        target = next((group for group in groups if all(same_event(article, member) for member in group)), None)
        if target is None:
            groups.append([article])
        else:
            target.append(article)
    result = []
    for group in groups:
        captures = tuple(sorted(group, key=lambda item: item.capture_identity))
        grouping = object_identity({"algorithm": GROUPING_VERSION, "captures": [item.capture_identity for item in captures]})
        result.append(EventGroup(f"event:{grouping}", grouping, captures))
    return tuple(sorted(result, key=lambda item: item.event_identity))


def _article_payload(article: CapturedArticle) -> dict[str, object]:
    value = asdict(article)
    value["schema"] = "vnext-scout-capture"
    value["schema_version"] = SCHEMA_VERSION
    value["categories"] = list(article.categories)
    return value


def _publish_immutable(root: Path, relative: Path, value: Mapping[str, object]) -> str:
    path = root / relative
    payload = canonical_json(value) + b"\n"
    if path.exists():
        if path.read_bytes() != payload:
            raise ScoutError(f"immutable artifact conflict: {relative.as_posix()}")
    else:
        atomic_json(path, dict(value), root=root, overwrite=False)
    return relative.as_posix()


def persist_capture_and_grouping(
    store: SQLiteStateStore,
    *,
    workflow_identity: str,
    sources_identity: str,
    articles: Sequence[CapturedArticle],
    failures: Sequence[CaptureFailure],
    observed_at: str,
) -> tuple[EventGroup, ...]:
    references = {}
    for article in articles:
        references[article.capture_identity] = _publish_immutable(
            store.root,
            Path("blobs/captures") / f"{article.capture_identity}.json",
            _article_payload(article),
        )
    batch: dict[str, object] = {
        "schema": "vnext-scout-capture-batch",
        "schema_version": SCHEMA_VERSION,
        "sources_identity": sources_identity,
        "article_references": dict(sorted(references.items())),
        "failures": [asdict(item) for item in failures],
    }
    batch_identity = object_identity(batch)
    batch["batch_identity"] = batch_identity
    _publish_immutable(store.root, Path("blobs/capture-batches") / f"{batch_identity}.json", batch)
    if not articles:
        request = _transition(
            workflow_identity,
            "capture",
            "DISCOVERED",
            "CAPTURE_FAILED",
            sources_identity,
            batch_identity,
            observed_at,
        )
        store.transition(request)
        return ()

    def persist_captures(connection: object) -> None:
        for article in articles:
            connection.execute("INSERT OR IGNORE INTO sources VALUES(?,?,?)", (article.source_identity, "RSS", sources_identity))
            connection.execute(
                "INSERT OR IGNORE INTO captures VALUES(?,?,?,?,?)",
                (article.capture_identity, article.source_identity, article.capture_identity, references[article.capture_identity], article.captured_at),
            )

    store.transition(
        _transition(
            workflow_identity,
            "capture",
            "DISCOVERED",
            "CAPTURED",
            sources_identity,
            batch_identity,
            observed_at,
        ),
        before_commit=persist_captures,
    )
    groups = group_articles(articles)

    grouping_output_identity = object_identity(
        [group.grouping_identity for group in groups]
    )

    def persist_groups(connection: object) -> None:
        for position, group in enumerate(groups):
            connection.execute(
                "INSERT OR IGNORE INTO events VALUES(?,?)",
                (group.event_identity, group.grouping_identity),
            )
            persisted = connection.execute(
                "SELECT grouping_identity FROM events WHERE event_identity=?",
                (group.event_identity,),
            ).fetchone()
            if persisted is None or persisted["grouping_identity"] != group.grouping_identity:
                raise ScoutError("global event identity conflicts with grouping")
            connection.execute(
                "INSERT INTO workflow_events VALUES(?,?,?,?)",
                (
                    workflow_identity,
                    group.event_identity,
                    group.grouping_identity,
                    position,
                ),
            )
            expected_captures = sorted(article.capture_identity for article in group.captures)
            for capture_identity in expected_captures:
                connection.execute(
                    "INSERT OR IGNORE INTO event_sources VALUES(?,?)",
                    (group.event_identity, capture_identity),
                )
            actual_captures = [
                row["capture_identity"]
                for row in connection.execute(
                    "SELECT capture_identity FROM event_sources "
                    "WHERE event_identity=? ORDER BY capture_identity",
                    (group.event_identity,),
                ).fetchall()
            ]
            if actual_captures != expected_captures:
                raise ScoutError("global event capture membership conflict")

    store.transition(
        _transition(
            workflow_identity,
            "group",
            "CAPTURED",
            "GROUPED",
            batch_identity,
            grouping_output_identity,
            observed_at,
        ),
        before_commit=persist_groups,
    )
    return groups


def validate_workflow_event_membership(
    store: SQLiteStateStore,
    *,
    workflow_identity: str,
    event_identity: str,
) -> tuple[object, ...]:
    """Prove that an event belongs to this workflow's exact grouping result."""
    with store.read() as connection:
        memberships = connection.execute(
            "SELECT we.event_identity,we.grouping_identity,we.position,e.grouping_identity "
            "AS persisted_grouping_identity FROM workflow_events we "
            "JOIN events e USING(event_identity) WHERE we.workflow_identity=? "
            "ORDER BY we.position",
            (workflow_identity,),
        ).fetchall()
        transitions = connection.execute(
            "SELECT receipt_identity,operation_identity,previous_state,resulting_state,"
            "actor,outcome,input_identity,output_identity,attempt_identity,"
            "idempotency_identity,receipt_json FROM state_transitions "
            "WHERE workflow_identity=? AND previous_state='CAPTURED' "
            "AND resulting_state='GROUPED'",
            (workflow_identity,),
        ).fetchall()
        captures = connection.execute(
            "SELECT c.capture_identity,c.payload_ref FROM workflow_events we "
            "JOIN event_sources es USING(event_identity) "
            "JOIN captures c USING(capture_identity) "
            "WHERE we.workflow_identity=? AND we.event_identity=? "
            "ORDER BY c.source_identity,c.capture_identity",
            (workflow_identity, event_identity),
        ).fetchall()
    if not memberships:
        raise ScoutError("workflow event membership missing")
    if [row["position"] for row in memberships] != list(range(len(memberships))):
        raise ScoutError("workflow event positions are not canonical")
    if any(
        row["grouping_identity"] != row["persisted_grouping_identity"]
        for row in memberships
    ):
        raise ScoutError("workflow event grouping binding mismatch")
    selected = [row for row in memberships if row["event_identity"] == event_identity]
    if len(selected) != 1:
        raise ScoutError("event is not owned uniquely by workflow grouping")
    if len(transitions) != 1:
        raise ScoutError("grouping transition ownership is absent or ambiguous")
    transition = transitions[0]
    expected_output = object_identity(
        [row["grouping_identity"] for row in memberships]
    )
    expected = {
        "operation_identity": "scout:group",
        "previous_state": "CAPTURED",
        "resulting_state": "GROUPED",
        "actor": "SCOUT",
        "outcome": "PASS",
        "output_identity": expected_output,
    }
    if any(transition[key] != value for key, value in expected.items()):
        raise ScoutError("grouping transition binding mismatch")
    if not isinstance(transition["input_identity"], str) or _SHA256.fullmatch(
        transition["input_identity"]
    ) is None:
        raise ScoutError("grouping transition input identity invalid")
    try:
        receipt = json.loads(transition["receipt_json"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ScoutError("grouping transition receipt invalid") from exc
    receipt_expected = {
        "workflow_identity": workflow_identity,
        "receipt_identity": transition["receipt_identity"],
        "attempt_identity": transition["attempt_identity"],
        "idempotency_identity": transition["idempotency_identity"],
        "input_identity": transition["input_identity"],
        **expected,
    }
    if (
        not isinstance(receipt, dict)
        or any(receipt.get(key) != value for key, value in receipt_expected.items())
        or receipt.get("receipt_identity") != object_identity({
            key: receipt.get(key) for key in (
                "schema", "schema_version", "workflow_identity",
                "operation_identity", "previous_state", "resulting_state",
                "actor", "outcome", "input_identity", "output_identity",
                "attempt_identity", "idempotency_identity",
            )
        })
    ):
        raise ScoutError("grouping transition receipt binding mismatch")
    if not captures:
        raise ScoutError("owned workflow event has no captures")
    return tuple(captures)


def build_source_packet(
    store: SQLiteStateStore,
    *,
    workflow_identity: str,
    event_identity: str,
    selection_actor: str,
    selection_authorization_identity: str,
    observed_at: str,
) -> dict[str, object]:
    rows = validate_workflow_event_membership(
        store,
        workflow_identity=workflow_identity,
        event_identity=event_identity,
    )
    if not isinstance(selection_actor, str) or not selection_actor.strip():
        raise ScoutError("explicit selection actor required")
    if (
        not isinstance(selection_authorization_identity, str)
        or _SHA256.fullmatch(selection_authorization_identity) is None
    ):
        raise ScoutError("explicit selection authorization identity required")
    _, transition_receipt, changed = store.transition(
        _transition(
            workflow_identity,
            "select",
            "GROUPED",
            "SELECTED",
            event_identity,
            event_identity,
            observed_at,
            actor=selection_actor,
        )
    )
    if not changed:
        raise ScoutError("selection transition must be newly persisted")
    selection_receipt: dict[str, object] = {
        "schema": "vnext-source-selection-receipt",
        "schema_version": 1,
        "workflow_identity": workflow_identity,
        "event_identity": event_identity,
        "actor": selection_actor,
        "authorization_identity": selection_authorization_identity,
        "transition_receipt_identity": transition_receipt["receipt_identity"],
    }
    selection_receipt["receipt_identity"] = object_identity(selection_receipt)
    validate_selection_receipt(
        selection_receipt,
        event_identity=event_identity,
        workflow_identity=workflow_identity,
    )
    _publish_immutable(
        store.root,
        Path("blobs/source-selections") / f"{selection_receipt['receipt_identity']}.json",
        selection_receipt,
    )
    if not rows:
        evidence = object_identity({"workflow": workflow_identity, "event": event_identity, "failure": "UNKNOWN_OR_EMPTY_EVENT"})
        store.transition(_transition(workflow_identity, "source-packet-invalid", "SELECTED", "SOURCE_PACKET_INVALID", event_identity, evidence, observed_at))
        raise ScoutError("unknown or empty event")
    selected: dict[str, dict[str, object]] = {}
    try:
        for row in rows:
            path = store.root / row["payload_ref"]
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("capture_identity") != row["capture_identity"]:
                raise ScoutError("capture reference identity mismatch")
            prior = selected.get(str(value["source_identity"]))
            if prior is None or len(str(value["source_text"])) > len(str(prior["source_text"])):
                selected[str(value["source_identity"])] = value
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ScoutError) as exc:
        evidence = object_identity({"workflow": workflow_identity, "event": event_identity, "failure": type(exc).__name__})
        store.transition(_transition(workflow_identity, "source-packet-invalid", "SELECTED", "SOURCE_PACKET_INVALID", event_identity, evidence, observed_at))
        raise ScoutError("selected event cannot produce a valid SourcePacket") from exc
    spans = []
    for index, value in enumerate(sorted(selected.values(), key=lambda item: str(item["source_identity"]))):
        text = str(value["source_text"])
        spans.append({
            "span_id": f"{event_identity}:source:{index + 1}",
            "position": index,
            "source_identity": value["source_identity"],
            "source_name": value["source_name"],
            "source_feed_url": value["source_feed_url"],
            "article_url": value["article_url"],
            "title": value["title"],
            "published_at": value["published_at"],
            "captured_at": value["captured_at"],
            "capture_identity": value["capture_identity"],
            "text": text,
            "text_sha256": sha256_bytes(text.encode("utf-8")),
            "byte_start": 0,
            "byte_end": len(text.encode("utf-8")),
            "content_scope": "FEED_ENTRY_SOURCE_TEXT",
        })
    packet: dict[str, object] = {
        "schema": "vnext-source-packet",
        "schema_version": SCHEMA_VERSION,
        "event_identity": event_identity,
        "selection_authority": "EXPLICIT_USER_EVENT_ID",
        "selection_receipt": selection_receipt,
        "completeness": "ONE_BEST_CAPTURE_PER_GROUPED_SOURCE",
        "source_count": len(spans),
        "spans": spans,
    }
    packet["packet_identity"] = object_identity(packet)
    relative = Path("blobs/source-packets") / f"{packet['packet_identity']}.json"
    reference = _publish_immutable(store.root, relative, packet)

    def persist_packet(connection: object) -> None:
        connection.execute(
            "INSERT INTO source_packets VALUES(?,?,?,?)",
            (packet["packet_identity"], event_identity, packet["packet_identity"], reference),
        )

    store.transition(_transition(workflow_identity, "source-packet", "SELECTED", "SOURCE_PACKET_READY", event_identity, str(packet["packet_identity"]), observed_at), before_commit=persist_packet)
    return packet


def _transition(
    workflow: str,
    operation: str,
    previous: str,
    resulting: str,
    input_identity: str,
    output_identity: str,
    observed_at: str,
    *,
    actor: str = "SCOUT",
) -> TransitionRequest:
    semantic = {"workflow": workflow, "operation": operation, "previous": previous, "resulting": resulting, "input": input_identity, "output": output_identity}
    identity = object_identity(semantic)
    return TransitionRequest(
        workflow_id=workflow,
        operation_id=f"scout:{operation}",
        previous_state=previous,
        resulting_state=resulting,
        actor=actor,
        outcome="PASS" if not resulting.endswith("FAILED") else "FAIL",
        input_identity=input_identity,
        output_identity=output_identity,
        attempt_identity=f"attempt:{identity}",
        idempotency_identity=f"idempotency:{identity}",
        observed_at=observed_at,
        provenance={"component": "VNext SCOUT Production Closure v1"},
    )


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")
