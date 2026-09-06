from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.crossref_integration_core_v2 import (
    NORMALIZED_SCHEMA_V1,
    CrossrefAdmissionProfileV2,
    CrossrefIntegrationStateV2,
    integrate_crossref_normalized_bytes_v2,
)

PROFILE = CrossrefAdmissionProfileV2(NORMALIZED_SCHEMA_V1, 10)


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def specimen(raw: str, doi: str = "10.1/example") -> bytes:
    return canonical(
        {
            "raw_capture_identity": raw,
            "records": [
                {
                    "DOI": doi,
                    "URL": None,
                    "created": None,
                    "published": None,
                    "publisher": None,
                    "title": None,
                    "type": None,
                }
            ],
            "schema": NORMALIZED_SCHEMA_V1,
        }
    )


def test_two_legitimate_specimens_use_unchanged_mechanism() -> None:
    first = specimen("1" * 64, "10.1/first")
    second = specimen("2" * 64, "10.1/second")
    state = CrossrefIntegrationStateV2()
    accepted_first = integrate_crossref_normalized_bytes_v2(PROFILE, state, first)
    assert accepted_first.disposition == "ACCEPTED"
    accepted_second = integrate_crossref_normalized_bytes_v2(
        PROFILE, accepted_first.state, second
    )
    assert accepted_second.disposition == "ACCEPTED"
    assert [record.doi_key for record in accepted_second.state.records] == [
        "10.1/first",
        "10.1/second",
    ]
    assert accepted_first.batch is not None
    assert accepted_first.batch.normalized_identity == hashlib.sha256(first).hexdigest()
    assert accepted_second.batch is not None
    assert accepted_second.batch.raw_capture_identity == "2" * 64


def test_replay_is_idempotent_and_conflict_is_zero_mutation() -> None:
    payload = specimen("1" * 64)
    accepted = integrate_crossref_normalized_bytes_v2(
        PROFILE, CrossrefIntegrationStateV2(), payload
    )
    replay = integrate_crossref_normalized_bytes_v2(PROFILE, accepted.state, payload)
    assert replay.disposition == "IDEMPOTENT_REPLAY"
    assert replay.state is accepted.state
    conflict = integrate_crossref_normalized_bytes_v2(
        PROFILE, accepted.state, specimen("2" * 64)
    )
    assert conflict.disposition == "QUARANTINED"
    assert conflict.state is accepted.state
    assert conflict.quarantine is not None
    assert conflict.quarantine.reason_codes == ("DOI_STATE_CONFLICT",)


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (lambda value: value.update(schema="other"), "NORMALIZED_SCHEMA_MISMATCH"),
        (
            lambda value: value.update(raw_capture_identity="bad"),
            "RAW_CAPTURE_IDENTITY_INVALID",
        ),
        (
            lambda value: value["records"].append(value["records"][0]),
            "DUPLICATE_DOI",
        ),
    ],
)
def test_invalid_specimens_are_deterministically_quarantined(mutation, reason) -> None:
    value = json.loads(specimen("1" * 64))
    mutation(value)
    result = integrate_crossref_normalized_bytes_v2(
        PROFILE, CrossrefIntegrationStateV2(), canonical(value)
    )
    assert result.disposition == "QUARANTINED"
    assert result.state == CrossrefIntegrationStateV2()
    assert result.quarantine is not None
    assert reason in result.quarantine.reason_codes


def test_profile_owns_record_limit_instead_of_reusable_mechanism() -> None:
    value = json.loads(specimen("1" * 64))
    value["records"].append({**value["records"][0], "DOI": "10.1/second"})
    payload = canonical(value)
    rejected = integrate_crossref_normalized_bytes_v2(
        CrossrefAdmissionProfileV2(NORMALIZED_SCHEMA_V1, 1),
        CrossrefIntegrationStateV2(),
        payload,
    )
    accepted = integrate_crossref_normalized_bytes_v2(
        CrossrefAdmissionProfileV2(NORMALIZED_SCHEMA_V1, 2),
        CrossrefIntegrationStateV2(),
        payload,
    )
    assert rejected.disposition == "QUARANTINED"
    assert accepted.disposition == "ACCEPTED"


def test_module_has_no_transport_or_phase_specific_authority() -> None:
    import pastila_scout.crossref_integration_core_v2 as subject

    source = Path(subject.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "http.client",
        "httpx",
        "socket",
        "ssl",
        "PHASE2",
        "PHASE3",
        "PHASE4",
        "PHASE5",
        ".pastila-runtime",
    ):
        assert forbidden not in source
