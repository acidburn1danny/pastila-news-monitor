from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def load(name: str) -> dict:
    return json.loads((ART / name).read_text(encoding="utf-8"))


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps(
        {"namespace": namespace, "value": value},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_g03c_separates_candidate_pass_from_pool_pending() -> None:
    value = load("humor-mechanics-batch2-development-pilot02-candidate01-g03c-diagnostic-v1.json")
    identity = value.pop("g03c_diagnostic_identity")

    assert identity == seal("B2_DEVELOPMENT_PILOT02_CANDIDATE01_G03C_DIAGNOSTIC_V1", value)
    assert value["candidate_level"]["verdict"] == "CANDIDATE_SHORTCUT_PASS"
    assert all(not item["material"] for key, item in value["candidate_level"].items() if key in {
        "lexical", "format", "position", "length", "topic_entity", "constructor_template", "metadata"
    })
    assert value["pool_level"]["dominant_positive_family_count"] == 1
    assert value["pool_level"]["verdict"] == "POOL_PENDING_INSUFFICIENT_INDEPENDENT_POSITIVE_FAMILIES"
    assert value["pool_level"]["weak_nonsemantic_classifier"]["training_or_tuning_performed"] is False
    assert value["contamination"]["blind_family_or_metadata_access"] is False
    assert value["contamination"]["verdict"] == "PASS_CLEAN_DEVELOPMENT_DIAGNOSTIC"
    assert value["g03c_verdict"] == "CANDIDATE_SHORTCUT_PASS_AND_POOL_PENDING"
    assert value["candidate_bytes_modified"] is False
    assert not any(value["performed"].values())
    assert not any(value["authority_matrix"].values())


def test_g03c_receipt_is_sealed_and_grants_no_promotion() -> None:
    value = load("humor-mechanics-batch2-development-pilot02-candidate01-g03c-receipt-v1.json")
    identity = value.pop("g03c_receipt_identity")

    assert identity == seal("B2_DEVELOPMENT_PILOT02_CANDIDATE01_G03C_RECEIPT_V1", value)
    assert value["candidate_level_verdict"] == "CANDIDATE_SHORTCUT_PASS"
    assert value["pool_level_verdict"] == "POOL_PENDING_INSUFFICIENT_INDEPENDENT_POSITIVE_FAMILIES"
    assert value["blind_holdout_content_accessed"] is False
    assert value["candidate_bytes_modified"] is False
    assert value["authority_matrix"]["curriculum_promotion"] is False
    assert not any(value["authority_matrix"].values())
