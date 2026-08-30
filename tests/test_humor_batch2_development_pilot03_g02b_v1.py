"""Verify Pilot 03's pathless, source-bound, zero-construction G02B release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pastila_scout.humor_batch2_constructor_access_v1 import prepare_development_constructor_access_v1

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def seal(namespace: str, value: Any) -> str:
    return hashlib.sha256(canonical({"namespace": namespace, "value": value})).hexdigest()


def test_g02b_release_is_source_bound_label_blind_and_unconsumed() -> None:
    packet = json.loads((ART / "humor-mechanics-batch2-development-pilot03-constructor-facing-assignment-g02b-v1.json").read_text(encoding="utf-8"))
    release_path = ART / "humor-mechanics-batch2-development-pilot03-constructor-access-release-v1.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    audit = json.loads((ART / "humor-mechanics-batch2-development-pilot03-g02b-preconstruction-audit-v1.json").read_text(encoding="utf-8"))
    source = (ART / "humor-mechanics-batch2-development-pilot03-ingestion-v1/source.utf8.txt").read_bytes()
    packet_core = dict(packet); packet_id = packet_core.pop("constructor_facing_packet_identity")
    assert seal("B2_DEVELOPMENT_PILOT03_CONSTRUCTOR_PACKET_G02B_SOURCE_BOUND_V1", packet_core) == packet_id
    assert seal("B2_DEVELOPMENT_PILOT03_CONSTRUCTOR_ACCESS_RELEASE_V1", release["release_core"]) == release["release_identity"]
    audit_core = dict(audit); audit_id = audit_core.pop("audit_identity")
    assert seal("B2_DEVELOPMENT_PILOT03_G02B_AUDIT_V1", audit_core) == audit_id
    source_object = packet["source_object"]
    assert source_object["source_text_utf8"].encode() == source
    assert len(source) == source_object["byte_length"] == 518
    assert hashlib.sha256(source).hexdigest() == source_object["sha256"]
    visible = canonical(packet).lower()
    for token in (b"m13", b"absurd_logical_extension", b"mapping_commitment", b"conformance_schema", b"removal_test"):
        assert token not in visible
    assert packet["creative_premise_family_id"] == "UNASSIGNED"
    assert packet["candidate_surface"] is None and packet["constructor_invoked"] is False
    assert all(value is False for value in packet["authority_matrix"].values())
    assert release["release_core"]["single_use_state"] == "UNCONSUMED_0_OF_1"
    assert release["transport_policy"]["constructor_invocation_authorized"] is False
    assert audit["verdict"] == "READY_FOR_BOUNDED_DEVELOPMENT_CONSTRUCTION_DECISION"
    assert audit["deterministic_blockers_remaining"] == []
    prepared = prepare_development_constructor_access_v1(release_bytes=release_path.read_bytes())
    assert prepared.packet_identity == packet_id
    assert prepared.release_identity == release["release_identity"]
