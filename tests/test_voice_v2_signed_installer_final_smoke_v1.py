from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".pastilaacida-voice-v2-signed-installer-final-smoke-v1-evidence"


def load(name: str) -> dict[str, object]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_signed_build_uses_exact_governed_signer() -> None:
    build = load("01-signed-build.json")
    assert build["signer_thumbprint"] == "604635DF3EB4CAF406D977987B1A6AA764D83612"
    assert build["signed_payload_file_count"] == 990


def test_installation_and_smoke_passed() -> None:
    install = load("02-installation.json")
    smoke = load("03-desktop-smoke.json")
    assert install["final_status"] == "success"
    assert install["activation_status"] == "activated"
    assert install["surface_publication_status"] == "published"
    assert smoke["cli_version"] == "1.1.7"
    assert smoke["desktop_alive_after_seconds"] == 10
    assert smoke["startup_integrity_error_observation"] == (
        "NOT_VISIBLE_DURING_HIDDEN_AUTOMATED_SMOKE"
    )


def test_release_boundary_is_closed_and_manifest_is_exact() -> None:
    boundary = load("04-release-boundary.json")
    assert boundary["open_release_packaging_gaps"] == 0
    assert boundary["production_activation"] == {"expressions": 3, "surfaces": 3}
    assert boundary["model_provider_model_load_calls"] == [0, 0, 0]
    manifest = load("manifest.json")
    assert (
        manifest["verdict"] == "SIGNED_INSTALLER_BUILD_INSTALL_AND_DESKTOP_SMOKE_PASSED"
    )
    for field, filename in (
        ("build_identity", "01-signed-build.json"),
        ("installation_identity", "02-installation.json"),
        ("desktop_smoke_identity", "03-desktop-smoke.json"),
        ("release_boundary_identity", "04-release-boundary.json"),
        ("hashes_identity", "05-hashes.json"),
    ):
        actual = hashlib.sha256((EVIDENCE / filename).read_bytes()).hexdigest()
        assert manifest[field] == f"sha256:{actual}"
