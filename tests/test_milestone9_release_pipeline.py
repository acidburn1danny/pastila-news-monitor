import copy

import pytest
from pathlib import Path

from pastila_scout.milestone9_proof_boundary import SCHEDULE_RULE, derive_schedule
from pastila_scout.milestone9_release_pipeline import (
    OPENSSL_EXECUTABLE_SHA256,
    RELEASE_SCHEMA,
    RUNTIME_IMAGE_INDEX_SHA256,
    TSA_ENDPOINT,
    bind_validated_request,
    compute_identity,
    identity,
    validate_release,
)


def release():
    value = {
        "schema": RELEASE_SCHEMA,
        "freeze_commit": "a" * 40,
        "freeze_tree": "b" * 40,
        "freeze_epoch": 1,
        "workflow_template_sha256": "c" * 64,
        "pipeline_sha256": "d" * 64,
        "schedule_rule": SCHEDULE_RULE,
        "scheduled_utc": derive_schedule(1)[0],
        "schedule_cron": derive_schedule(1)[1],
        "scheduler_delay_hours": 24,
        "artifact_retention_days": 30,
        "runtime_image_index_sha256": RUNTIME_IMAGE_INDEX_SHA256,
        "openssl_executable_sha256": OPENSSL_EXECUTABLE_SHA256,
        "tsa_endpoint": TSA_ENDPOINT,
    }
    value["release_identity"] = compute_identity(value, "release_identity")
    return value


def validation(value, query=b"query"):
    from pastila_scout.milestone9_release_pipeline import sha256, VALIDATION_SCHEMA
    row = {
        "schema": VALIDATION_SCHEMA,
        "release_identity": value["release_identity"],
        "query_sha256": sha256(query),
        "query_length": len(query),
        "runtime_image_index_sha256": RUNTIME_IMAGE_INDEX_SHA256,
        "openssl_executable_sha256": OPENSSL_EXECUTABLE_SHA256,
        "offline_network": "NETWORK_NONE",
        "query_semantics": "SHA256_IMPRINT_NONCE_CERTREQ_NO_POLICY_NO_EXTENSIONS",
    }
    row["validation_identity"] = compute_identity(row, "validation_identity")
    return row


def test_phase_records_bind_exact_query_bytes():
    value = release()
    assert validate_release(value) == value["release_identity"]
    bound = bind_validated_request(value, b"query", validation(value))
    assert bound.query == b"query"


def test_transport_cannot_accept_substituted_query():
    value = release()
    with pytest.raises(ValueError, match="query bytes"):
        bind_validated_request(value, b"replacement", validation(value))


def test_release_rejects_governance_drift():
    value = copy.deepcopy(release())
    value["artifact_retention_days"] = 7
    with pytest.raises(ValueError, match="release authority"):
        validate_release(value)


def test_activation_template_has_no_rfc3161_transport_or_metadata_capture():
    root = Path(__file__).parents[1]
    text = (root / "deployment/semantic-authority-milestone-9.yml.template").read_text("utf-8")
    assert "docker run --rm --network none --read-only" in text
    assert "push-to-registry: false" in text
    assert "timestamp.digicert.com" not in text
    assert "Crossref" not in text and "OpenAlex" not in text
    assert text.index("Verify committed proof") < text.index("Attest initiation")
    assert text.index("Attest initiation") < text.index("Bind initiation attestation into final subject")
    assert text.index("Bind initiation attestation into final subject") < text.index("Attest final state")
    assert "--prepare-final '${{ steps.initiation.outputs.bundle-path }}'" in text
