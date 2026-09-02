from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pytest

from pastila_scout.semantic_authority_frame_v2_1 import (
    build_frame, canonical_bytes, normalize_doi, segment_utf8_losslessly,
    derive_drand_round, select_canonical_rekor_entry, select_frame_entry,
    select_index, select_snapshot_manifest, sha, verify_drand,
    verify_drand_quorum, verify_rekor_commitment, verify_snapshot_manifest,
)

FREEZE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def rows(registry):
    return [{"registry": registry, "stable_id": registry[0] + "1", "doi": "https://doi.org/10.1/X", "resource_locator": "https://example.test/" + registry.lower(), "publication_type": "article", "language": "en", "access_right": True, "license": "open", "content_digest": "a" * 64}]


def snapshot(registry, source=None):
    source = rows(registry) if source is None else source
    manifest = {"registry": registry, "release_id": "R1", "published_at": "2026-02-01T00:00:00Z", "record_count": len(source), "projected_records_sha256": sha(canonical_bytes(tuple(source))), "archive_sha256": "b" * 64, "external_commitment": "synthetic-proof"}
    return verify_snapshot_manifest(manifest, source, governance_frozen_at=FREEZE, verify_external_manifest=lambda _: True)


def test_snapshot_and_frame_are_order_invariant_and_merge_doi():
    crossref, openalex = snapshot("CROSSREF"), snapshot("OPENALEX")
    one = build_frame([crossref, openalex]); two = build_frame([openalex, crossref])
    assert one == two
    assert one["eligible_count"] == 1
    assert one["entries"][0]["provenance"] == ["CROSSREF:C1", "OPENALEX:O1"]


@pytest.mark.parametrize("mutation", ["count", "digest", "date", "proof"])
def test_snapshot_manifest_fails_closed(mutation):
    source = rows("CROSSREF")
    manifest = {"registry": "CROSSREF", "release_id": "R1", "published_at": "2026-02-01T00:00:00Z", "record_count": 1, "projected_records_sha256": sha(canonical_bytes(tuple(source))), "archive_sha256": "b" * 64, "external_commitment": "proof"}
    if mutation == "count": manifest["record_count"] = 2
    if mutation == "digest": manifest["projected_records_sha256"] = "0" * 64
    if mutation == "date": manifest["published_at"] = "2025-01-01T00:00:00Z"
    with pytest.raises(ValueError):
        verify_snapshot_manifest(manifest, source, governance_frozen_at=FREEZE, verify_external_manifest=lambda _: mutation != "proof")


def test_frame_logs_exclusion_and_rejects_duplicate_and_semantic_field():
    bad = rows("CROSSREF"); bad[0]["access_right"] = False
    frame = build_frame([snapshot("CROSSREF", bad), snapshot("OPENALEX")])
    assert "EXPLICIT_ACQUISITION_RIGHT_MISSING" in {d["reason"] for d in frame["decisions"]}
    duplicate = rows("CROSSREF") * 2
    with pytest.raises(ValueError): build_frame([snapshot("CROSSREF", duplicate), snapshot("OPENALEX")])
    semantic = rows("CROSSREF"); semantic[0]["abstract"] = "forbidden"
    with pytest.raises(ValueError): build_frame([snapshot("CROSSREF", semantic), snapshot("OPENALEX")])


def test_rekor_single_leaf_requires_payload_and_external_signature():
    payload = {"frame": "a" * 64}; root = hashlib.sha256(b"\0" + canonical_bytes(payload)).digest()
    entry = {"body": payload, "log_index": 0, "tree_size": 1, "inclusion_path": [], "signed_root": root.hex(), "tree_signature": "aa", "integrated_time": 1}
    assert verify_rekor_commitment(entry, expected_payload=payload, verify_tree_signature=lambda r, s, sig: r == root and s == 1) == 1
    with pytest.raises(ValueError): verify_rekor_commitment(entry, expected_payload={"frame": "b" * 64}, verify_tree_signature=lambda *_: True)
    with pytest.raises(ValueError): verify_rekor_commitment(entry, expected_payload=payload, verify_tree_signature=lambda *_: False)


def test_drand_pins_chain_round_and_signature():
    signature = b"synthetic-signature"; chain = "c" * 64
    receipt = {"round": 42, "chain_hash": chain, "signature": signature.hex(), "previous_signature": "01", "randomness": hashlib.sha256(signature).hexdigest()}
    assert verify_drand(receipt, expected_round=42, expected_chain_hash=chain, verify_signature=lambda r, p, s: (r, p, s) == (42, b"\1", signature)) == hashlib.sha256(signature).digest()
    for field, value in (("round", 41), ("chain_hash", "d" * 64), ("randomness", "0" * 64)):
        changed = dict(receipt); changed[field] = value
        with pytest.raises(ValueError): verify_drand(changed, expected_round=42, expected_chain_hash=chain, verify_signature=lambda *_: True)


