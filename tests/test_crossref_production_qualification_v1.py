"""Adversarial offline tests for the Phase 4 production orchestration."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import pastila_scout.crossref_production_qualification_v1 as production
from pastila_scout.crossref_production_qualification_v1 import (
    CrossrefProductionQualificationError,
    OfflineCrossrefResponseV1,
    execute_offline_crossref_production_qualification_v1,
    recover_offline_crossref_production_qualification_v1,
)

ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / ".pastila-runtime/milestone10-crossref-pilot-v2"
NORMALIZED_IDENTITY = "bc2dd86d76c89f9e39f4a99a72db87ef57a5835ea92533a02f942ecc1111f4e0"
RAW_IDENTITY = "3acbdb9f2e54940f5953b497ace279a5884d0ce607f4e77e868de9a667783281"
STATE_IDENTITY = "768ac0572117e39a3cc0f9f4b7d0a255ed116f33b4fd6f5653e09c091ac804d5"


def offline_response() -> OfflineCrossrefResponseV1:
    manifest = json.loads((PROOF / "raw-capture/manifest.json").read_bytes())
    headers = json.loads((PROOF / "raw-capture/response-headers.json").read_bytes())
    return OfflineCrossrefResponseV1(
        manifest["status"],
        tuple(tuple(pair) for pair in headers),
        (PROOF / "raw-capture/response-body.bin").read_bytes(),
    )


def test_complete_path_is_offline_ordered_durable_and_identity_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def network_forbidden(*args, **kwargs):
        raise AssertionError("Phase 4 attempted network access")

    monkeypatch.setattr("socket.socket", network_forbidden)
    root = tmp_path / "run"
    outcome = execute_offline_crossref_production_qualification_v1(
        root, offline_response()
    )

    assert outcome.disposition == "ACCEPTED"
    assert outcome.raw_capture_identity == RAW_IDENTITY
    assert outcome.normalized_identity == NORMALIZED_IDENTITY
    assert outcome.state_after_identity == STATE_IDENTITY
    assert outcome.batch_identity is not None
    assert outcome.quarantine_identity is None
    assert (root / "attempt-consumed.json").exists()
    assert (root / "raw-capture/manifest.json").exists()
    assert (root / "normalized-records.json").read_bytes() == (
        PROOF / "normalized-records.json"
    ).read_bytes()
    assert (root / "integration-state.json").exists()
    assert (root / "completion.json").read_bytes() == outcome.canonical_bytes


def test_runtime_authority_rebinding_fails_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "run"
    monkeypatch.setattr(
        production,
        "integrate_crossref_normalized_bytes_v1",
        lambda state, payload: None,
    )
    with pytest.raises(CrossrefProductionQualificationError, match="rebound"):
        execute_offline_crossref_production_qualification_v1(root, offline_response())
    assert not root.exists()


@pytest.mark.parametrize(
    ("authority", "name"),
    [
        (production._capture_authority, "_consume_attempt_authority_v1"),
        (production._capture_authority, "record_raw_capture_v1"),
        (production._integration_authority, "_decode_document"),
    ],
)
def test_transitive_runtime_rebinding_fails_before_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    authority: object,
    name: str,
) -> None:
    root = tmp_path / "run"
    monkeypatch.setattr(authority, name, lambda *args, **kwargs: None)
    with pytest.raises(CrossrefProductionQualificationError, match="closure"):
        execute_offline_crossref_production_qualification_v1(root, offline_response())
    assert not root.exists()


def test_second_execution_cannot_retry_or_redraw(tmp_path: Path) -> None:
    root = tmp_path / "run"
    response = offline_response()
    execute_offline_crossref_production_qualification_v1(root, response)

    with pytest.raises(CrossrefProductionQualificationError, match="new Path"):
        execute_offline_crossref_production_qualification_v1(root, response)


def test_recovery_revalidates_every_durable_layer_without_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "run"
    original = execute_offline_crossref_production_qualification_v1(
        root, offline_response()
    )

    def network_forbidden(*args, **kwargs):
        raise AssertionError("recovery attempted network access")

    monkeypatch.setattr("socket.socket", network_forbidden)
    assert recover_offline_crossref_production_qualification_v1(root) == original

    normalized = root / "normalized-records.json"
    normalized.write_bytes(normalized.read_bytes() + b" ")
    with pytest.raises(CrossrefProductionQualificationError):
        recover_offline_crossref_production_qualification_v1(root)


def test_atomic_state_publication_recovers_only_matching_pending_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "run"
    real_link = os.link
    calls = 0

    def fail_first_link(source, destination):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("simulated interruption")
        return real_link(source, destination)

    monkeypatch.setattr(production.os, "link", fail_first_link)
    with pytest.raises(OSError, match="simulated interruption"):
        execute_offline_crossref_production_qualification_v1(root, offline_response())
    assert (root / "integration-state.json.pending").exists()
    assert not (root / "integration-state.json").exists()

    monkeypatch.setattr(production.os, "link", real_link)
    outcome = recover_offline_crossref_production_qualification_v1(root)
    assert outcome.disposition == "ACCEPTED"
    assert outcome.state_after_identity == STATE_IDENTITY
    assert not (root / "integration-state.json.pending").exists()


def test_foreign_pending_state_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "run"
    real_link = production.os.link

    def interrupt(source, destination):
        raise OSError("stop")

    production.os.link = interrupt
    try:
        with pytest.raises(OSError):
            execute_offline_crossref_production_qualification_v1(
                root, offline_response()
            )
    finally:
        production.os.link = real_link
    (root / "integration-state.json.pending").write_bytes(b"foreign")
    with pytest.raises(
        CrossrefProductionQualificationError, match="pending publication"
    ):
        recover_offline_crossref_production_qualification_v1(root)


def test_foreign_pending_alongside_published_state_fails_closed(
    tmp_path: Path,
) -> None:
    root = tmp_path / "run"
    execute_offline_crossref_production_qualification_v1(root, offline_response())
    (root / "integration-state.json.pending").write_bytes(b"foreign")
    with pytest.raises(
        CrossrefProductionQualificationError, match="published-state hard-link"
    ):
        recover_offline_crossref_production_qualification_v1(root)


def test_altered_offline_snapshot_is_rejected_before_execution(tmp_path: Path) -> None:
    exact = offline_response()
    with pytest.raises(CrossrefProductionQualificationError, match="proof bytes"):
        OfflineCrossrefResponseV1(exact.status, exact.headers, exact.body + b" ")
    assert not (tmp_path / "run").exists()


def test_module_has_no_production_network_entry_or_policy_expansion() -> None:
    source = Path(production.__file__).read_text(encoding="utf-8")
    assert "DirectCrossrefHttpsTransportV1" not in source
    assert "http.client" not in source
    assert "import TransportOnce" not in source
    assert "OpenAlex" not in source
    assert "schedule" not in source.casefold()
    assert "retention" not in source.casefold()
    assert "publish" not in production.__all__
    assert set(production.__all__) == {
        "EXECUTION_ROOT_RELATIVE",
        "SCHEMA",
        "OfflineCrossrefResponseV1",
        "CrossrefProductionOutcomeV1",
        "CrossrefProductionQualificationError",
        "authorized_qualification_root_v1",
        "execute_offline_crossref_production_qualification_v1",
        "recover_offline_crossref_production_qualification_v1",
    }


def test_symlink_execution_boundary_is_rejected_when_supported(
    tmp_path: Path,
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation unavailable")
    with pytest.raises(CrossrefProductionQualificationError):
        recover_offline_crossref_production_qualification_v1(linked)
