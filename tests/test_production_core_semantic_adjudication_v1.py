import copy
import hashlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import pastila_scout.production_core_semantic_adjudication_v1 as module
from pastila_scout.production_core_semantic_adjudication_v1 import (
    ROLE_IDS,
    SIGNED_FIELDS,
    adjudicate_pair,
    sha256,
    sign_receipt,
    verify_receipt,
)

OPENSSL = Path(
    os.environ.get("PASTILA_ADJUDICATION_TEST_OPENSSL", shutil.which("openssl") or "")
)


def _keypair(root: Path, name: str):
    private = root / f"{name}.pem"
    public = root / f"{name}.pub.pem"
    subprocess.run(
        [str(OPENSSL), "genpkey", "-algorithm", "ED25519", "-out", str(private)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [str(OPENSSL), "pkey", "-in", str(private), "-pubout", "-out", str(public)],
        check=True,
        capture_output=True,
    )
    return private, public


def _unsigned(role: str, key: Path, verdict="PASS"):
    values = {
        "schema": "pastila-production-core-semantic-adjudication-receipt",
        "schema_version": 1,
        "qualification_generation_sha256": "1" * 64,
        "corpus_sha256": "2" * 64,
        "case_id": "PCQ-FAC-001",
        "candidate_alias": "CANDIDATE-A",
        "candidate_output_sha256": "3" * 64,
        "assertion_id": "ASSERTION-001",
        "rubric_sha256": "4" * 64,
        "adjudicator_id": f"PERSON-{role[-1]}",
        "adjudicator_role": role,
        "adjudicator_key_sha256": sha256(key.read_bytes()),
        "verdict": verdict,
    }
    return {field: values[field] for field in SIGNED_FIELDS}


@pytest.fixture
def kit(tmp_path):
    if not OPENSSL.is_file():
        pytest.skip("qualified local OpenSSL unavailable")
    runtime = {
        name: hashlib.sha256((OPENSSL.parent / name).read_bytes()).hexdigest()
        for name in ("openssl.exe", "libcrypto-3-x64.dll", "libssl-3-x64.dll")
    }
    a_priv, a_pub = _keypair(tmp_path, "a")
    b_priv, b_pub = _keypair(tmp_path, "b")
    a = sign_receipt(
        _unsigned(ROLE_IDS[0], a_pub),
        private_key=a_priv,
        openssl=OPENSSL,
        expected_openssl_runtime_sha256=runtime,
    )
    b = sign_receipt(
        _unsigned(ROLE_IDS[1], b_pub),
        private_key=b_priv,
        openssl=OPENSSL,
        expected_openssl_runtime_sha256=runtime,
    )
    authority = {
        field: a[field]
        for field in (
            "qualification_generation_sha256",
            "corpus_sha256",
            "case_id",
            "candidate_alias",
            "candidate_output_sha256",
            "assertion_id",
            "rubric_sha256",
        )
    }
    registrations = {
        ROLE_IDS[0]: ("PERSON-A", sha256(a_pub.read_bytes())),
        ROLE_IDS[1]: ("PERSON-B", sha256(b_pub.read_bytes())),
    }
    return runtime, authority, registrations, (a_priv, a_pub, a), (b_priv, b_pub, b)


def test_real_ed25519_two_person_pass_is_offline_and_identity_closed(kit):
    runtime, authority, registrations, (_, a_pub, a), (_, b_pub, b) = kit
    assert (
        verify_receipt(
            a,
            public_key=a_pub,
            openssl=OPENSSL,
            expected_openssl_runtime_sha256=runtime,
        )
        == a["receipt_identity"]
    )
    assert (
        adjudicate_pair(
            [a, b],
            public_keys={ROLE_IDS[0]: a_pub, ROLE_IDS[1]: b_pub},
            registered_adjudicators=registrations,
            expected_authority=authority,
            openssl=OPENSSL,
            expected_openssl_runtime_sha256=runtime,
        )
        == "PASS"
    )


@pytest.mark.parametrize(
    "field", ["case_id", "candidate_output_sha256", "rubric_sha256", "verdict"]
)
def test_signed_field_substitution_fails(kit, field):
    runtime, _, _, (_, a_pub, a), _ = kit
    bad = copy.deepcopy(a)
    bad[field] = (
        "FAIL" if field == "verdict" else ("X" if field == "case_id" else "f" * 64)
    )
    with pytest.raises(ValueError):
        verify_receipt(
            bad,
            public_key=a_pub,
            openssl=OPENSSL,
            expected_openssl_runtime_sha256=runtime,
        )


def test_boolean_schema_and_identity_revealing_alias_are_rejected(kit):
    runtime, _, _, (a_priv, a_pub, _), _ = kit
    boolean = _unsigned(ROLE_IDS[0], a_pub)
    boolean["schema_version"] = True
    revealing = _unsigned(ROLE_IDS[0], a_pub)
    revealing["candidate_alias"] = "EXPERIMENTAL_CORE_V1_1"
    for invalid in (boolean, revealing):
        with pytest.raises(ValueError):
            sign_receipt(
                invalid,
                private_key=a_priv,
                openssl=OPENSSL,
                expected_openssl_runtime_sha256=runtime,
            )


def test_owner_registration_and_expected_authority_are_mandatory(kit):
    runtime, authority, registrations, (_, a_pub, a), (_, b_pub, b) = kit
    keys = {ROLE_IDS[0]: a_pub, ROLE_IDS[1]: b_pub}
    wrong_registration = dict(registrations)
    wrong_registration[ROLE_IDS[1]] = ("PERSON-C", registrations[ROLE_IDS[1]][1])
    with pytest.raises(ValueError):
        adjudicate_pair(
            [a, b],
            public_keys=keys,
            registered_adjudicators=wrong_registration,
            expected_authority=authority,
            openssl=OPENSSL,
            expected_openssl_runtime_sha256=runtime,
        )
    invented = dict(authority)
    invented["corpus_sha256"] = "f" * 64
    with pytest.raises(ValueError):
        adjudicate_pair(
            [a, b],
            public_keys=keys,
            registered_adjudicators=registrations,
            expected_authority=invented,
            openssl=OPENSSL,
            expected_openssl_runtime_sha256=runtime,
        )


def test_signature_extra_field_and_verifier_substitution_fail(kit, tmp_path):
    runtime, _, _, (_, a_pub, a), _ = kit
    bad = copy.deepcopy(a)
    bad["signature_base64"] = "AA=="
    with pytest.raises(ValueError):
        verify_receipt(
            bad,
            public_key=a_pub,
            openssl=OPENSSL,
            expected_openssl_runtime_sha256=runtime,
        )
    extra = copy.deepcopy(a)
    extra["extra"] = None
    with pytest.raises(ValueError):
        verify_receipt(
            extra,
            public_key=a_pub,
            openssl=OPENSSL,
            expected_openssl_runtime_sha256=runtime,
        )
    substitute = tmp_path / "openssl"
    substitute.write_bytes(OPENSSL.read_bytes() + b"x")
    with pytest.raises(ValueError):
        verify_receipt(
            a,
            public_key=a_pub,
            openssl=substitute,
            expected_openssl_runtime_sha256=runtime,
        )


def test_public_key_path_substitution_after_snapshot_cannot_change_verification(
    kit, monkeypatch
):
    runtime, _, _, (_, a_pub, a), _ = kit
    original_run = module._run

    def substitute_then_run(command, *, timeout=30, env=None):
        a_pub.write_bytes(b"substituted-after-snapshot")
        return original_run(command, timeout=timeout, env=env)

    monkeypatch.setattr(module, "_run", substitute_then_run)
    assert (
        verify_receipt(
            a,
            public_key=a_pub,
            openssl=OPENSSL,
            expected_openssl_runtime_sha256=runtime,
        )
        == a["receipt_identity"]
    )


def test_openssl_path_substitution_and_host_config_after_snapshot_cannot_influence_result(
    kit, monkeypatch, tmp_path
):
    runtime, _, _, (_, a_pub, a), _ = kit
    copied_root = tmp_path / "runtime"
    copied_root.mkdir()
    for name in runtime:
        shutil.copy2(OPENSSL.parent / name, copied_root / name)
    copied_openssl = copied_root / "openssl.exe"
    original_run = module._run

    def substitute_then_run(command, *, timeout=30, env=None):
        copied_openssl.write_bytes(b"substituted-after-snapshot")
        assert env is not None and env["OPENSSL_CONF"].endswith("openssl-empty.cnf")
        assert env["OPENSSL_MODULES"].endswith("empty-modules")
        return original_run(command, timeout=timeout, env=env)

    monkeypatch.setenv("OPENSSL_CONF", "host-controlled.cnf")
    monkeypatch.setenv("OPENSSL_MODULES", "host-controlled-modules")
    monkeypatch.setattr(module, "_run", substitute_then_run)
    assert (
        verify_receipt(
            a,
            public_key=a_pub,
            openssl=copied_openssl,
            expected_openssl_runtime_sha256=runtime,
        )
        == a["receipt_identity"]
    )


def test_duplicate_person_disagreement_missing_and_cross_case_fail_closed(kit):
    runtime, authority, registrations, (a_priv, a_pub, a), (b_priv, b_pub, b) = kit
    duplicate = sign_receipt(
        _unsigned(ROLE_IDS[1], a_pub),
        private_key=a_priv,
        openssl=OPENSSL,
        expected_openssl_runtime_sha256=runtime,
    )
    keys = {ROLE_IDS[0]: a_pub, ROLE_IDS[1]: a_pub}
    with pytest.raises(ValueError):
        adjudicate_pair(
            [a, duplicate],
            public_keys=keys,
            registered_adjudicators=registrations,
            expected_authority=authority,
            openssl=OPENSSL,
            expected_openssl_runtime_sha256=runtime,
        )
    disagree = sign_receipt(
        _unsigned(ROLE_IDS[1], b_pub, "FAIL"),
        private_key=b_priv,
        openssl=OPENSSL,
        expected_openssl_runtime_sha256=runtime,
    )
    assert (
        adjudicate_pair(
            [a, disagree],
            public_keys={ROLE_IDS[0]: a_pub, ROLE_IDS[1]: b_pub},
            registered_adjudicators=registrations,
            expected_authority=authority,
            openssl=OPENSSL,
            expected_openssl_runtime_sha256=runtime,
        )
        == "FAIL_CLOSED"
    )
    with pytest.raises(ValueError):
        adjudicate_pair(
            [a],
            public_keys={ROLE_IDS[0]: a_pub, ROLE_IDS[1]: b_pub},
            registered_adjudicators=registrations,
            expected_authority=authority,
            openssl=OPENSSL,
            expected_openssl_runtime_sha256=runtime,
        )
    cross = copy.deepcopy(b)
    cross["case_id"] = "PCQ-FAC-002"
    with pytest.raises(ValueError):
        adjudicate_pair(
            [a, cross],
            public_keys={ROLE_IDS[0]: a_pub, ROLE_IDS[1]: b_pub},
            registered_adjudicators=registrations,
            expected_authority=authority,
            openssl=OPENSSL,
            expected_openssl_runtime_sha256=runtime,
        )
