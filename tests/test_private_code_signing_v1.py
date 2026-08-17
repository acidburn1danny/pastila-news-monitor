from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "packaging/windows/signing-authority-v1.json"
CERTIFICATE = ROOT / "packaging/signing/PastilaAcida-Private-Code-Signing-V1.cer"
SIGNER = ROOT / "packaging/signing/invoke-authenticode-v1.ps1"
WRAPPER = ROOT / "packaging/inno/build-release-installer.ps1"
ORCHESTRATOR = ROOT / "src/pastila_scout/windows_release_orchestration_v1.py"
ISS = ROOT / "packaging/inno/PastilaScout.iss"


def authority() -> dict[str, object]:
    return json.loads(AUTHORITY.read_text(encoding="utf-8"))


def test_signing_config_is_public_and_contains_no_secret() -> None:
    value = authority()
    serialized = json.dumps(value).casefold()
    assert value["schema"] == "pastilaacida-authenticode-signing-authority-v1"
    assert value["signing_mode"] == "private_signing_required"
    assert not any(
        token in serialized
        for token in (
            "pfx_password",
            "private_key_bytes",
            "signing_pin",
            "token_secret",
        )
    )
    assert value["certificate"]["private_key_export_policy"] == "NON_EXPORTABLE"


def test_public_certificate_is_hash_bound_and_non_secret() -> None:
    value = authority()["certificate"]
    assert CERTIFICATE.suffix == ".cer"
    assert (
        hashlib.sha256(CERTIFICATE.read_bytes()).hexdigest()
        == value["public_certificate_sha256"]
    )
    assert CERTIFICATE.read_bytes()[:4] != b"PK\x03\x04"


def test_exact_thumbprint_selection_and_no_automatic_certificate_choice() -> None:
    source = SIGNER.read_text(encoding="utf-8")
    assert "Where-Object Thumbprint -ceq $thumb" in source
    assert "/sha1 $thumb /fd SHA256" in source
    assert " /a " not in source
    assert re.fullmatch(r"[0-9A-F]{40}", authority()["certificate"]["thumbprint"])


def test_private_mode_fails_closed_for_certificate_tool_signer_and_unsigned() -> None:
    source = SIGNER.read_text(encoding="utf-8")
    assert "exact certificate is missing or ambiguous" in source
    assert "artifact has the wrong signer" in source
    assert "artifact is unsigned" in source
    orchestration = ORCHESTRATOR.read_text(encoding="utf-8")
    assert 'raise ReleaseOrchestrationError("SignTool is required")' in orchestration
    assert (
        'raise ReleaseOrchestrationError("public signing provider is not configured")'
        in orchestration
    )


def test_inner_executables_are_signed_before_installer_construction() -> None:
    source = WRAPPER.read_text(encoding="utf-8")
    signing = source.index(
        "foreach($launcher in @('PastilaScout.exe','pastila-scout.exe'))"
    )
    orchestration = source.index("& $PythonExecutable @arguments")
    assert signing < orchestration
    assert "Copy-Item -LiteralPath $BundleRoot" in source
    assert "--signing-mode', 'private_signing_required'" in source


def test_inno_signs_installer_and_uninstaller_through_one_external_signer() -> None:
    source = ISS.read_text(encoding="utf-8")
    assert "#include AuthenticodeSetupInclude" in source
    orchestration = ORCHESTRATOR.read_text(encoding="utf-8")
    assert (
        '"SignTool=PastilaAcidaAuthenticodeV1 $f\\nSignedUninstaller=yes\\n"'
        in orchestration
    )
    assert "/SPastilaAcidaAuthenticodeV1=" in orchestration
    assert 'f"-File $q{signer}$q -Operation Sign -Path $f "' in orchestration
    assert 'f"-SignToolPath $q{signtool.resolve()}$q"' in orchestration


def test_installer_is_verified_before_final_hash_and_receipt_completion() -> None:
    source = ORCHESTRATOR.read_text(encoding="utf-8")
    verification = source.index("metadata = _authenticode(")
    final_hash = source.index('plan["installer_sha256"] = _hash(installer)')
    completed = source.index('plan["orchestration_result"] = "completed"')
    assert verification < final_hash < completed


def test_receipt_schema_records_public_signer_metadata() -> None:
    source = ORCHESTRATOR.read_text(encoding="utf-8")
    for field in (
        "mode",
        "status",
        "signer_subject",
        "signer_thumbprint",
        "public_certificate_sha256",
        "file_digest_algorithm",
        "timestamp_status",
        "trust_scope",
    ):
        assert f'"{field}"' in source


def test_historical_unsigned_candidate_remains_historical() -> None:
    identity = json.loads(
        (ROOT / "packaging/windows/release-identity.json").read_text(encoding="utf-8")
    )
    assert identity["failed_clean_pc_candidate"]["status"] == (
        "FAILED_CLEAN_PC_INSTALLATION_ACCEPTANCE"
    )
    assert identity["current_candidate"]["status"] == (
        "PENDING_REBUILD_AND_CLEAN_PC_ACCEPTANCE"
    )


def test_repository_contains_no_pfx_or_private_key_material() -> None:
    forbidden_suffixes = {".pfx", ".p12", ".pvk", ".key"}
    files = [
        path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts
    ]
    assert not [path for path in files if path.suffix.casefold() in forbidden_suffixes]


def test_timestamp_and_commercial_replacement_are_explicit() -> None:
    value = authority()
    assert value["timestamp"] == {
        "status": "NOT_CONFIGURED_PRIVATE_V1",
        "rfc3161_url": None,
        "future_configuration_required_for_public_signing": True,
    }
    assert "commercial" in value["commercial_replacement"].casefold()


def test_tamper_regression_is_a_disposable_live_security_gate() -> None:
    documentation = (
        ROOT / "docs/windows-application/PrivateCodeSigningV1.md"
    ).read_text(encoding="utf-8")
    assert "fail-closed" in documentation
    assert "external signing work root" in documentation
    assert "Never distribute a private key or PFX" in documentation
