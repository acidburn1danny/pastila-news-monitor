"""Adversarial offline qualification for Crossref capture integration."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import pastila_scout.crossref_capture_integration_v1 as integration_module
from pastila_scout.crossref_capture_integration_v1 import (
    CrossrefIntegrationInputRejected,
    CrossrefIntegrationResultV1,
    CrossrefIntegrationStateV1,
    integrate_crossref_normalized_bytes_v1,
)

ROOT = Path(__file__).resolve().parents[1]
NORMALIZED = (
    ROOT / ".pastila-runtime/milestone10-crossref-pilot-v2/normalized-records.json"
)
RAW_IDENTITY = "3acbdb9f2e54940f5953b497ace279a5884d0ce607f4e77e868de9a667783281"
NORMALIZED_IDENTITY = "bc2dd86d76c89f9e39f4a99a72db87ef57a5835ea92533a02f942ecc1111f4e0"


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()


def _integrate(
    state: CrossrefIntegrationStateV1 | None = None,
    payload: bytes | None = None,
):
    supplied = NORMALIZED.read_bytes() if payload is None else payload
    return integrate_crossref_normalized_bytes_v1(
        CrossrefIntegrationStateV1() if state is None else state,
        supplied,
    )


def test_exact_committed_capture_integrates_atomically_offline(monkeypatch) -> None:
    def network_forbidden(*args, **kwargs):
        raise AssertionError("Phase 3 attempted network access")

    monkeypatch.setattr("socket.socket", network_forbidden)
    result = _integrate()

    assert result.disposition == "ACCEPTED"
    assert result.quarantine is None
    assert result.batch is not None
    assert result.batch.normalized_identity == NORMALIZED_IDENTITY
    assert result.batch.raw_capture_identity == RAW_IDENTITY
    assert len(result.batch.records) == len(result.state.records) == 10
    assert result.state.applied_batch_identities == (result.batch.identity,)
    keys = tuple(record.doi_key for record in result.state.records)
    assert keys == tuple(sorted(keys))
    assert len(keys) == len(set(keys)) == 10
    assert {record.source_ordinal for record in result.state.records} == set(range(10))
    assert all(
        record.DOI.casefold() == record.doi_key for record in result.state.records
    )
    assert all(
        record.raw_capture_identity == RAW_IDENTITY for record in result.state.records
    )
    assert all(
        record.normalized_identity == NORMALIZED_IDENTITY
        for record in result.state.records
    )


def test_exact_replay_is_idempotent_and_byte_stable() -> None:
    first = _integrate()
    replay = _integrate(first.state)

    assert replay.disposition == "IDEMPOTENT_REPLAY"
    assert replay.state is first.state
    assert replay.state.canonical_bytes == first.state.canonical_bytes
    assert replay.state.identity == first.state.identity
    assert replay.batch == first.batch


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda value: value.update(schema="wrong"), "NORMALIZED_SCHEMA_MISMATCH"),
        (
            lambda value: value.update(raw_capture_identity="0" * 64),
            "RAW_CAPTURE_IDENTITY_MISMATCH",
        ),
        (
            lambda value: value["records"][0].update(extra="forbidden"),
            "RECORD_SHAPE_INVALID",
        ),
        (
            lambda value: value["records"][-1].update(title="wrong"),
            "RECORD_FIELD_TYPE_INVALID",
        ),
        (
            lambda value: value["records"][0].update(DOI=""),
            "DOI_INVALID",
        ),
        (
            lambda value: value["records"].append(value["records"][0]),
            "RECORD_SET_INVALID",
        ),
        (
            lambda value: value["records"][1].update(
                DOI=value["records"][0]["DOI"].upper()
            ),
            "DUPLICATE_DOI",
        ),
    ],
)
def test_invalid_whole_capture_is_quarantined_without_partial_state(
    mutate, reason: str
) -> None:
    value = json.loads(NORMALIZED.read_bytes())
    mutate(value)
    result = _integrate(payload=_canonical(value))

    assert result.disposition == "QUARANTINED"
    assert result.batch is None
    assert result.state == CrossrefIntegrationStateV1()
    assert result.quarantine is not None
    assert reason in result.quarantine.reason_codes
    assert result.quarantine.state_before_identity == result.state.identity
    assert result.quarantine.state_after_identity == result.state.identity


@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        b'{"schema":"duplicate","schema":"duplicate"}\n',
        b'{"raw_capture_identity":"x","records":[],"schema":"x"}',
        b'{"raw_capture_identity":"x","records":[],"schema":NaN}\n',
    ],
)
def test_malformed_or_noncanonical_bytes_are_quarantined(payload: bytes) -> None:
    result = _integrate(payload=payload)

    assert result.disposition == "QUARANTINED"
    assert result.quarantine is not None
    assert any(
        reason in result.quarantine.reason_codes
        for reason in ("NORMALIZED_BYTES_MALFORMED", "NORMALIZED_BYTES_NONCANONICAL")
    )
    assert result.state == CrossrefIntegrationStateV1()


def test_changed_bytes_cannot_select_their_own_authority() -> None:
    value = json.loads(NORMALIZED.read_bytes())
    value["records"][0]["title"] = ["Caller-selected evidence"]
    result = _integrate(payload=_canonical(value))

    assert result.disposition == "QUARANTINED"
    assert result.quarantine is not None
    assert "NORMALIZED_IDENTITY_MISMATCH" in result.quarantine.reason_codes

    with pytest.raises(TypeError):
        integrate_crossref_normalized_bytes_v1(
            CrossrefIntegrationStateV1(),
            _canonical(value),
            expected_normalized_identity="0" * 64,
        )


def test_runtime_evidence_label_rebinding_cannot_change_admission(monkeypatch) -> None:
    value = json.loads(NORMALIZED.read_bytes())
    value["raw_capture_identity"] = "1" * 64
    value["records"][0]["title"] = ["Runtime-rebound evidence"]
    changed = _canonical(value)
    monkeypatch.setattr(
        integration_module,
        "PHASE2_NORMALIZED_IDENTITY",
        __import__("hashlib").sha256(changed).hexdigest(),
    )
    monkeypatch.setattr(integration_module, "PHASE2_RAW_CAPTURE_IDENTITY", "1" * 64)

    result = _integrate(payload=changed)
    assert result.disposition == "QUARANTINED"
    assert result.quarantine is not None
    assert {
        "NORMALIZED_IDENTITY_MISMATCH",
        "RAW_CAPTURE_IDENTITY_MISMATCH",
    }.issubset(result.quarantine.reason_codes)


def test_runtime_state_label_rebinding_cannot_admit_unqualified_state(
    monkeypatch,
) -> None:
    accepted = _integrate()
    assert accepted.batch is not None
    unqualified = CrossrefIntegrationStateV1((accepted.batch.records[0],), ())
    monkeypatch.setattr(
        integration_module, "PHASE3_EMPTY_STATE_IDENTITY", unqualified.identity
    )
    monkeypatch.setattr(
        integration_module, "PHASE3_ACCEPTED_STATE_IDENTITY", unqualified.identity
    )

    with pytest.raises(CrossrefIntegrationInputRejected, match="not a qualified"):
        _integrate(unqualified)


def test_runtime_hash_helper_injection_cannot_admit_unqualified_state(
    monkeypatch,
) -> None:
    accepted = _integrate()
    assert accepted.batch is not None
    unqualified = CrossrefIntegrationStateV1((accepted.batch.records[0],), ())
    monkeypatch.setattr(
        integration_module,
        "_sha256",
        lambda value: (
            "62846329a1f032711c76f5120705b4c9a1237b92d5de6e9e273da8f25b41475b"
        ),
        raising=False,
    )

    with pytest.raises(CrossrefIntegrationInputRejected, match="not a qualified"):
        _integrate(unqualified)


def test_runtime_canonical_helper_injection_cannot_admit_unqualified_state(
    monkeypatch,
) -> None:
    accepted = _integrate()
    assert accepted.batch is not None
    unqualified = CrossrefIntegrationStateV1((accepted.batch.records[0],), ())
    monkeypatch.setattr(
        integration_module,
        "_canonical_json_bytes",
        lambda value: (
            b'{"applied_batch_identities":[],"record_identities":[],'
            b'"records":[],"schema":"pastila-crossref-integration-state-v1"}\n'
        ),
    )

    with pytest.raises(CrossrefIntegrationInputRejected, match="not a qualified"):
        _integrate(unqualified)


def test_runtime_schema_label_rebinding_cannot_change_output(monkeypatch) -> None:
    expected = _integrate()
    assert expected.batch is not None
    for name in (
        "INTEGRATION_SCHEMA",
        "STATE_SCHEMA",
        "QUARANTINE_SCHEMA",
        "_NORMALIZED_SCHEMA",
    ):
        monkeypatch.setattr(integration_module, name, "caller-rebound-schema")
    monkeypatch.setattr(integration_module, "_RECORD_FIELDS", set())

    actual = _integrate()
    assert actual.disposition == "ACCEPTED"
    assert actual.batch is not None
    assert actual.batch.identity == expected.batch.identity
    assert actual.state.identity == expected.state.identity


def test_unqualified_preexisting_state_cannot_enter_integration_boundary() -> None:
    first = _integrate()
    assert first.batch is not None
    conflicting_state = CrossrefIntegrationStateV1((first.batch.records[0],), ())
    with pytest.raises(
        CrossrefIntegrationInputRejected, match="not a qualified Phase 3 state"
    ):
        _integrate(conflicting_state)


def test_nested_metadata_is_immutable_and_detached_from_parsed_input() -> None:
    result = _integrate()
    assert result.batch is not None
    record = result.batch.records[0]
    published = record.published
    assert published is not None
    mutable_view = published.as_dict()
    mutable_view["date-parts"] = [[9999]]

    assert published.as_dict() != mutable_view
    with pytest.raises(FrozenInstanceError):
        published.canonical_bytes = b"{}\n"  # type: ignore[misc]


def test_state_constructor_rejects_noncanonical_or_duplicate_content() -> None:
    accepted = _integrate()
    first = accepted.state.records[0]

    with pytest.raises(CrossrefIntegrationInputRejected):
        CrossrefIntegrationStateV1((first, first), ())
    with pytest.raises(CrossrefIntegrationInputRejected):
        CrossrefIntegrationStateV1((), ("1" * 64, "1" * 64))
    with pytest.raises(CrossrefIntegrationInputRejected):
        CrossrefIntegrationStateV1([], ())  # type: ignore[arg-type]


def test_quarantine_receipt_is_deterministic() -> None:
    value = json.loads(NORMALIZED.read_bytes())
    value["records"][0]["DOI"] = ""
    payload = _canonical(value)

    first = _integrate(payload=payload)
    second = _integrate(payload=payload)
    assert first.quarantine is not None
    assert second.quarantine is not None
    assert first.quarantine.identity == second.quarantine.identity
    assert first.quarantine.as_dict() == second.quarantine.as_dict()


def test_result_constructor_rejects_unbound_batch_or_quarantine() -> None:
    accepted = _integrate()
    assert accepted.batch is not None
    with pytest.raises(CrossrefIntegrationInputRejected, match="absent"):
        CrossrefIntegrationResultV1(
            "ACCEPTED", CrossrefIntegrationStateV1(), batch=accepted.batch
        )

    malformed = _integrate(payload=b"not-json")
    assert malformed.quarantine is not None
    with pytest.raises(CrossrefIntegrationInputRejected, match="not bound"):
        CrossrefIntegrationResultV1(
            "QUARANTINED", accepted.state, quarantine=malformed.quarantine
        )
