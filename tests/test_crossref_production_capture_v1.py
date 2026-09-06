"""Offline adversarial qualification for bounded Phase 5 production capture."""

from __future__ import annotations

import inspect
import json
import os
from pathlib import Path

import pytest

import pastila_scout.crossref_production_capture_v1 as capture
from pastila_scout.crossref_production_capture_v1 import (
    CrossrefProductionCaptureError,
    _execute_with_transport_once_v1,
)


class FakeResponse:
    status = 200

    def __init__(self, body: bytes) -> None:
        self._body = body
        self._offset = 0
        self.closed = False

    def getheaders(self):
        return [("Content-Type", "application/json")]

    def read(self, amount: int) -> bytes:
        value = self._body[self._offset : self._offset + amount]
        self._offset += len(value)
        return value

    def close(self) -> None:
        self.closed = True


def response_body(count: int) -> bytes:
    return (
        json.dumps(
            {
                "message": {
                    "items": [
                        {
                            "DOI": f"10.1000/{index}",
                            "URL": None,
                            "created": None,
                            "published": None,
                            "publisher": None,
                            "title": None,
                            "type": None,
                        }
                        for index in range(count)
                    ]
                },
                "message-type": "work-list",
                "message-version": "1.0.0",
                "status": "ok",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode()


def test_offline_seam_invokes_exact_transport_once_and_records_before_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    response = FakeResponse(response_body(10))

    def transport(request):
        calls.append(request)
        return response

    monkeypatch.setattr(
        "socket.socket",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("qualification attempted network access")
        ),
    )

    root = tmp_path / "run"
    receipt = _execute_with_transport_once_v1(root, transport)
    assert calls == [capture.FROZEN_REQUEST]
    assert response.closed is True
    assert receipt.record_count == 10
    assert receipt.transport_mode == "OFFLINE_QUALIFICATION"
    assert receipt.request_identity == capture.frozen_request_identity_v1()
    assert (root / "attempt-consumed.json").is_file()
    assert (root / "raw-capture/response-body.bin").read_bytes() == response_body(10)
    assert (root / "raw-capture/manifest.json").is_file()
    assert (root / "completion.json").read_bytes() == receipt.canonical_bytes
    assert not (root / "normalized-records.json").exists()
    assert not (root / "integration-state.json").exists()


def test_transport_failure_consumes_attempt_and_cannot_retry(tmp_path: Path) -> None:
    calls = 0

    def transport(_request):
        nonlocal calls
        calls += 1
        raise OSError("simulated transport failure")

    root = tmp_path / "run"
    with pytest.raises(OSError, match="transport failure"):
        _execute_with_transport_once_v1(root, transport)
    assert calls == 1
    assert (root / "attempt-consumed.json").is_file()
    with pytest.raises(CrossrefProductionCaptureError, match="new Path"):
        _execute_with_transport_once_v1(root, transport)
    assert calls == 1


def test_clean_runtime_parent_is_created_before_one_shot_execution(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runtime-container" / "run"
    assert not root.parent.exists()
    receipt = _execute_with_transport_once_v1(
        root, lambda _request: FakeResponse(response_body(0))
    )
    assert receipt.record_count == 0
    assert receipt.transport_mode == "OFFLINE_QUALIFICATION"
    assert root.parent.is_dir()
    assert (root / "attempt-consumed.json").is_file()


def test_more_than_ten_records_is_terminal_after_raw_recording(tmp_path: Path) -> None:
    calls = 0

    def transport(_request):
        nonlocal calls
        calls += 1
        return FakeResponse(response_body(11))

    root = tmp_path / "run"
    with pytest.raises(Exception, match="more than 10"):
        _execute_with_transport_once_v1(root, transport)
    assert calls == 1
    assert (root / "raw-capture/response-body.bin").read_bytes() == response_body(11)
    assert not (root / "completion.json").exists()
    with pytest.raises(CrossrefProductionCaptureError, match="new Path"):
        _execute_with_transport_once_v1(root, transport)
    assert calls == 1


def test_completion_interruption_is_terminal_and_cannot_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "run"
    real_link = os.link

    def interrupt_completion(source, destination):
        if Path(destination).name == "completion.json":
            raise OSError("simulated completion interruption")
        return real_link(source, destination)

    monkeypatch.setattr(capture.os, "link", interrupt_completion)
    with pytest.raises(OSError, match="completion interruption"):
        _execute_with_transport_once_v1(
            root, lambda _request: FakeResponse(response_body(2))
        )
    assert (root / "completion.json.pending").is_file()
    assert not (root / "completion.json").exists()

    monkeypatch.setattr(capture.os, "link", real_link)
    calls = 0

    def forbidden_retry(_request):
        nonlocal calls
        calls += 1
        return FakeResponse(response_body(2))

    with pytest.raises(CrossrefProductionCaptureError, match="new Path"):
        _execute_with_transport_once_v1(root, forbidden_retry)
    assert calls == 0
    assert not hasattr(capture, "recover_bounded_crossref_production_capture_v1")


@pytest.mark.parametrize(
    "name",
    [
        "execute_one_shot_capture_v1",
        "_record_raw_capture",
        "_execute_with_transport_once_v1",
        "normalize_capture_v1",
        "authorized_execution_root_v1",
    ],
)
def test_runtime_rebinding_fails_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setattr(capture, name, lambda *_args: None)
    with pytest.raises(CrossrefProductionCaptureError, match="rebound"):
        capture.execute_bounded_crossref_production_capture_v1()
    assert not (tmp_path / "run").exists()


@pytest.mark.parametrize(
    "name",
    ["_build_frozen_request_v1", "_read_bounded_body", "_normalize_item"],
)
def test_transitive_capture_authority_rebinding_fails_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setattr(capture._capture_authority, name, lambda *_args: None)
    with pytest.raises(CrossrefProductionCaptureError, match="rebound"):
        capture.execute_bounded_crossref_production_capture_v1()
    assert not (tmp_path / "run").exists()


def test_external_tls_authority_rebinding_fails_before_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(capture._capture_authority.certifi, "where", lambda: "other")
    with pytest.raises(CrossrefProductionCaptureError, match="rebound"):
        capture.execute_bounded_crossref_production_capture_v1()
    assert not (tmp_path / "run").exists()


def test_runtime_closure_lists_cannot_be_emptied_to_bypass_rebinding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(capture, "_CAPTURE_RUNTIME_CLOSURE", ())
    monkeypatch.setattr(capture, "_EXTERNAL_RUNTIME_CLOSURE", ())
    monkeypatch.setattr(capture, "_LOCAL_CLOSURE", ())
    monkeypatch.setattr(capture._capture_authority, "_build_frozen_request_v1", None)
    with pytest.raises(CrossrefProductionCaptureError, match="rebound"):
        capture.execute_bounded_crossref_production_capture_v1()
    assert not (tmp_path / "run").exists()


def test_phase5_surface_is_exact_and_has_no_downstream_capability() -> None:
    source = Path(capture.__file__).read_text(encoding="utf-8")
    assert "crossref_capture_integration" not in source
    assert "crossref_production_qualification" not in source
    assert "OpenAlex" not in source
    assert "schedule" not in source.casefold()
    assert "publish" not in capture.__all__
    assert "_execute_with_transport_once_v1" not in capture.__all__
    assert (
        len(
            inspect.signature(
                capture.execute_bounded_crossref_production_capture_v1
            ).parameters
        )
        == 0
    )
    expected_root = (
        Path(capture.__file__).resolve().parents[2] / capture.EXECUTION_ROOT_RELATIVE
    )
    existed = expected_root.exists()
    assert capture.authorized_execution_root_v1() == expected_root
    assert expected_root.exists() is existed
    assert capture.FROZEN_REQUEST.maximum_attempts == 1
    assert capture.FROZEN_REQUEST.maximum_redirects == 0
    assert capture.FROZEN_REQUEST.maximum_pages == 1
    assert capture.FROZEN_REQUEST.timeout_seconds == 15
    production_source = inspect.getsource(
        capture.execute_bounded_crossref_production_capture_v1
    )
    assert production_source.index("_create_and_consume_attempt") < (
        production_source.index("DirectCrossrefHttpsTransportV1")
    )
    assert 'transport_mode="PRODUCTION_DIRECT_HTTPS"' in production_source


def test_offline_seam_cannot_claim_direct_https_provenance(tmp_path: Path) -> None:
    receipt = _execute_with_transport_once_v1(
        tmp_path / "run", lambda _request: FakeResponse(response_body(1))
    )
    value = json.loads(receipt.canonical_bytes)
    assert value["transport_mode"] == "OFFLINE_QUALIFICATION"
    assert "PRODUCTION_DIRECT_HTTPS" not in receipt.canonical_bytes.decode()
