from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "docs/artifacts/humor-mechanics-batch2-development-pilot02-candidate01-naturalness-rejection-disposition-v1.json"


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps(
        {"namespace": namespace, "value": value},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def test_disposition_is_sealed_nonpositive_and_preserves_rejection() -> None:
    value = json.loads(PATH.read_text(encoding="utf-8"))
    identity = value.pop("disposition_identity")

    assert identity == seal("B2_DEVELOPMENT_PILOT02_CANDIDATE01_NATURALNESS_REJECTION_DISPOSITION_V1", value)
    assert value["disposition"] == "DEVELOPMENT_NONPOSITIVE_ROMANIAN_NATURALNESS_REJECTION_EVIDENCE"
    assert value["partition"] == "DEVELOPMENT"
    assert value["visibility"] == "NON_MODEL_VISIBLE"
    assert value["stable_rejection_reasons"] == [
        "UNNATURAL_GOVERNANCE_STYLE_CREATIVE_MARKER",
        "PROCEDURAL_ABSTRACT_REGISTER",
    ]
    assert value["positive_coverage_eligible"] is False
    assert value["curriculum_candidate_eligible"] is False
    assert value["candidate_bytes_modified"] is False
    assert value["frozen_findings_reinterpreted"] is False
    assert not any(value["performed"].values())
    assert not any(value["authority_matrix"].values())
