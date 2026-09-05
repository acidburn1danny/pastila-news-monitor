"""Offline identity closure for the Milestone 10 Phase 2 qualification."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pastila_scout.crossref_pilot_offline_v1 import (
    CA_BUNDLE_SHA256,
    WIRE_REQUEST_BYTES,
    frozen_request_identity_v1,
)

ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION = (
    ROOT
    / "docs"
    / "artifacts"
    / "milestone10-phase2-crossref-pilot-offline-qualification-v1.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_phase2_qualification_schema_identity_and_zero_activity() -> None:
    value = json.loads(QUALIFICATION.read_bytes())
    assert set(value) == {
        "design_sha256",
        "dependency_manifest_sha256",
        "foundation_commit",
        "frozen_request_identity",
        "implementation_sha256",
        "invariants",
        "phase1_authority_identity",
        "phase1_commit",
        "qualification_test_sha256",
        "schema",
        "test_sha256",
        "tls_ca_bundle_sha256",
        "verdict",
        "wire_request_sha256",
        "zero_activity",
    }
    assert value["schema"] == "pastila-crossref-pilot-phase2-offline-qualification-v1"
    assert value["verdict"] == "PASS_OFFLINE_PRENETWORK_IMPLEMENTATION"
    assert value["foundation_commit"] == "3fa29f45ae3d4ee57b495f39dc5518776c5c2da2"
    assert value["phase1_commit"] == "e75dcdea4aa6dc8b89645ec9f9dcf0c1fb0d42a8"
    assert value["phase1_authority_identity"] == (
        "3ee1f209bf4b83c07d47b95c7bc4f76485bfcbfe7b7f73cffb5664fd533555c4"
    )
    assert value["frozen_request_identity"] == frozen_request_identity_v1()
    assert value["tls_ca_bundle_sha256"] == CA_BUNDLE_SHA256
    assert (
        value["wire_request_sha256"] == hashlib.sha256(WIRE_REQUEST_BYTES).hexdigest()
    )
    assert value["implementation_sha256"] == sha256(
        ROOT / "src" / "pastila_scout" / "crossref_pilot_offline_v1.py"
    )
    assert value["test_sha256"] == sha256(
        ROOT / "tests" / "test_crossref_pilot_offline_v1.py"
    )
    assert value["design_sha256"] == sha256(
        ROOT / "docs" / "milestone10-phase2-crossref-pilot-offline.md"
    )
    assert value["qualification_test_sha256"] == sha256(Path(__file__))
    assert value["dependency_manifest_sha256"] == sha256(ROOT / "pyproject.toml")
    assert value["zero_activity"] == {
        "crossref_network_requests": 0,
        "metadata_records_acquired": 0,
        "normalized_production_record_sets": 0,
    }
    assert value["invariants"] == {
        "atomic_normalization": "PASS",
        "body_limit_streaming_sentinel": "PASS",
        "closed_capture_record_normalize_order": "PASS",
        "direct_pinned_ca_tls_no_proxy": "PASS",
        "durable_pretransport_attempt_consumption": "PASS",
        "exact_crossref_envelope": "PASS",
        "exact_frozen_request": "PASS",
        "exact_http11_wire_request": "PASS",
        "no_redirect_retry_or_pagination": "PASS",
        "raw_normalized_identity_separation": "PASS",
        "raw_request_response_identity_binding": "PASS",
        "recursive_normalized_immutability": "PASS",
        "single_use_concrete_adapter": "PASS",
        "strict_response_and_json_profile": "PASS",
        "total_monotonic_deadline": "PASS",
        "truthful_canonical_parsed_headers": "PASS",
    }