def test_selection_is_deterministic_bound_and_replayable():
    args = dict(governance_identity="a" * 64, frame_root="b" * 64, chain_hash="c" * 64, round_number=42, randomness=b"x" * 32, population_size=7)
    assert select_index(**args) == select_index(**args)
    index, trace = select_index(**args)
    assert 0 <= index < 7 and trace
    changed = dict(args, frame_root="d" * 64)
    assert select_index(**changed)[1] != trace
    with pytest.raises(ValueError): select_index(**dict(args, population_size=0))


def test_lossless_segmenter_uses_actual_unicode_bytes():
    data = "ână\r\nβ\nfinal".encode()
    segments = segment_utf8_losslessly(data)
    assert b"".join(s.text.encode() for s in segments) == data
    assert segments[0].char_end == 5 and segments[0].byte_end == len("ână\r\n".encode())
    assert segments[-1].byte_end == len(data)
    with pytest.raises(UnicodeDecodeError): segment_utf8_losslessly(b"\xff")


def test_canonical_domain_and_doi_are_fail_closed():
    assert normalize_doi(" DOI:10.2/ABC ") == "10.2/abc"
    assert normalize_doi("not-a-doi") is None
    assert normalize_doi("10.2/β") is None
    with pytest.raises(ValueError): canonical_bytes({"x": 1.5})


def test_earliest_snapshot_selection_and_tie_are_fail_closed():
    manifests = [{"published_at": "2026-03-01T00:00:00Z", "id": "late"}, {"published_at": "2026-02-01T00:00:00Z", "id": "early"}]
    assert select_snapshot_manifest(manifests, governance_frozen_at=FREEZE)["id"] == "early"
    with pytest.raises(ValueError):
        select_snapshot_manifest(manifests + [{"published_at": "2026-02-01T00:00:00Z", "id": "tie"}], governance_frozen_at=FREEZE)


def test_canonical_rekor_entry_is_earliest_valid():
    payload = {"frame": "a" * 64}; leaf = hashlib.sha256(b"\0" + canonical_bytes(payload)).digest()
    root = hashlib.sha256(b"\1" + leaf + leaf).hexdigest()
    def item(index): return {"body": payload, "log_index": index, "tree_size": 2, "inclusion_path": [leaf.hex()], "signed_root": root, "tree_signature": "aa", "integrated_time": index + 1}
    assert select_canonical_rekor_entry([item(1), item(0)], expected_payload=payload, verify_tree_signature=lambda *_: True)["log_index"] == 0


def test_drand_round_derivation_and_two_endpoint_quorum():
    assert derive_drand_round(integrated_time=100, genesis_time=0, period_seconds=30) == 2885
    signature = b"sig"; chain = "c" * 64
    base = {"round": 2885, "chain_hash": chain, "signature": signature.hex(), "previous_signature": "01", "randomness": hashlib.sha256(signature).hexdigest()}
    assert verify_drand_quorum([dict(base, endpoint="a"), dict(base, endpoint="b")], expected_round=2885, expected_chain_hash=chain, verify_signature=lambda *_: True) == hashlib.sha256(signature).digest()
    with pytest.raises(ValueError): verify_drand_quorum([dict(base, endpoint="a"), dict(base, endpoint="a")], expected_round=2885, expected_chain_hash=chain, verify_signature=lambda *_: True)


def test_selection_is_directly_bound_to_frame_closure():
    frame = build_frame([snapshot("CROSSREF"), snapshot("OPENALEX")])
    entry, trace = select_frame_entry(frame, governance_identity="a" * 64, chain_hash="c" * 64, round_number=1, randomness=b"x" * 32)
    assert entry == frame["entries"][0] and trace
    broken = dict(frame, merkle_root="0" * 64)
    with pytest.raises(ValueError): select_frame_entry(broken, governance_identity="a" * 64, chain_hash="c" * 64, round_number=1, randomness=b"x" * 32)


@pytest.mark.parametrize("name,field", [
    ("semantic-contract-v2-objective-selection-v2-1-zero-frame-qualification.json", "qualification_identity"),
    ("semantic-contract-v2-objective-selection-v2-1-zero-frame-audit.json", "audit_identity"),
])
def test_frozen_zero_frame_records_have_canonical_identities(name, field):
    path = Path(__file__).resolve().parents[1] / "docs" / "artifacts" / name
    record = json.loads(path.read_text(encoding="utf-8"))
    body = dict(record); expected = body.pop(field)
    assert sha(canonical_bytes(body)) == expected
    assert record.get("real_frame_executed", False) is False
