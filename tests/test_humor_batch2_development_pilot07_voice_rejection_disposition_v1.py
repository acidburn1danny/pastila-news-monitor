from __future__ import annotations

import hashlib
import json
from pathlib import Path


PATH = (
    Path(__file__).resolve().parents[1]
    / "docs/artifacts/humor-mechanics-batch2-development-pilot07-candidate01-voice-rejection-disposition-v1.json"
)


def seal(namespace: str, value: dict) -> str:
    payload = json.dumps(
        {"namespace": namespace, "value": value},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_pilot07_voice_rejection_is_nonpositive_and_non_authorizing() -> None:
    disposition = json.loads(PATH.read_text(encoding="utf-8"))
    core = dict(disposition)
    identity = core.pop("disposition_identity")
    assert identity == seal("B2_DEVELOPMENT_PILOT07_CANDIDATE01_VOICE_REJECTION_DISPOSITION_V1", core)
    assert disposition["disposition"] == "DEVELOPMENT_NONPOSITIVE_VOICE_REJECTION_EVIDENCE"
    assert disposition["stable_rejection_reasons"] == ["CANNED_CROSS_PILOT_CREATIVE_TRANSITION_REUSE"]
    assert disposition["candidate_git_blob_oid_sha1"] == "345829c569ae87d350a30158e026c52371e3c560"
    assert disposition["candidate_bytes_modified"] is False
    assert disposition["existing_identities_modified"] is False
    assert disposition["positive_coverage_eligible"] is False
    assert disposition["owner_review_eligible"] is False
    assert disposition["g04b_pool_certification_eligible"] is False
    assert disposition["visibility"] == "NON_MODEL_VISIBLE"
    assert not any(disposition["authority_matrix"].values())
