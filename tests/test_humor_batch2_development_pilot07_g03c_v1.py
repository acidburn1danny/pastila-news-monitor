from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs/artifacts"


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps(
        {"namespace": namespace, "value": value},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def load(name: str) -> dict:
    return json.loads((ARTIFACTS / name).read_text(encoding="utf-8"))


def test_pilot07_g03c_separates_candidate_pass_from_pool_pending() -> None:
    value = load("humor-mechanics-batch2-development-pilot07-candidate01-g03c-diagnostic-v1.json")
    identity = value.pop("g03c_diagnostic_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_G03C_DIAGNOSTIC_V1", value)
    assert value["candidate_level"]["verdict"] == "CANDIDATE_SHORTCUT_PASS"
    for key in ("lexical", "format", "position", "length", "topic_entity", "constructor_template", "metadata"):
        assert value["candidate_level"][key]["material"] is False
    assert value["pool_level"]["independent_source_family_count"] == 3
    assert value["pool_level"]["dominant_mechanism_recovered_family_count"] == 3
    assert value["pool_level"]["owner_frozen_positive_family_count"] == 2
    assert value["pool_level"]["certification_status"].startswith("NOT_EVALUATED")
    assert value["pool_level"]["weak_nonsemantic_classifier"]["training_or_tuning_performed"] is False
    assert value["contamination"]["verdict"] == "PASS_CLEAN_DEVELOPMENT_DIAGNOSTIC"
    assert value["blind_holdout_content_or_metadata_accessed"] is False
    assert value["candidate_bytes_modified"] is False
    assert not any(value["authority_matrix"].values())


def test_pilot07_g03c_receipt_is_sealed_and_non_authorizing() -> None:
    value = load("humor-mechanics-batch2-development-pilot07-candidate01-g03c-receipt-v1.json")
    identity = value.pop("g03c_receipt_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_G03C_RECEIPT_V1", value)
    assert value["candidate_level_verdict"] == "CANDIDATE_SHORTCUT_PASS"
    assert value["pool_level_verdict"] == "POOL_REBALANCING_PROGRESS_PILOT07_QUALITY_GATES_AND_SEPARATE_G04B_PENDING"
    assert value["next_gate_eligible"] == "G04A_ROMANIAN_NATURALNESS_SEPARATELY_AUTHORIZED_ONLY"
    assert value["candidate_bytes_modified"] is False
    assert value["blind_holdout_content_or_metadata_accessed"] is False
    assert not any(value["authority_matrix"].values())
