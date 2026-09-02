from copy import deepcopy
import itertools
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_authority_governance_v2_3 import (
    CUTOFF, canonical, identity, select_predecessor_release, validate_governance,
)


def release(registry, release_id, timestamp, *, official=True, complete=True):
    return {
        "registry": registry,
        "release_id": release_id,
        "published_at": timestamp,
        "official": official,
        "complete": complete,
        "immutable_archive_commitment": "a" * 64,
        "publication_evidence_identity": "b" * 64,
    }


def history(registry, rows):
    rows = tuple(rows)
    return {
        "registry": registry,
        "cutoff_utc": CUTOFF,
        "complete_through_utc": CUTOFF,
        "release_count": len(rows),
        "release_set_sha256": hashlib.sha256(canonical(sorted(rows, key=canonical))).hexdigest(),
        "external_verification": True,
    }


def select(rows, registry):
    return select_predecessor_release(rows, registry=registry, history_evidence=history(registry, rows))


def policy():
    value = {
        "schema": "OBJECTIVE_AUTHORITY_SELECTION_GOVERNANCE_V2_3",
        "supersedes": "53602bc3360e392fb05328cd6e21b9ccc252b1ab411f79f8ca96e3aea82eef5c",
        "temporal_selection": {
            "cutoff_utc": CUTOFF,
            "rule": "UNIQUE_LATEST_OFFICIAL_COMPLETE_RELEASE_STRICTLY_BEFORE_EXTERNAL_FREEZE",
            "registries": ["CROSSREF_ANNUAL_PUBLIC_DATA_FILE", "OPENALEX_PUBLIC_QUARTERLY_SNAPSHOT"],
            "release_history": "COMPLETE_OFFICIAL_HISTORY_THROUGH_CUTOFF_WITH_EXTERNAL_PROVENANCE",
            "publication_evidence": "OFFICIAL_RELEASE_RECORD_PLUS_COMPLETE_MANIFEST_DATE",
            "archive_evidence": "PUBLISHER_COMMITMENT_OR_COMPLETE_PER_OBJECT_SHA256_MERKLE_V1_WITH_IMMUTABLE_LOCATORS",
            "ties_ambiguity_missing_or_unverifiable": "TERMINAL_NO_FRAME_NO_SUBSTITUTION",
            "owner_snapshot_choice": False,
            "post_cutoff_release_effect": "NONE",
        },
        "outcome_invariance": {
            "properties": [
                "INPUT_ORDER_PERMUTATION_INVARIANT", "POST_CUTOFF_INSERTION_INVARIANT",
                "OLDER_RELEASE_INSERTION_INVARIANT", "UNIQUE_PREDECESSOR_REQUIRED",
                "NO_REDRAW_RESAMPLE_OR_FALLBACK", "NO_SEMANTIC_FIELDS_IN_TEMPORAL_SELECTION",
            ],
            "semantic_content_observed": False,
        },
        "anti_gaming": {
            "snapshot_enumeration": "COMPLETE_NOT_OWNER_CURATED",
            "negative_space": "ALL_OFFICIAL_RELEASES_THROUGH_CUTOFF_ACCOUNTED_FOR",
            "cutoff_mutation": "PROHIBITED",
            "registry_substitution": "PROHIBITED",
            "snapshot_fallback": "PROHIBITED",
            "post_hoc_filtering": "PROHIBITED",
            "redraw_or_resampling": False,
            "content_or_coverage_inspection_before_temporal_selection": False,
        },
        "unchanged_downstream": {
            "frame_scope_extraction": "V2_1_FROZEN_UNCHANGED",
            "rekor_drand_selection": "V2_2_FROZEN_UNCHANGED",
        },
        "registry_snapshots_acquired": 0, "frame_executed": False,
        "source_selected": False, "authority_basis_created": False,
        "pilot15_prepared": False, "blind_access": False,
    }
    value["governance_identity"] = identity(value, "governance_identity")
    return value


