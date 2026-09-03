import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout import semantic_authority_deployment_v2_3_12 as deployment
from pastila_scout import semantic_authority_rfc3161_verifier_v2_3_13 as verifier
from pastila_scout.semantic_authority_capture_orchestrator_v2_3_7 import canonical


def provenance() -> dict[str, object]:
    return {
        "schema": verifier.SCHEMA,
        "platform": verifier.PLATFORM,
        "openssl_version": verifier.OPENSSL_VERSION,
        "runtime_image_index_sha256": verifier.RUNTIME_IMAGE_INDEX_SHA256,
        "runtime_image_amd64_manifest_sha256": verifier.RUNTIME_IMAGE_AMD64_MANIFEST_SHA256,
        "runtime_sbom_sha256": verifier.RUNTIME_SBOM_SHA256,
        "runtime_layer_sha256": list(verifier.RUNTIME_LAYER_SHA256),
        "debian_inrelease_sha256": verifier.DEBIAN_INRELEASE_SHA256,
        "debian_packages_sha256": verifier.DEBIAN_PACKAGES_SHA256,
        "openssl_package_sha256": verifier.OPENSSL_PACKAGE_SHA256,
        "libssl_package_sha256": verifier.LIBSSL_PACKAGE_SHA256,
        "openssl_executable_sha256": verifier.OPENSSL_EXECUTABLE_SHA256,
        "runtime_libssl_sha256": verifier.RUNTIME_LIBSSL_SHA256,
        "runtime_libcrypto_sha256": verifier.RUNTIME_LIBCRYPTO_SHA256,
        "debian_signing_fingerprints": list(verifier.DEBIAN_SIGNING_FINGERPRINTS),
    }


def test_provenance_is_exact_and_v2312_uses_linux_pin():
    verifier.verify_provenance_record(provenance())
    assert verifier.RUNTIME_LAYER_SHA256 == (
        "53c88f1dfeb79b2f207f7f1a03a45e0dc5ed208b9f496de16b98f81189dc0392",
        "eae668646f447b181fe300ae6756351b6167aa2578be449b167ba79ed4926798",
        "ff2e6e687b6ce78177a4cac678dd533c8e72b97469f030783b6bb491f681fd4c",
        "7c40a3faff76845154c32b7b35d5535b201d3bd04f94a0c408f8e98f9ed98ad6",
        "85694cfea2c4dfd425b9947a149670940f0625182653d556ed9c541e0cb1f292",
        "d7d82d76b698080549e693e4b53493dc29835ae4ac836fb2aa2d6ef513e9008c",
        "50475ada0cb12c5af6c0c7c3188df0354108a5096b87a1ba0ca5a34e4e1150d3",
    )
    assert deployment.OPENSSL_SHA256 == verifier.OPENSSL_EXECUTABLE_SHA256
    bad = provenance()
    bad["openssl_version"] = "caller-selected"
    with pytest.raises(ValueError, match="provenance"):
        verifier.verify_provenance_record(bad)
    bad = provenance()
    bad["runtime_layer_sha256"] = list(reversed(verifier.RUNTIME_LAYER_SHA256))
    with pytest.raises(ValueError, match="provenance"):
        verifier.verify_provenance_record(bad)


def test_elf_and_executable_checks_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    elf = bytearray(64)
    elf[:7] = b"\x7fELF\x02\x01\x01"
    elf[18:20] = (62).to_bytes(2, "little")
    verifier.verify_linux_amd64_elf(bytes(elf))
    with pytest.raises(ValueError, match="amd64"):
        verifier.verify_linux_amd64_elf(bytes(elf[:18] + (183).to_bytes(2, "little") + elf[20:]))
    path = tmp_path / "openssl"
    path.write_bytes(elf)
    monkeypatch.setattr(verifier, "OPENSSL_EXECUTABLE_SHA256", verifier.sha256(bytes(elf)))
    verifier.verify_executable(path)
    path.write_bytes(bytes(elf) + b"tampered")
    with pytest.raises(ValueError, match="identity"):
        verifier.verify_executable(path)


def test_qualification_record_closes_code_and_identity_chain():
    root = Path(__file__).resolve().parents[1]
    record_path = root / "docs/artifacts/semantic-contract-v2-3-13-linux-openssl-rfc3161-zero-network-qualification.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    identity = record.pop("qualification_identity")
    assert identity == hashlib.sha256(canonical(record)).hexdigest()
    assert record["module_sha256"] == verifier.sha256(
        (root / "src/pastila_scout/semantic_authority_rfc3161_verifier_v2_3_13.py").read_bytes()
    )
    assert record["test_sha256"] == verifier.sha256(Path(__file__).read_bytes())
    assert record["runtime_image"]["dependency_closure"] == "PASS_EXECUTED_IN_DIGEST_PINNED_OCI_ROOTFS"
