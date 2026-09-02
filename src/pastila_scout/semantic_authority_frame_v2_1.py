"""Pure, fail-closed primitives for zero-frame V2.1 qualification (no I/O)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Callable, Iterable, Mapping

SHA256 = re.compile(r"^[0-9a-f]{64}$")
REGISTRIES = frozenset({"CROSSREF", "OPENALEX"})
FIELDS = frozenset({"registry", "stable_id", "doi", "resource_locator", "publication_type", "language", "access_right", "license", "content_digest"})


def canonical_bytes(value: Any) -> bytes:
    """Canonical JSON over the frozen integer/string/boolean/null metadata subset."""
    def validate(item: Any) -> None:
        if isinstance(item, float):
            raise ValueError("floats prohibited")
        if isinstance(item, dict):
            if not all(isinstance(key, str) for key in item):
                raise ValueError("non-string key")
            for child in item.values():
                validate(child)
        elif isinstance(item, (list, tuple)):
            for child in item:
                validate(child)
        elif item is not None and not isinstance(item, (str, int, bool)):
            raise ValueError("unsupported canonical type")
    validate(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_doi(value: str | None) -> str | None:
    if value is None:
        return None
    result = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if result.startswith(prefix):
            result = result[len(prefix):]
            break
    return result if result.isascii() and result.startswith("10.") and "/" in result and not any(c.isspace() for c in result) else None


def select_snapshot_manifest(
    manifests: Iterable[Mapping[str, Any]], *, governance_frozen_at: datetime
) -> Mapping[str, Any]:
    """Select the earliest official release after freeze; ties fail closed."""
    eligible: list[tuple[datetime, Mapping[str, Any]]] = []
    for manifest in manifests:
        try:
            published = datetime.fromisoformat(str(manifest["published_at"]).replace("Z", "+00:00"))
        except (KeyError, ValueError) as exc:
            raise ValueError("snapshot publication time invalid") from exc
        if published.tzinfo is None or governance_frozen_at.tzinfo is None:
            raise ValueError("timezone-aware timestamps required")
        if published.astimezone(timezone.utc) > governance_frozen_at.astimezone(timezone.utc):
            eligible.append((published.astimezone(timezone.utc), manifest))
    if not eligible:
        raise ValueError("no eligible post-freeze snapshot")
    eligible.sort(key=lambda item: (item[0], canonical_bytes(item[1])))
    earliest = eligible[0][0]
    if sum(published == earliest for published, _ in eligible) != 1:
        raise ValueError("ambiguous earliest snapshot release")
    return eligible[0][1]


@dataclass(frozen=True)
class VerifiedSnapshot:
    registry: str
    identity: str
    records: tuple[Mapping[str, Any], ...]


def verify_snapshot_manifest(
    manifest: Mapping[str, Any], records: Iterable[Mapping[str, Any]], *,
    governance_frozen_at: datetime,
    verify_external_manifest: Callable[[Mapping[str, Any]], bool],
) -> VerifiedSnapshot:
    """Verify an externally committed, adapter-projected snapshot manifest."""
    required = {"registry", "release_id", "published_at", "record_count", "projected_records_sha256", "archive_sha256", "external_commitment"}
    if set(manifest) != required or manifest.get("registry") not in REGISTRIES:
        raise ValueError("snapshot manifest schema or registry mismatch")
    try:
        published = datetime.fromisoformat(str(manifest["published_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("snapshot publication time invalid") from exc
    if published.tzinfo is None or governance_frozen_at.tzinfo is None:
        raise ValueError("timezone-aware timestamps required")
    if published.astimezone(timezone.utc) <= governance_frozen_at.astimezone(timezone.utc):
        raise ValueError("snapshot predates governance freeze")
    rows = tuple(dict(row) for row in records)
    digest = sha(canonical_bytes(rows))
    if manifest["record_count"] != len(rows) or manifest["projected_records_sha256"] != digest:
        raise ValueError("snapshot projection binding mismatch")
    if not SHA256.fullmatch(str(manifest["archive_sha256"])) or not verify_external_manifest(manifest):
        raise ValueError("external snapshot commitment invalid")
    identity = sha(canonical_bytes({"manifest": manifest, "projection_sha256": digest}))
    return VerifiedSnapshot(str(manifest["registry"]), identity, rows)


def build_frame(snapshots: Iterable[VerifiedSnapshot]) -> dict[str, Any]:
    """Build a deterministic Crossref/OpenAlex frame and complete decision log."""
    snapshots = tuple(snapshots)
    if len(snapshots) != 2 or {s.registry for s in snapshots} != REGISTRIES:
        raise ValueError("exactly one verified snapshot per registry required")
    if len({s.identity for s in snapshots}) != 2:
        raise ValueError("snapshot identities must be distinct")
    records = [dict(row) for snapshot in snapshots for row in snapshot.records]
    for snapshot in snapshots:
        if any(row.get("registry") != snapshot.registry for row in snapshot.records):
            raise ValueError("record registry not bound to snapshot")
    records.sort(key=canonical_bytes)
    digests = [sha(canonical_bytes(row)) for row in records]
    if len(digests) != len(set(digests)):
        raise ValueError("duplicate snapshot record")
    decisions: list[dict[str, Any]] = []
    eligible: list[tuple[str, dict[str, Any]]] = []
    for ordinal, row in enumerate(records):
        if set(row) - FIELDS:
            raise ValueError("unknown or semantic metadata projected")
        doi, stable = normalize_doi(row.get("doi")), row.get("stable_id")
        key = "doi:" + doi if doi else (f'{row["registry"].lower()}:{stable}' if isinstance(stable, str) and stable else None)
        reason = None
        if key is None:
            reason = "STABLE_KEY_MISSING"
        elif not isinstance(row.get("resource_locator"), str) or not row["resource_locator"]:
            reason = "IMMUTABLE_RESOURCE_LOCATOR_MISSING"
        elif not isinstance(row.get("content_digest"), str) or not SHA256.fullmatch(row["content_digest"]):
            reason = "IMMUTABLE_CONTENT_DIGEST_MISSING"
        elif row.get("access_right") is not True:
            reason = "EXPLICIT_ACQUISITION_RIGHT_MISSING"
        decisions.append({"ordinal": ordinal, "registry": row["registry"], "stable_id": stable, "key": key, "record_digest": digests[ordinal], "eligible": reason is None, "reason": reason})
        if reason is None:
            eligible.append((key, row))
    groups: dict[str, list[dict[str, Any]]] = {}
    for key, row in eligible:
        groups.setdefault(key, []).append(row)
    entries = []
    for key in sorted(groups, key=lambda item: item.encode()):
        rows = groups[key]
        content_digests = {row["content_digest"] for row in rows}
        if len(content_digests) != 1:
            for decision in decisions:
                if decision["key"] == key:
                    decision.update(eligible=False, reason="CROSS_REGISTRY_CONTENT_DIGEST_CONFLICT")
            continue
        entries.append({"key": key, "content_digest": next(iter(content_digests)), "locators": sorted({row["resource_locator"] for row in rows}), "provenance": sorted({f'{row["registry"]}:{row["stable_id"]}' for row in rows})})
    root = merkle_root([hashlib.sha256(b"\0" + canonical_bytes(entry)).digest() for entry in entries]).hex()
    body = {"snapshot_identities": sorted(s.identity for s in snapshots), "entries": entries, "decisions": decisions, "eligible_count": len(entries), "visited_count": len(decisions), "merkle_root": root}
    return {**body, "frame_identity": sha(canonical_bytes(body))}


def merkle_root(nodes: list[bytes]) -> bytes:
    if not nodes:
        return hashlib.sha256(b"").digest()
    while len(nodes) > 1:
        nodes = [hashlib.sha256(b"\1" + nodes[i] + (nodes[i + 1] if i + 1 < len(nodes) else nodes[i])).digest() for i in range(0, len(nodes), 2)]
    return nodes[0]


def verify_rekor_commitment(entry: Mapping[str, Any], *, expected_payload: Mapping[str, Any], verify_tree_signature: Callable[[bytes, int, bytes], bool]) -> int:
    """Verify exact payload, RFC6962 inclusion proof, and signed tree root."""
    if entry.get("body") != expected_payload:
        raise ValueError("Rekor payload mismatch")
    node = hashlib.sha256(b"\0" + canonical_bytes(expected_payload)).digest()
    index, size, proof = entry.get("log_index"), entry.get("tree_size"), entry.get("inclusion_path")
    if not isinstance(index, int) or index < 0 or not isinstance(size, int) or size <= index or not isinstance(proof, list):
        raise ValueError("Rekor proof coordinates invalid")
    fn, sn = index, size - 1
    for encoded in proof:
        try:
            sibling = bytes.fromhex(encoded)
        except (TypeError, ValueError) as exc:
            raise ValueError("Rekor proof hash invalid") from exc
        if len(sibling) != 32:
            raise ValueError("Rekor proof hash invalid")
        if fn & 1 or fn == sn:
            node = hashlib.sha256(b"\1" + sibling + node).digest()
            while fn and not (fn & 1):
                fn >>= 1; sn >>= 1
        else:
            node = hashlib.sha256(b"\1" + node + sibling).digest()
        fn >>= 1; sn >>= 1
    if sn:
        raise ValueError("Rekor proof length invalid")
    try:
        root, signature = bytes.fromhex(entry.get("signed_root", "")), bytes.fromhex(entry.get("tree_signature", ""))
    except (TypeError, ValueError) as exc:
        raise ValueError("Rekor encoding invalid") from exc
    if len(root) != 32 or root != node or not verify_tree_signature(root, size, signature):
        raise ValueError("Rekor inclusion or signature invalid")
    integrated = entry.get("integrated_time")
    if not isinstance(integrated, int) or integrated <= 0:
        raise ValueError("Rekor integrated time invalid")
    return integrated


def select_canonical_rekor_entry(
    entries: Iterable[Mapping[str, Any]], *, expected_payload: Mapping[str, Any],
    verify_tree_signature: Callable[[bytes, int, bytes], bool],
) -> Mapping[str, Any]:
    """Return the unique earliest valid log entry, making later attempts ineligible."""
    valid: list[Mapping[str, Any]] = []
    for entry in entries:
        try:
            verify_rekor_commitment(entry, expected_payload=expected_payload, verify_tree_signature=verify_tree_signature)
        except (ValueError, TypeError):
            continue
        valid.append(entry)
    if not valid:
        raise ValueError("no valid Rekor commitment")
    valid.sort(key=lambda item: item["log_index"])
    if len(valid) > 1 and valid[0]["log_index"] == valid[1]["log_index"]:
        raise ValueError("ambiguous canonical Rekor entry")
    return valid[0]


def verify_drand(receipt: Mapping[str, Any], *, expected_round: int, expected_chain_hash: str, verify_signature: Callable[[int, bytes, bytes], bool]) -> bytes:
    """Verify pinned chain/round, signature through an adapter, and randomness."""
    if receipt.get("round") != expected_round or receipt.get("chain_hash") != expected_chain_hash:
        raise ValueError("drand chain or round mismatch")
    try:
        signature = bytes.fromhex(receipt.get("signature", "")); randomness = bytes.fromhex(receipt.get("randomness", "")); previous = bytes.fromhex(receipt.get("previous_signature", ""))
    except (TypeError, ValueError) as exc:
        raise ValueError("drand encoding invalid") from exc
    if not SHA256.fullmatch(expected_chain_hash) or len(randomness) != 32 or hashlib.sha256(signature).digest() != randomness:
        raise ValueError("drand randomness invalid")
    if not verify_signature(expected_round, previous, signature):
        raise ValueError("drand signature invalid")
    return randomness


def derive_drand_round(*, integrated_time: int, genesis_time: int, period_seconds: int) -> int:
    """Derive the first round at/after the committed time plus 24 hours."""
    if integrated_time <= 0 or genesis_time < 0 or period_seconds <= 0:
        raise ValueError("drand timing parameters invalid")
    target = integrated_time + 86_400
    if target <= genesis_time:
        return 1
    return (target - genesis_time + period_seconds - 1) // period_seconds + 1


def verify_drand_quorum(
    receipts: Iterable[Mapping[str, Any]], *, expected_round: int,
    expected_chain_hash: str,
    verify_signature: Callable[[int, bytes, bytes], bool],
) -> bytes:
    """Require two independently labelled endpoints to return identical beacons."""
    receipts = tuple(receipts)
    if len(receipts) < 2 or len({item.get("endpoint") for item in receipts}) < 2:
        raise ValueError("drand endpoint quorum missing")
    values = [verify_drand(item, expected_round=expected_round, expected_chain_hash=expected_chain_hash, verify_signature=verify_signature) for item in receipts]
    if len(set(values)) != 1:
        raise ValueError("drand endpoint quorum mismatch")
    return values[0]


def select_index(*, governance_identity: str, frame_root: str, chain_hash: str, round_number: int, randomness: bytes, population_size: int) -> tuple[int, tuple[str, ...]]:
    """Domain-separated SHA-256 rejection sampling without modulo bias."""
    if population_size <= 0 or round_number < 0 or len(randomness) != 32 or not all(SHA256.fullmatch(x) for x in (governance_identity, frame_root, chain_hash)):
        raise ValueError("selection inputs invalid")
    domain = b"PASTILA_SEMANTIC_AUTHORITY_SELECTION_V2_1\0"
    seed = hashlib.sha256(domain + bytes.fromhex(governance_identity) + bytes.fromhex(frame_root) + bytes.fromhex(chain_hash) + round_number.to_bytes(8, "big") + randomness).digest()
    limit, trace = (1 << 256) // population_size * population_size, []
    for counter in range(1 << 64):
        digest = hashlib.sha256(domain + seed + counter.to_bytes(8, "big")).digest(); trace.append(digest.hex())
        number = int.from_bytes(digest, "big")
        if number < limit:
            return number % population_size, tuple(trace)
    raise ValueError("selection counter exhausted")


def select_frame_entry(frame: Mapping[str, Any], **selection: Any) -> tuple[Mapping[str, Any], tuple[str, ...]]:
    """Bind selection directly to the frame root, count, and canonical ordering."""
    entries = frame.get("entries")
    if not isinstance(entries, list) or frame.get("eligible_count") != len(entries):
        raise ValueError("frame population closure invalid")
    if frame.get("merkle_root") != merkle_root([hashlib.sha256(b"\0" + canonical_bytes(entry)).digest() for entry in entries]).hex():
        raise ValueError("frame root mismatch")
    if entries != sorted(entries, key=lambda entry: entry["key"].encode()):
        raise ValueError("frame order mismatch")
    index, trace = select_index(frame_root=frame["merkle_root"], population_size=len(entries), **selection)
    return entries[index], trace


@dataclass(frozen=True)
class Segment:
    char_start: int; char_end: int; byte_start: int; byte_end: int; text: str


def segment_utf8_losslessly(data: bytes) -> tuple[Segment, ...]:
    """Segment actual UTF-8 bytes into lossless line spans with exact coordinates."""
    text = data.decode("utf-8")
    parts = text.splitlines(keepends=True) or [""]
    output, char_start, byte_start = [], 0, 0
    for part in parts:
        raw = part.encode()
        output.append(Segment(char_start, char_start + len(part), byte_start, byte_start + len(raw), part))
        char_start += len(part); byte_start += len(raw)
    if char_start != len(text) or byte_start != len(data) or b"".join(item.text.encode() for item in output) != data:
        raise ValueError("lossless segment closure failed")
    return tuple(output)
