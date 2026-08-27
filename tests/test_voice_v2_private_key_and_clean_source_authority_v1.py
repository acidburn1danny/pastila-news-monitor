from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT / ".pastilaacida-voice-v2-private-key-and-clean-source-authority-v1-evidence"
)


def load(name: str) -> dict[str, object]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_private_key_audit_remains_fail_closed() -> None:
    audit = load("01-private-signing-key-restoration-audit.json")
    assert (
        audit["restoration_result"]
        == "EXACT_PRIVATE_SIGNING_KEY_NOT_LOCALLY_DISCOVERABLE"
    )
    assert audit["replacement_authorized"] is False
    assert all(value == 0 for value in audit["certificate_stores"].values())


def test_clean_candidate_authority_binds_wheel_payload_and_packaging_inputs() -> None:
    authority = load("03-clean-candidate-source-authority.json")
    assert authority["dirty_repository_is_authority"] is False
    assert authority["worktree_unrelated_changes_excluded"] is True
    assert (
        authority["wheel"]["sha256"]
        == "936a4a75e2365afabc71acce38f8b720aa954e62740979fadc090aa9b01d9c41"
    )
    assert authority["production_activation"] == {"expressions": 3, "surfaces": 3}
    inventory = load("02-clean-payload-inventory.json")
    assert inventory["total_files"] > 0
    assert any(item["path"] == "PastilaScout.exe" for item in inventory["files"])
    assert any(item["path"] == "pastila-scout.exe" for item in inventory["files"])


def test_manifest_identities_match_exact_files() -> None:
    manifest = load("manifest.json")
    assert manifest["verdict"] == "SOURCE_AUTHORITY_FROZEN_SIGNING_KEY_BLOCKED"
    for field, name in (
        ("private_key_audit_identity", "01-private-signing-key-restoration-audit.json"),
        ("clean_payload_inventory_identity", "02-clean-payload-inventory.json"),
        (
            "clean_candidate_source_authority_identity",
            "03-clean-candidate-source-authority.json",
        ),
        ("release_boundary_identity", "04-release-boundary.json"),
        ("hashes_identity", "05-hashes.json"),
    ):
        actual = hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest()
        assert manifest[field] == f"sha256:{actual}"
