"""Supply-chain and platform pins for the V2.3.13 Linux RFC-3161 verifier."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping

SCHEMA = "PASTILA_RFC3161_OPENSSL_PROVENANCE_V2_3_13"
RUNTIME_IMAGE_INDEX_SHA256 = "edf6433343f65f94707985869aeaafe8beadaeaee11c4bc02068fca52dce28dd"
RUNTIME_IMAGE_AMD64_MANIFEST_SHA256 = "da6cc0443346c30914c68d265b8dba465cb85708c572d97846122fd036edc003"
RUNTIME_SBOM_SHA256 = "fbe29777e66f0a992e9629621256776cde33fa3d57ce07152141fd77a629a808"
RUNTIME_LAYER_SHA256 = (
    "53c88f1dfeb79b2f207f7f1a03a45e0dc5ed208b9f496de16b98f81189dc0392",
    "eae668646f447b181fe300ae6756351b6167aa2578be449b167ba79ed4926798",
)
DEBIAN_INRELEASE_SHA256 = "a3f869d29c521a824ac8a9d7619b2539532af2d3ce5d5003c25e1df8f497bb23"
DEBIAN_PACKAGES_SHA256 = "83b7feb4a963517002e20c497f3482f3e8f419b8b04598e89efdb9b58bafc6d5"
OPENSSL_PACKAGE_SHA256 = "c10711cab7bdaf56f707c5b55b5f27e4fba9019bd7c1ff12540adc9322f206ae"
LIBSSL_PACKAGE_SHA256 = "7fc9f0372f9271eaad49dbe373f858897853bb02eef6f30f25112cebf2f4afd0"
OPENSSL_EXECUTABLE_SHA256 = "83a9c490e5cd0f8dc19a31438269d82c7b096e51ca2198290468c3766762bfae"
RUNTIME_LIBSSL_SHA256 = "0ee209617de171cebc07295b1b997a3aa15bf0a8ff99f1a4a2df39bcb7b4237f"
RUNTIME_LIBCRYPTO_SHA256 = "27a68367828749ef0180c14dbb9beb22729b472c4bf764ab8b0a724a5753962b"
OPENSSL_VERSION = "3.5.4-1~deb13u1"
PLATFORM = "linux/amd64"
DEBIAN_SIGNING_FINGERPRINTS = (
    "B8B80B5B623EAB6AD8775C45B7C5D7D6350947F8",
    "04B54C3CDCA79751B16BC6B5225629DF75B188BD",
    "41587F7DB8C774BCCF131416762F67A0B2C39DE4",
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def verify_linux_amd64_elf(payload: bytes) -> None:
    if len(payload) < 20 or payload[:7] != b"\x7fELF\x02\x01\x01":
        raise ValueError("OpenSSL is not ELF64 little-endian")
    if int.from_bytes(payload[18:20], "little") != 62:
        raise ValueError("OpenSSL is not amd64")


def verify_executable(path: Path) -> None:
    if not path.is_file() or path.is_symlink():
        raise ValueError("OpenSSL executable path")
    payload = path.read_bytes()
    verify_linux_amd64_elf(payload)
    if sha256(payload) != OPENSSL_EXECUTABLE_SHA256:
        raise ValueError("OpenSSL executable identity")


def verify_provenance_record(value: Mapping[str, object]) -> None:
    required = {
        "schema", "platform", "openssl_version", "runtime_image_index_sha256",
        "runtime_image_amd64_manifest_sha256", "runtime_sbom_sha256",
        "runtime_layer_sha256",
        "debian_inrelease_sha256", "debian_packages_sha256",
        "openssl_package_sha256", "libssl_package_sha256",
        "openssl_executable_sha256", "runtime_libssl_sha256",
        "runtime_libcrypto_sha256", "debian_signing_fingerprints",
    }
    expected = {
        "schema": SCHEMA, "platform": PLATFORM, "openssl_version": OPENSSL_VERSION,
        "runtime_image_index_sha256": RUNTIME_IMAGE_INDEX_SHA256,
        "runtime_image_amd64_manifest_sha256": RUNTIME_IMAGE_AMD64_MANIFEST_SHA256,
        "runtime_sbom_sha256": RUNTIME_SBOM_SHA256,
        "runtime_layer_sha256": list(RUNTIME_LAYER_SHA256),
        "debian_inrelease_sha256": DEBIAN_INRELEASE_SHA256,
        "debian_packages_sha256": DEBIAN_PACKAGES_SHA256,
        "openssl_package_sha256": OPENSSL_PACKAGE_SHA256,
        "libssl_package_sha256": LIBSSL_PACKAGE_SHA256,
        "openssl_executable_sha256": OPENSSL_EXECUTABLE_SHA256,
        "runtime_libssl_sha256": RUNTIME_LIBSSL_SHA256,
        "runtime_libcrypto_sha256": RUNTIME_LIBCRYPTO_SHA256,
        "debian_signing_fingerprints": list(DEBIAN_SIGNING_FINGERPRINTS),
    }
    if set(value) != required or dict(value) != expected:
        raise ValueError("OpenSSL provenance record")