def test_governance_record_is_closed_and_self_identifying():
    validate_governance(policy())
    for path, replacement in [
        (("temporal_selection", "owner_snapshot_choice"), True),
        (("temporal_selection", "cutoff_utc"), "2026-09-03T00:00:00Z"),
        (("outcome_invariance", "semantic_content_observed"), True),
    ]:
        bad = deepcopy(policy())
        bad[path[0]][path[1]] = replacement
        bad["governance_identity"] = identity(bad, "governance_identity")
        with pytest.raises(ValueError):
            validate_governance(bad)


def test_frozen_governance_record_validates():
    path = Path("docs/artifacts/semantic-contract-v2-objective-authority-selection-governance-v2-3.json")
    validate_governance(json.loads(path.read_text(encoding="utf-8")))


def test_unique_predecessor_is_permutation_and_post_cutoff_invariant():
    registry = "CROSSREF_ANNUAL_PUBLIC_DATA_FILE"
    rows = [
        release(registry, "old", "2025-01-01T00:00:00Z"),
        release(registry, "winner", "2026-03-17T00:00:00Z"),
        release(registry, "future", "2027-01-01T00:00:00Z"),
    ]
    assert {select(order, registry)["release_id"] for order in itertools.permutations(rows)} == {"winner"}
    rows.append(release(registry, "later-future", "2028-01-01T00:00:00Z"))
    assert select(rows, registry)["release_id"] == "winner"


def test_incomplete_unofficial_and_cutoff_equal_are_ineligible():
    registry = "OPENALEX_PUBLIC_QUARTERLY_SNAPSHOT"
    rows = [
        release(registry, "winner", "2026-06-26T00:00:00Z"),
        release(registry, "incomplete", "2026-08-01T00:00:00Z", complete=False),
        release(registry, "unofficial", "2026-08-02T00:00:00Z", official=False),
        release(registry, "equal", CUTOFF),
    ]
    assert select(rows, registry)["release_id"] == "winner"


def test_tie_missing_evidence_wrong_registry_and_no_predecessor_fail_closed():
    registry = "CROSSREF_ANNUAL_PUBLIC_DATA_FILE"
    tied = [release(registry, key, "2026-03-17T00:00:00Z") for key in ("a", "b")]
    with pytest.raises(ValueError, match="ambiguous"):
        select(tied, registry)
    malformed = release(registry, "a", "2026-03-17T00:00:00Z")
    malformed["immutable_archive_commitment"] = "not-a-digest"
    with pytest.raises(ValueError, match="evidence"):
        select([malformed], registry)
    with pytest.raises(ValueError, match="registry"):
        select([release("OPENALEX_PUBLIC_QUARTERLY_SNAPSHOT", "a", "2026-01-01T00:00:00Z")], registry)
    with pytest.raises(ValueError, match="no eligible"):
        select([release(registry, "future", "2027-01-01T00:00:00Z")], registry)


def test_release_omission_count_root_cutoff_and_external_proof_fail_closed():
    registry = "CROSSREF_ANNUAL_PUBLIC_DATA_FILE"
    rows = [release(registry, "old", "2025-01-01T00:00:00Z"), release(registry, "winner", "2026-03-17T00:00:00Z")]
    evidence = history(registry, rows)
    for key, value in [
        ("release_count", 1), ("release_set_sha256", "0" * 64),
        ("cutoff_utc", "2026-09-01T00:00:00Z"),
        ("complete_through_utc", "2026-09-01T00:00:00Z"),
        ("external_verification", False),
    ]:
        bad = dict(evidence); bad[key] = value
        with pytest.raises(ValueError):
            select_predecessor_release(rows, registry=registry, history_evidence=bad)
    with pytest.raises(ValueError, match="commitment"):
        select_predecessor_release(rows[:-1], registry=registry, history_evidence=evidence)


def test_temporal_selector_has_no_semantic_or_owner_choice_parameter():
    names = set(select_predecessor_release.__annotations__)
    assert names == {"releases", "registry", "history_evidence", "cutoff", "return"}
