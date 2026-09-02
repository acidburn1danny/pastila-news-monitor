"""Validate the owner-executable, outcome-invariant authority selection policy.

Independence is established by replayable inputs and future public randomness,
not by claims that a human or agent lacks knowledge of V2.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def canonical_identity(value: Mapping[str, Any], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return hashlib.sha256(
        json.dumps(
            body, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def validate_objective_policy(value: Mapping[str, Any]) -> None:
    required = {
        "governance_identity",
        "registry_union",
        "frame_derivation",
        "entropy_anchor",
        "selection",
        "scope",
        "extraction",
        "evidence",
        "owner_execution",
    }
    if required - value.keys():
        raise ValueError("incomplete objective selection governance")
    if value["governance_identity"] != canonical_identity(value, "governance_identity"):
        raise ValueError("objective governance identity mismatch")

    registries = value["registry_union"]
    if registries.get("operation") != "MANDATORY_UNION_NO_REGISTRY_CHOICE":
        raise ValueError("owner-selectable registry")
    if registries.get("roots") != ["CROSSREF_ANNUAL_PUBLIC_DATA_FILE", "OPENALEX_PUBLIC_SNAPSHOT"]:
        raise ValueError("registry-root skew")
    if registries.get("snapshot_rule") != "FIRST_PUBLISHED_SNAPSHOT_AFTER_GOVERNANCE_FREEZE":
        raise ValueError("snapshot cherry-picking")

    frame = value["frame_derivation"]
    if frame.get("metadata_fields") != [
        "STABLE_RECORD_ID",
        "RESOURCE_LOCATOR",
        "PUBLICATION_TYPE",
        "LANGUAGE_IF_RECORDED",
        "ACCESS_AND_LICENSE_METADATA",
        "REGISTRY_PROVENANCE",
    ]:
        raise ValueError("frame metadata field skew")
    if frame.get("semantic_query_or_keyword_filter") is not False:
        raise ValueError("semantic frame shaping")
    if frame.get("v2_relation_or_coverage_filter") is not False:
        raise ValueError("V2 frame shaping")
    if frame.get("complete_negative_space") is not True:
        raise ValueError("frame negative space missing")
    if frame.get("owner_discretion") != "NONE_AFTER_GOVERNANCE_FREEZE":
        raise ValueError("owner frame discretion")

    entropy = value["entropy_anchor"]
    if entropy.get("network") != "DRAND_QUICKNET_MAINNET":
        raise ValueError("entropy network skew")
    if entropy.get("chain_hash") != "52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971":
        raise ValueError("entropy chain skew")
    if entropy.get("round_rule") != "FIRST_ROUND_AT_OR_AFTER_FRAME_COMMIT_TIME_PLUS_86400_SECONDS":
        raise ValueError("owner-selectable entropy round")
    if entropy.get("cryptographic_verification_required") is not True:
        raise ValueError("unverified entropy")

    selection = value["selection"]
    if selection.get("algorithm") != "SHA256_DOMAIN_SEPARATED_REJECTION_SAMPLING_V1":
        raise ValueError("selection algorithm skew")
    if selection.get("draws") != 1 or selection.get("redraw") is not False:
        raise ValueError("resampling path")
    if selection.get("post_draw_eligibility_failure") != "TERMINAL_NO_SOURCE_NO_REDRAW":
        raise ValueError("result-dependent replacement")

    scope = value["scope"]
    if scope.get("rule") != "ALL_ACQUIRED_BYTES":
        raise ValueError("selective scope")
    if scope.get("semantic_exclusions") is not False:
        raise ValueError("semantic scope shaping")

    extraction = value["extraction"]
    if extraction.get("phase_one") != "LOSSLESS_ALL_BYTE_RANGES_BY_FROZEN_SEGMENTER":
        raise ValueError("lossy extraction")
    if extraction.get("phase_two") != "VISIT_EVERY_SEGMENT_IN_BYTE_ORDER_WITH_NO_DROPPING":
        raise ValueError("selective semantic mapping")
    if extraction.get("coverage_visible") is not False:
        raise ValueError("coverage-visible extraction")
    if extraction.get("stopping_rule") != "END_OF_SOURCE":
        raise ValueError("early extraction stop")
    if extraction.get("all_decisions_logged") is not True:
        raise ValueError("extraction negative space missing")

    evidence = value["evidence"]
    if evidence.get("replay_from_public_inputs") is not True:
        raise ValueError("non-replayable independence evidence")
    if evidence.get("complete_intermediate_hash_chain") is not True:
        raise ValueError("incomplete execution evidence")
    if evidence.get("identity_labels_as_independence_proof") is not False:
        raise ValueError("fictional trust separation")

    owner = value["owner_execution"]
    if owner.get("v2_informed") is not True:
        raise ValueError("false blindness claim")
    if owner.get("may_choose_frame_source_scope_segment_or_redraw") is not False:
        raise ValueError("V2-informed owner retains outcome choice")
    if owner.get("may_abort_after_observing_result") is not False:
        raise ValueError("selective abort path")


def derive_entropy_round(*, frame_commit_unix_seconds: int, genesis_time: int, period: int) -> int:
    """Return the first beacon round at/after the fixed 24-hour delay."""
    if frame_commit_unix_seconds < genesis_time or period <= 0:
        raise ValueError("invalid entropy round inputs")
    target = frame_commit_unix_seconds + 86400
    return ((target - genesis_time + period - 1) // period) + 1
