"""Static validation for the source-blind V2.2 selection governance."""
from __future__ import annotations
import hashlib, json
from typing import Any, Mapping

def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

def identity(value: Mapping[str, Any], field: str) -> str:
    body = dict(value); body.pop(field, None)
    return hashlib.sha256(canonical(body)).hexdigest()

def validate(policy: Mapping[str, Any]) -> None:
    if policy.get("schema") != "OBJECTIVE_AUTHORITY_SELECTION_GOVERNANCE_V2_2": raise ValueError("schema")
    if policy.get("supersedes") != "dbea255e0e23439b5a20a9b0541429877502aaf896976cd2a56537dbb68480c0": raise ValueError("lineage")
    cutoff = policy["external_freeze"]
    if cutoff.get("protocol") != "RFC3161_DIGICERT_SHA256" or cutoff.get("verified") is not True: raise ValueError("external freeze")
    if cutoff.get("timestamp_utc") != "2026-09-02T17:31:02Z": raise ValueError("cutoff")
    releases = policy["release_selection"]
    if releases.get("rule") != "UNIQUE_EARLIEST_OFFICIAL_COMPLETE_RELEASE_STRICTLY_AFTER_EXTERNAL_FREEZE": raise ValueError("release rule")
    if releases.get("unavailable") != "WAIT_NO_FRAME_NO_SUBSTITUTION": raise ValueError("wait")
    commitment = policy["archive_commitment"]
    required = {"VERSIONED_IMMUTABLE_LOCATOR", "BYTE_LENGTH", "SHA256"}
    if set(commitment.get("leaf_fields", [])) != required: raise ValueError("leaf commitment")
    if commitment.get("etag_accepted") or commitment.get("missing_digest") != "TERMINAL_INELIGIBLE": raise ValueError("digest weakness")
    if commitment.get("all_manifest_objects_required") is not True: raise ValueError("negative space")
    lifecycle = policy["lifecycle"]
    if lifecycle.get("rekor_frame_commitment") != "ONLY_AFTER_COMPLETE_FRAME_EXISTS": raise ValueError("Rekor phase")
    if lifecycle.get("drand_round") != "DERIVED_ONLY_FROM_VERIFIED_REKOR_INTEGRATED_TIME_PLUS_86400": raise ValueError("entropy phase")
    for key in ("registry_snapshots_acquired", "frame_executed", "source_selected", "authority_basis_created", "pilot15_prepared", "blind_access"):
        if policy.get(key) not in (0, False): raise ValueError(key)
    if identity(policy, "governance_identity") != policy.get("governance_identity"): raise ValueError("identity")
