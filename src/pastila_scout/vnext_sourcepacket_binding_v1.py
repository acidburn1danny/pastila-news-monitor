"""Fail-closed binding from SCOUT production output to the frozen SourcePacket contract."""
from __future__ import annotations

import re
from collections.abc import Mapping

from .vnext_foundation_v1 import BoundaryError, object_identity, sha256_bytes

SOURCE_SCHEMA = "vnext-source-packet"
TARGET_SCHEMA = "editor-vnext-source-packet"
SCHEMA_VERSION = 1
SOURCE_SELECTION = "EXPLICIT_EVENT_ID"
TARGET_SELECTION = "EXPLICIT_USER_EVENT_ID"
SOURCE_COMPLETENESS = "ONE_BEST_CAPTURE_PER_GROUPED_SOURCE"
TARGET_COMPLETENESS = "ALL_CAPTURED_UNIQUE_SOURCES"
_SHA256 = re.compile(r"[0-9a-f]{64}")


class SourcePacketBindingError(BoundaryError):
    """The SCOUT packet cannot be proven compatible with the frozen contract."""


def _required_text(value: Mapping[str, object], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise SourcePacketBindingError(f"missing or empty {key}")
    return item


def _sha256(value: Mapping[str, object], key: str) -> str:
    item = _required_text(value, key)
    if _SHA256.fullmatch(item) is None:
        raise SourcePacketBindingError(f"invalid {key}")
    return item


def validate_scout_packet(packet: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    """Validate only properties provable from the self-contained SCOUT packet."""
    if packet.get("schema") != SOURCE_SCHEMA or packet.get("schema_version") != SCHEMA_VERSION:
        raise SourcePacketBindingError("SCOUT SourcePacket schema mismatch")
    if packet.get("selection_authority") != SOURCE_SELECTION:
        raise SourcePacketBindingError("SCOUT selection authority mismatch")
    if packet.get("completeness") != SOURCE_COMPLETENESS:
        raise SourcePacketBindingError("SCOUT completeness mismatch")
    claimed_identity = _sha256(packet, "packet_identity")
    semantic = {key: value for key, value in packet.items() if key != "packet_identity"}
    if object_identity(semantic) != claimed_identity:
        raise SourcePacketBindingError("SCOUT packet identity mismatch")
    _required_text(packet, "event_identity")
    spans = packet.get("spans")
    if not isinstance(spans, list) or not spans:
        raise SourcePacketBindingError("SCOUT packet requires spans")
    if packet.get("source_count") != len(spans):
        raise SourcePacketBindingError("SCOUT source_count mismatch")
    seen_sources: set[str] = set()
    seen_spans: set[str] = set()
    for position, raw_span in enumerate(spans):
        if not isinstance(raw_span, Mapping):
            raise SourcePacketBindingError("SCOUT span must be an object")
        if raw_span.get("position") != position:
            raise SourcePacketBindingError("SCOUT span positions are not canonical")
        span_id = _required_text(raw_span, "span_id")
        source_identity = _required_text(raw_span, "source_identity")
        if span_id in seen_spans or source_identity in seen_sources:
            raise SourcePacketBindingError("duplicate span or source identity")
        seen_spans.add(span_id)
        seen_sources.add(source_identity)
        text = _required_text(raw_span, "text")
        encoded = text.encode("utf-8")
        if raw_span.get("byte_start") != 0 or raw_span.get("byte_end") != len(encoded):
            raise SourcePacketBindingError("SCOUT span byte boundary mismatch")
        if _sha256(raw_span, "text_sha256") != sha256_bytes(encoded):
            raise SourcePacketBindingError("SCOUT span text identity mismatch")
        _sha256(raw_span, "capture_identity")
        for key in ("source_name", "source_feed_url", "article_url", "title", "captured_at", "content_scope"):
            _required_text(raw_span, key)
        published = raw_span.get("published_at")
        if published is not None and not isinstance(published, str):
            raise SourcePacketBindingError("invalid published_at")
        if raw_span.get("content_scope") != "FEED_ENTRY_SOURCE_TEXT":
            raise SourcePacketBindingError("unsupported content scope")
    return tuple(spans)


def bind_source_packet(packet: Mapping[str, object]) -> dict[str, object]:
    """Produce the frozen SourcePacket representation without changing source bytes."""
    spans = validate_scout_packet(packet)
    bound_spans: list[dict[str, object]] = []
    for span in spans:
        bound_spans.append({
            "span_id": span["span_id"],
            "position": span["position"],
            "source_id": span["source_identity"],
            "source_name": span["source_name"],
            "source_feed_url": span["source_feed_url"],
            "article_url": span["article_url"],
            "title": span["title"],
            "published_at": span.get("published_at"),
            "captured_at": span["captured_at"],
            "capture_sha256": span["capture_identity"],
            "byte_start": span["byte_start"],
            "byte_end": span["byte_end"],
            "sha256": span["text_sha256"],
            "text": span["text"],
            "content_scope": span["content_scope"],
        })
    bound: dict[str, object] = {
        "schema": TARGET_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "event_id": packet["event_identity"],
        "selection_authority": TARGET_SELECTION,
        "completeness": TARGET_COMPLETENESS,
        "source_count": len(bound_spans),
        "spans": bound_spans,
    }
    bound["packet_identity"] = object_identity(bound)
    validate_bound_source_packet(bound)
    return bound


def validate_bound_source_packet(packet: Mapping[str, object]) -> None:
    """Verify the emitted packet independently of SCOUT persistence or repository paths."""
    if packet.get("schema") != TARGET_SCHEMA or packet.get("schema_version") != SCHEMA_VERSION:
        raise SourcePacketBindingError("bound SourcePacket schema mismatch")
    if packet.get("selection_authority") != TARGET_SELECTION:
        raise SourcePacketBindingError("bound selection authority mismatch")
    if packet.get("completeness") != TARGET_COMPLETENESS:
        raise SourcePacketBindingError("bound completeness mismatch")
    identity = _sha256(packet, "packet_identity")
    if object_identity({key: value for key, value in packet.items() if key != "packet_identity"}) != identity:
        raise SourcePacketBindingError("bound packet identity mismatch")
    _required_text(packet, "event_id")
    spans = packet.get("spans")
    if not isinstance(spans, list) or not spans or packet.get("source_count") != len(spans):
        raise SourcePacketBindingError("bound spans/source_count mismatch")
    sources: set[str] = set()
    for position, raw_span in enumerate(spans):
        if not isinstance(raw_span, Mapping) or raw_span.get("position") != position:
            raise SourcePacketBindingError("bound span ordering mismatch")
        source_id = _required_text(raw_span, "source_id")
        if source_id in sources:
            raise SourcePacketBindingError("bound duplicate source")
        sources.add(source_id)
        text = _required_text(raw_span, "text")
        encoded = text.encode("utf-8")
        if raw_span.get("byte_start") != 0 or raw_span.get("byte_end") != len(encoded):
            raise SourcePacketBindingError("bound byte boundary mismatch")
        if _sha256(raw_span, "sha256") != sha256_bytes(encoded):
            raise SourcePacketBindingError("bound text identity mismatch")
        _sha256(raw_span, "capture_sha256")
        for key in ("span_id", "source_name", "source_feed_url", "article_url", "title", "captured_at", "content_scope"):
            _required_text(raw_span, key)
        if raw_span.get("content_scope") != "FEED_ENTRY_SOURCE_TEXT":
            raise SourcePacketBindingError("bound content scope mismatch")
