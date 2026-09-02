"""Hardened metadata-only predecessor-release governance V2.3.1."""
from __future__ import annotations

from datetime import date
import hashlib
import json
import re
from typing import Any, Callable, Iterable, Mapping

REGISTRIES = ("CROSSREF_ANNUAL_PUBLIC_DATA_FILE", "OPENALEX_PUBLIC_QUARTERLY_SNAPSHOT")
GOVERNANCE_IDENTITY = "41f202af7e835bfc9bbb048d803ee19e7861719ae4d45f0298035f586d640c52"
CUTOFF_UTC = "2026-09-02T17:31:02Z"
CUTOFF_DATE_EXCLUSIVE = date(2026, 9, 2)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HISTORY_SCHEMA = "EXTERNALLY_VERIFIED_COMPLETE_RELEASE_HISTORY_V2_3_1"
COVERAGE = "ALL_OFFICIAL_COMPLETE_RELEASES_PUBLISHED_BEFORE_2026_09_02"


def canonical(value: Any) -> bytes:
    if isinstance(value, float):
        raise ValueError("floats prohibited")
    if isinstance(value, dict):
        if not all(isinstance(k, str) for k in value):
            raise ValueError("non-string key")
        for child in value.values():
            canonical(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            canonical(child)
    elif value is not None and not isinstance(value, (str, int, bool)):
        raise ValueError("unsupported canonical type")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def identity(value: Mapping[str, Any], field: str) -> str:
    body = dict(value); body.pop(field, None)
    return hashlib.sha256(canonical(body)).hexdigest()


def release_set_sha256(releases: Iterable[Mapping[str, Any]]) -> str:
    rows = [dict(row) for row in releases]
    return hashlib.sha256(canonical(sorted(rows, key=canonical))).hexdigest()


def _release_date(value: Any) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("publication date must be canonical official-date precision")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("publication date invalid") from exc


def select_verified_predecessor_release(
    releases: Iterable[Mapping[str, Any]], *, registry: str,
    history_evidence: Mapping[str, Any], verifier_identity: str,
    verify_external_attestation: Callable[[bytes, str, str], bool],
) -> Mapping[str, Any]:
    """Verify complete metadata history, then select without caller-set timing."""
    if registry not in REGISTRIES:
        raise ValueError("registry outside frozen population")
    rows = tuple(dict(row) for row in releases)
    fields = {
        "registry", "release_id", "publication_date", "official_release_record_identity",
        "completeness_evidence_identity", "archive_commitment_identity",
        "immutable_locator_set_identity", "archive_available",
    }
    seen_ids: set[str] = set(); seen_records: set[str] = set(); seen_archives: set[str] = set()
    dated: list[tuple[date, Mapping[str, Any]]] = []
    for row in rows:
        if set(row) != fields or row.get("registry") != registry:
            raise ValueError("release descriptor schema or registry mismatch")
        if not isinstance(row["release_id"], str) or not row["release_id"] or row["release_id"] in seen_ids:
            raise ValueError("duplicate or invalid release id")
        hashes = tuple(row[key] for key in (
            "official_release_record_identity", "completeness_evidence_identity",
            "archive_commitment_identity", "immutable_locator_set_identity",
        ))
        if not all(isinstance(value, str) and HEX64.fullmatch(value) for value in hashes):
            raise ValueError("release authority identity invalid")
        if hashes[0] in seen_records or hashes[2] in seen_archives:
            raise ValueError("release alias or duplicate archive")
        if not isinstance(row["archive_available"], bool):
            raise ValueError("archive availability not authoritative boolean")
        seen_ids.add(row["release_id"]); seen_records.add(hashes[0]); seen_archives.add(hashes[2])
        dated.append((_release_date(row["publication_date"]), row))
    evidence_fields = {
        "schema", "governance_identity", "registry", "cutoff_utc", "cutoff_date_exclusive",
        "coverage_claim", "authority_sources", "release_count", "release_set_sha256",
        "capture_identity", "attestation_identity", "verifier_identity",
    }
    if set(history_evidence) != evidence_fields:
        raise ValueError("history evidence schema mismatch")
    if history_evidence.get("schema") != HISTORY_SCHEMA or history_evidence.get("governance_identity") != GOVERNANCE_IDENTITY:
        raise ValueError("history governance/version skew")
    if history_evidence.get("registry") != registry or history_evidence.get("cutoff_utc") != CUTOFF_UTC or history_evidence.get("cutoff_date_exclusive") != CUTOFF_DATE_EXCLUSIVE.isoformat():
        raise ValueError("history registry or cutoff skew")
    if history_evidence.get("coverage_claim") != COVERAGE:
        raise ValueError("history negative-space claim missing")
    if history_evidence.get("authority_sources") != ["PUBLISHER_RELEASE_INDEX", "PUBLISHER_ARCHIVE_LISTING"]:
        raise ValueError("independent publisher metadata paths missing")
    root = release_set_sha256(rows)
    if history_evidence.get("release_count") != len(rows) or history_evidence.get("release_set_sha256") != root:
        raise ValueError("release history count/root mismatch")
    for key in ("capture_identity", "attestation_identity", "verifier_identity"):
        if not isinstance(history_evidence.get(key), str) or not HEX64.fullmatch(history_evidence[key]):
            raise ValueError("history evidence identity invalid")
    if history_evidence["verifier_identity"] != verifier_identity:
        raise ValueError("history verifier identity skew")
    attested = dict(history_evidence); attestation = attested.pop("attestation_identity")
    if not verify_external_attestation(canonical(attested), attestation, verifier_identity):
        raise ValueError("external history attestation invalid")
    eligible = [(published, row) for published, row in dated if published < CUTOFF_DATE_EXCLUSIVE]
    if not eligible:
        raise ValueError("no predecessor release")
    latest = max(published for published, _ in eligible)
    winners = [row for published, row in eligible if published == latest]
    if len(winners) != 1:
        raise ValueError("ambiguous predecessor publication date")
    winner = winners[0]
    if winner["archive_available"] is not True:
        raise ValueError("canonical predecessor archive unavailable; fallback prohibited")
    return winner


def validate_governance(policy: Mapping[str, Any]) -> None:
    if policy.get("schema") != "OBJECTIVE_AUTHORITY_SELECTION_GOVERNANCE_V2_3_1": raise ValueError("schema")
    if policy.get("supersedes") != "f9f190dee6d2010f2c6113a9dd54a7817de10c8f0487a4b63e8bb2da30288bbe": raise ValueError("lineage")
    if policy.get("cutoff") != {"rfc3161_utc": CUTOFF_UTC, "publication_date_exclusive": "2026-09-02", "caller_override": False}: raise ValueError("cutoff")
    if policy.get("history_proof") != {
        "schema": HISTORY_SCHEMA, "coverage": COVERAGE,
        "authority_sources": ["PUBLISHER_RELEASE_INDEX", "PUBLISHER_ARCHIVE_LISTING"],
        "external_attestation_required": True, "count_and_release_set_root_bound": True,
        "self_asserted_verification_accepted": False,
    }: raise ValueError("history proof")
    if policy.get("selection") != {
        "rule": "UNIQUE_LATEST_OFFICIAL_COMPLETE_RELEASE_DATE_STRICTLY_BEFORE_CUTOFF_DATE",
        "timestamp_precision": "OFFICIAL_PUBLICATION_DATE_NO_INVENTED_TIME",
        "unavailable_winner": "TERMINAL_NO_FRAME_NO_FALLBACK",
        "tie_alias_duplicate_or_version_skew": "TERMINAL_NO_FRAME",
        "post_cutoff_effect": "NONE", "redraw_resample_or_owner_choice": False,
    }: raise ValueError("selection")
    for key in ("registry_histories_acquired", "snapshot_content_acquired", "frame_executed", "source_selected", "authority_basis_created", "pilot15_prepared", "blind_access"):
        if policy.get(key) not in (0, False): raise ValueError(key)
    if policy.get("governance_identity") != identity(policy, "governance_identity"): raise ValueError("identity")
