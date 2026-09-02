"""Temporal eligibility governance V2.3 for pre-existing registry releases.

This module is deliberately metadata-only.  It selects release descriptors, not
snapshot objects, records, frame entries, or semantic content.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Iterable, Mapping


REGISTRIES = ("CROSSREF_ANNUAL_PUBLIC_DATA_FILE", "OPENALEX_PUBLIC_QUARTERLY_SNAPSHOT")
CUTOFF = "2026-09-02T17:31:02Z"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def identity(value: Mapping[str, Any], field: str) -> str:
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(canonical(body)).hexdigest()


def _time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid release timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("release timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def select_predecessor_release(
    releases: Iterable[Mapping[str, Any]], *, registry: str,
    history_evidence: Mapping[str, Any], cutoff: str = CUTOFF,
) -> Mapping[str, Any]:
    """Select the unique latest complete official release strictly before cutoff."""
    if registry not in REGISTRIES:
        raise ValueError("registry outside frozen population")
    cutoff_time = _time(cutoff)
    releases = tuple(dict(item) for item in releases)
    expected_history = {
        "registry", "cutoff_utc", "complete_through_utc", "release_count",
        "release_set_sha256", "external_verification",
    }
    if set(history_evidence) != expected_history or history_evidence.get("registry") != registry:
        raise ValueError("release history evidence schema mismatch")
    if history_evidence.get("cutoff_utc") != cutoff:
        raise ValueError("release history cutoff mismatch")
    if _time(history_evidence.get("complete_through_utc")) < cutoff_time:
        raise ValueError("release history does not cover cutoff")
    if history_evidence.get("external_verification") is not True:
        raise ValueError("release history not externally verified")
    release_set_sha256 = hashlib.sha256(canonical(sorted(releases, key=canonical))).hexdigest()
    if history_evidence.get("release_count") != len(releases) or history_evidence.get("release_set_sha256") != release_set_sha256:
        raise ValueError("release history commitment mismatch")
    eligible: list[tuple[datetime, Mapping[str, Any]]] = []
    seen_ids: set[str] = set()
    for item in releases:
        required = {
            "registry", "release_id", "published_at", "official", "complete",
            "immutable_archive_commitment", "publication_evidence_identity",
        }
        if set(item) != required:
            raise ValueError("release descriptor schema mismatch")
        if item["registry"] != registry:
            raise ValueError("mixed registry release history")
        release_id = item["release_id"]
        if not isinstance(release_id, str) or not release_id or release_id in seen_ids:
            raise ValueError("invalid or duplicate release identity")
        seen_ids.add(release_id)
        published = _time(item["published_at"])
        if item["official"] is not True or item["complete"] is not True:
            continue
        if not all(
            isinstance(item[key], str) and len(item[key]) == 64
            and all(c in "0123456789abcdef" for c in item[key])
            for key in ("immutable_archive_commitment", "publication_evidence_identity")
        ):
            raise ValueError("release evidence identity invalid")
        if published < cutoff_time:
            eligible.append((published, item))
    if not eligible:
        raise ValueError("no eligible predecessor release")
    latest = max(published for published, _ in eligible)
    winners = [item for published, item in eligible if published == latest]
    if len(winners) != 1:
        raise ValueError("ambiguous predecessor release")
    return winners[0]


def validate_governance(policy: Mapping[str, Any]) -> None:
    if policy.get("schema") != "OBJECTIVE_AUTHORITY_SELECTION_GOVERNANCE_V2_3":
        raise ValueError("schema")
    if policy.get("supersedes") != "53602bc3360e392fb05328cd6e21b9ccc252b1ab411f79f8ca96e3aea82eef5c":
        raise ValueError("lineage")
    temporal = policy.get("temporal_selection", {})
    if temporal.get("cutoff_utc") != CUTOFF:
        raise ValueError("cutoff changed")
    if temporal.get("rule") != "UNIQUE_LATEST_OFFICIAL_COMPLETE_RELEASE_STRICTLY_BEFORE_EXTERNAL_FREEZE":
        raise ValueError("temporal rule")
    if temporal.get("registries") != list(REGISTRIES):
        raise ValueError("registry population")
    if temporal.get("release_history") != "COMPLETE_OFFICIAL_HISTORY_THROUGH_CUTOFF_WITH_EXTERNAL_PROVENANCE":
        raise ValueError("negative space")
    if temporal.get("publication_evidence") != "OFFICIAL_RELEASE_RECORD_PLUS_COMPLETE_MANIFEST_DATE":
        raise ValueError("publication evidence")
    if temporal.get("archive_evidence") != "PUBLISHER_COMMITMENT_OR_COMPLETE_PER_OBJECT_SHA256_MERKLE_V1_WITH_IMMUTABLE_LOCATORS":
        raise ValueError("archive evidence")
    if temporal.get("ties_ambiguity_missing_or_unverifiable") != "TERMINAL_NO_FRAME_NO_SUBSTITUTION":
        raise ValueError("fail closed")
    if temporal.get("owner_snapshot_choice") is not False or temporal.get("post_cutoff_release_effect") != "NONE":
        raise ValueError("owner or calendar influence")
    proof = policy.get("outcome_invariance", {})
    required = {
        "INPUT_ORDER_PERMUTATION_INVARIANT", "POST_CUTOFF_INSERTION_INVARIANT",
        "OLDER_RELEASE_INSERTION_INVARIANT", "UNIQUE_PREDECESSOR_REQUIRED",
        "NO_REDRAW_RESAMPLE_OR_FALLBACK", "NO_SEMANTIC_FIELDS_IN_TEMPORAL_SELECTION",
    }
    if set(proof.get("properties", [])) != required:
        raise ValueError("invariance proof")
    if proof.get("semantic_content_observed") is not False:
        raise ValueError("semantic observation")
    anti = policy.get("anti_gaming", {})
    if anti != {
        "snapshot_enumeration": "COMPLETE_NOT_OWNER_CURATED",
        "negative_space": "ALL_OFFICIAL_RELEASES_THROUGH_CUTOFF_ACCOUNTED_FOR",
        "cutoff_mutation": "PROHIBITED",
        "registry_substitution": "PROHIBITED",
        "snapshot_fallback": "PROHIBITED",
        "post_hoc_filtering": "PROHIBITED",
        "redraw_or_resampling": False,
        "content_or_coverage_inspection_before_temporal_selection": False,
    }:
        raise ValueError("anti-gaming policy")
    unchanged = policy.get("unchanged_downstream", {})
    if unchanged.get("frame_scope_extraction") != "V2_1_FROZEN_UNCHANGED":
        raise ValueError("frame semantics")
    if unchanged.get("rekor_drand_selection") != "V2_2_FROZEN_UNCHANGED":
        raise ValueError("entropy semantics")
    for key in ("registry_snapshots_acquired", "frame_executed", "source_selected", "authority_basis_created", "pilot15_prepared", "blind_access"):
        if policy.get(key) not in (0, False):
            raise ValueError(key)
    if policy.get("governance_identity") != identity(policy, "governance_identity"):
        raise ValueError("identity")
