from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "packaging/inno/build-clean-authority-installer-v1.ps1"


def test_clean_source_installer_consumes_frozen_authority_not_git_state() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "ExpectedAuthorityManifestSha256" in source
    assert "dirty_repository_is_authority" in source
    assert "git status" not in source
    assert "git rev-parse" not in source


def test_clean_source_installer_signs_launchers_installer_and_uninstaller() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "foreach($launcher in @('PastilaScout.exe','pastila-scout.exe'))" in source
    assert "SignedUninstaller=yes" in source
    assert "-File `$q$signingScript`$q" in source
    assert "-Operation Verify -Path $installer" in source
    assert "604635DF3EB4CAF406D977987B1A6AA764D83612" in source


def test_clean_source_installer_validates_every_payload_file() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "payload inventory count mismatch" in source
    assert "payload mismatch:" in source
    assert "unexpected payload file count" in source
    assert "GetSHA256OfFile" in source
