from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / ".pastilaacida-voice-v2-host-signing-key-and-clean-source-closure-v1-evidence"
)


def load(name: str) -> dict[str, object]:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_host_identity_has_exact_private_signing_key() -> None:
    value = load("01-host-current-user-signing-key.json")
    assert value["effective_windows_user"] == "PASTILAACIDA\\black"
    assert value["thumbprint"] == "604635DF3EB4CAF406D977987B1A6AA764D83612"
    assert value["has_private_key"] is True
    assert value["code_signing_eku"] == "1.3.6.1.5.5.7.3.3"


def test_context_reconciliation_preserves_preliminary_audit() -> None:
    value = load("02-context-reconciliation.json")
    assert value["sandbox_current_user"] == "PastilaAcida\\CodexSandboxOffline"
    assert value["host_result"] == "CERTIFICATE_AND_PRIVATE_KEY_PRESENT"
    assert value["supersession_scope"] == "PRIVATE_KEY_DISCOVERABILITY_ONLY"


def test_closure_and_manifest_are_exact() -> None:
    closure = load("03-closure.json")
    assert closure["clean_candidate_source_authority_status"] == "FROZEN"
    assert closure["private_signing_key_status"] == "AVAILABLE_IN_HOST_USER_CONTEXT"
    assert closure["production_activation"] == {"expressions": 3, "surfaces": 3}
    manifest = load("manifest.json")
    assert (
        manifest["verdict"]
        == "PRIVATE_KEY_AVAILABLE_AND_CLEAN_CANDIDATE_SOURCE_AUTHORITY_FROZEN"
    )
    for field, filename in (
        ("host_signing_key_identity", "01-host-current-user-signing-key.json"),
        ("context_reconciliation_identity", "02-context-reconciliation.json"),
        ("clean_candidate_source_authority_identity", "03-closure.json"),
        ("hashes_identity", "04-hashes.json"),
    ):
        actual = hashlib.sha256((EVIDENCE / filename).read_bytes()).hexdigest()
        assert manifest[field] == f"sha256:{actual}"
