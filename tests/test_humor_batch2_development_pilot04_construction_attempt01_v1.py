"""Verify the frozen one-shot Pilot 04 construction evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_pilot04_attempt_is_exactly_once_and_byte_bound() -> None:
    evidence = json.loads((ART / "humor-mechanics-batch2-development-pilot04-construction-attempt01-v1.json").read_text(encoding="utf-8"))
    candidate = (ART / "humor-mechanics-batch2-development-pilot04-candidate01-v1.txt").read_bytes()
    core = dict(evidence); identity = core.pop("evidence_identity")
    assert seal("B2_DEVELOPMENT_PILOT04_CONSTRUCTION_ATTEMPT01_V1", core) == identity
    assert evidence["attempt"] == {"authorized": 1, "consumed": 1, "remaining": 0, "constructor_invocations": 1}
    assert evidence["terminal_classification"] == "CANDIDATE_PRODUCED_DEVELOPMENT_ONLY"
    assert hashlib.sha256(candidate).hexdigest() == evidence["candidate_surface_sha256"]
    expected_candidate = seal("B2_DEVELOPMENT_PILOT04_CANDIDATE_V1", {
        "constructor_packet_identity": evidence["constructor_facing_packet_identity"],
        "raw_surface_sha256": evidence["candidate_surface_sha256"], "attempt_ordinal": 1, "partition": "DEVELOPMENT",
    })
    assert expected_candidate == evidence["candidate_identity"]
    expected_family = seal("B2_CREATIVE_PREMISE_FAMILY_V1", {
        "sealed_assignment_identity": "689f57472f4c0147cb6613da5ea737639d74404fbf5e2d0d54ad24700b55f28c",
        "source_commitment": evidence["construction_provenance"]["closed_authority_envelope_source_commitment"],
        "candidate_identity": expected_candidate,
    })
    assert expected_family == evidence["creative_premise_family_id"]
    assert evidence["capability"]["consumed"] is True and evidence["capability"]["reads"] == 1
    assert evidence["post_construction_g02b_verdict"] == "PASS"
    assert all(value is False for value in evidence["authority_matrix"].values())
    assert evidence["retry_authority"] is evidence["repair_authority"] is evidence["selection_authority"] is False
    exposure = evidence["constructor_exposure_reconciliation"]
    assert exposure["authorized_packet_only"] is True and exposure["exact_source_bytes_only"] is True
    assert all(value is False for key, value in exposure.items() if key not in {"authorized_packet_only", "exact_source_bytes_only"})
