from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path

from pastila_scout.windows_release_orchestration_v1 import _release_identity

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
RELEASE_IDENTITY = ROOT / "packaging" / "windows" / "release-identity.json"


def test_product_version_and_windows_revision_have_separate_authorities() -> None:
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    authority = json.loads(RELEASE_IDENTITY.read_text(encoding="utf-8"))
    resolved = _release_identity(ROOT)

    assert project["version"] == resolved["product_version"] == "1.1.8"
    assert authority["product_version_authority"] == ("pyproject.toml:project.version")
    assert "product_version" not in authority
    assert authority["windows_release_revision"] == "r3"
    assert resolved["windows_release_revision"] == "r3"


def test_executable_and_installer_metadata_derive_the_canonical_version() -> None:
    version = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]["version"]
    template = (ROOT / "packaging" / "pyinstaller" / "version_info.txt.in").read_text(
        encoding="utf-8"
    )
    build = (ROOT / "packaging" / "pyinstaller" / "build.ps1").read_text(
        encoding="utf-8"
    )
    installer = (ROOT / "packaging" / "inno" / "PastilaScout.iss").read_text(
        encoding="utf-8"
    )
    wrapper = (ROOT / "packaging" / "inno" / "build-release-installer.ps1").read_text(
        encoding="utf-8"
    )

    assert "filevers=({FILE_VERSION})" in template
    assert "prodvers=({PRODUCT_VERSION})" in template
    assert "StringStruct('ProductVersion', '{CANONICAL_VERSION}')" in template
    assert 'metadata.version("pastila-news-monitor")' in build
    assert "pyproject.toml" in wrapper and "--app-version', $appVersion" in wrapper
    assert "AppVersion={#AppVersion}" in installer
    assert "VersionInfoVersion={#AppVersion}" in installer
    assert "OutputBaseFilename=PastilaScout-{#AppVersion}-Setup" in installer
    numeric = ", ".join((*version.split("."), "0"))
    rendered = (
        template.replace("{FILE_VERSION}", numeric)
        .replace("{PRODUCT_VERSION}", numeric)
        .replace("{CANONICAL_VERSION}", version)
    )
    assert "filevers=(1, 1, 8, 0)" in rendered
    assert "prodvers=(1, 1, 8, 0)" in rendered
    assert "StringStruct('FileVersion', '1.1.8')" in rendered
    assert "StringStruct('ProductVersion', '1.1.8')" in rendered


def test_release_artifact_names_and_stable_installer_identity_are_governed() -> None:
    authority = json.loads(RELEASE_IDENTITY.read_text(encoding="utf-8"))
    names = authority["artifact_names"]
    identity = authority["installer_identity"]

    assert names["installer"].format(product_version="1.1.8") == (
        "PastilaScout-1.1.8-Setup.exe"
    )
    assert (
        names["release_receipt"].format(
            product_version="1.1.8", windows_release_revision="r3"
        )
        == "PastilaScout-1.1.8-Windows-r3-release-receipt.json"
    )
    assert (
        names["sha256_receipt"].format(
            product_version="1.1.8", windows_release_revision="r3"
        )
        == "PastilaScout-1.1.8-Windows-r3-sha256.json"
    )
    assert identity == {
        "app_id": "PastilaScout",
        "display_name": "Pastila Scout",
        "architecture": "x64compatible",
        "install_directory": r"{localappdata}\Programs\PastilaScout",
    }
    installer = (ROOT / "packaging" / "inno" / "PastilaScout.iss").read_text(
        encoding="utf-8"
    )
    assert "AppId=PastilaScout" in installer
    assert r"DefaultDirName={localappdata}\Programs\PastilaScout" in installer


def test_packaged_r2_history_remains_immutable_and_not_current_authority() -> None:
    authority = json.loads(RELEASE_IDENTITY.read_text(encoding="utf-8"))
    historical = authority["historical_parent"]
    assert historical == {
        "tag": "packaged-owner-v0.1.0-r2-episode-draft-v1-verified",
        "commit": "5364286c8c40ae3294474066f6c3a4895c50c9c1",
    }
    peeled = subprocess.check_output(
        ["git", "rev-parse", f"{historical['tag']}^{{}}"], text=True
    ).strip()
    assert peeled == historical["commit"]


def test_failed_1_1_0_candidate_is_explicitly_historical() -> None:
    authority = json.loads(RELEASE_IDENTITY.read_text(encoding="utf-8"))
    assert authority["failed_clean_pc_candidate"] == {
        "product_version": "1.1.0",
        "windows_release_revision": "r3",
        "status": "FAILED_CLEAN_PC_INSTALLATION_ACCEPTANCE",
        "installer_sha256": (
            "b3c15f8e563bd07446dc1a062031a1eb348272cc36ec46bcb87ddb9e30f3bdfe"
        ),
        "defects": [
            "automatic development repository chooser",
            "provider-unavailable onboarding deadlock",
        ],
    }
    assert authority["current_candidate"] == {
        "status": "PENDING_REBUILD_AND_CLEAN_PC_ACCEPTANCE",
        "remediation_source_commit": "ae04a40566fc0e7033c2a96e86c3b5b08d2d2aca",
    }


def test_no_stale_product_version_is_active_in_release_metadata() -> None:
    active = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            PYPROJECT,
            RELEASE_IDENTITY,
            ROOT / "packaging" / "inno" / "build-release-installer.ps1",
            ROOT / "src" / "pastila_scout" / "windows_release_orchestration_v1.py",
        )
    )
    without_history = active.replace("packaged-owner-v0.1.0-r2", "historical-r2")
    assert 'version = "0.1.0"' not in without_history
    assert "owner rebuild version must remain 0.1.0" not in without_history
    assert "'--app-version', '0.1.0'" not in without_history
