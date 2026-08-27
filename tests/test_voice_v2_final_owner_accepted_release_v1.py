from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".pastilaacida-voice-v2-final-owner-accepted-release-v1-evidence"


def load(name: str) -> dict[str, object]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_owner_acceptance_covers_all_final_ui_changes() -> None:
    value = load("01-owner-acceptance.json")
    assert value["accepted"] is True
    assert len(value["accepted_visual_changes"]) == 4


def test_exact_final_artifacts_and_activation_are_frozen() -> None:
    artifacts = load("02-release-artifacts.json")
    installation = load("03-installation-and-activation.json")
    assert (
        artifacts["installer"]["sha256"]
        == "18d0e52927dfbe765874ee2510583d359630c93f5cf90b74a7e8f369125ce09d"
    )
    assert (
        artifacts["installed_gui"]["sha256"]
        == "5e55f428f2726c0b4810ce9f0efbc1d4c44f1a23ebe5ae2173eed8cd18c00656"
    )
    assert artifacts["signer_thumbprint"] == "604635DF3EB4CAF406D977987B1A6AA764D83612"
    assert installation["final_status"] == "success"
    assert installation["activation_status"] == "activated"


def test_release_has_zero_open_gaps_and_exact_manifest_links() -> None:
    gaps = load("04-final-residual-gap-audit.json")
    assert gaps["open_production_binding_gaps"] == 0
    assert gaps["open_release_packaging_gaps"] == 0
    assert gaps["open_ui_acceptance_gaps"] == 0
    assert gaps["production_activation"] == {"expressions": 3, "surfaces": 3}
    manifest = load("manifest.json")
    assert (
        manifest["verdict"]
        == "VOICE_V2_SIGNED_PRODUCTION_RELEASE_OWNER_ACCEPTED_AND_FROZEN"
    )
    for field, name in (
        ("owner_acceptance_identity", "01-owner-acceptance.json"),
        ("artifact_identity", "02-release-artifacts.json"),
        ("installation_identity", "03-installation-and-activation.json"),
        ("final_residual_gap_audit_identity", "04-final-residual-gap-audit.json"),
        ("hashes_identity", "05-hashes.json"),
    ):
        actual = hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest()
        assert manifest[field] == f"sha256:{actual}"
