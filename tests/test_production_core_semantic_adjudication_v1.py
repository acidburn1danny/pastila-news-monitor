import base64
import copy
import hashlib
import json
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
    adjudicate_pair_from_registry,
    load_adjudicator_registry,
    sha256,
    sign_receipt,
    verify_receipt,
)

OPENSSL = Path(
    os.environ.get("PASTILA_ADJUDICATION_TEST_OPENSSL", shutil.which("openssl") or "")
)
ROOT = Path(__file__).resolve().parents[1]
REGISTRY = (
    ROOT
    / "docs/artifacts/production-core-semantic-adjudicator-public-key-registry-v1.json"
)
REGISTRY_IDENTITY = "26772b5ae3e7ffe853e75b79b9d37ef7649ad183917afa2a0170f79e2b2d1639"


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
        "adjudicator_registry_identity": REGISTRY_IDENTITY,
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
            "adjudicator_registry_identity",
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
    "field",
    [
        "case_id",
        "candidate_output_sha256",
        "rubric_sha256",
        "adjudicator_registry_identity",
        "verdict",
    ],
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


def test_registry_loader_closes_exact_artifact_identity_and_key_bytes():
    raw = REGISTRY.read_bytes()
    loaded = load_adjudicator_registry(raw)
    assert loaded.identity == REGISTRY_IDENTITY
    value = json.loads(raw)
    for role in ROLE_IDS:
        assert (
            sha256(loaded.public_key_bytes[role])
            == value["roles"][role]["public_key_sha256"]
        )
        assert loaded.registrations[role] == (
            value["roles"][role]["adjudicator_id"],
            value["roles"][role]["public_key_sha256"],
        )


def test_registry_artifact_substitution_and_duplicate_keys_fail_closed():
    raw = REGISTRY.read_bytes()
    with pytest.raises(ValueError, match="artifact identity mismatch"):
        load_adjudicator_registry(raw + b" ")
    duplicate = raw.replace(
        b'{\n  "schema":', b'{\n  "schema":"duplicate",\n  "schema":', 1
    )
    with pytest.raises(ValueError):
        load_adjudicator_registry(duplicate)


def test_registry_wrapper_materializes_exact_keys_and_rejects_stale_authority(
    monkeypatch,
):
    raw = REGISTRY.read_bytes()
    expected_authority = {
        "qualification_generation_sha256": module.FROZEN_GENERATION_IDENTITY,
        "corpus_sha256": module.FROZEN_CORPUS_IDENTITY,
        "case_id": "pcq-fac-001",
        "candidate_alias": "CANDIDATE-A",
        "candidate_output_sha256": "3" * 64,
        "assertion_id": "ASSERTION-001",
        "rubric_sha256": module.FROZEN_RUBRIC_IDENTITY,
        "adjudicator_registry_identity": module.FROZEN_REGISTRY_IDENTITY,
    }
    candidate_output = {
        "schema": "pastila-core-v2-structured-qualification-response",
        "schema_version": 1,
        "case_id": expected_authority["case_id"],
        "request_identity": "sha256:" + "6" * 64,
        "output_type": "FACTUAL",
        "outcome": "ANSWER",
        "text": "Fapt verificat.",
        "claim_bindings": [{"claim_index": 1, "source_span_ids": ["source:1"]}],
        "abstention_code": None,
    }
    valid_output = module.canonical_response_bytes(candidate_output)
    packet_core = {
        "schema": "pastila-production-core-blind-adjudication-packet",
        "schema_version": 1,
        "qualification_generation_sha256": expected_authority["qualification_generation_sha256"],
        "corpus_sha256": expected_authority["corpus_sha256"],
        "case": {"case_id": expected_authority["case_id"], "request_identity": candidate_output["request_identity"], "output_type": "FACTUAL"},
        "candidate_alias": expected_authority["candidate_alias"],
        "candidate_output": candidate_output,
        "candidate_output_base64": base64.b64encode(valid_output).decode("ascii"),
        "candidate_output_sha256": module.sha256(valid_output),
        "candidate_output_validation": {"status": "PASS", "failure_code": None, "failure_detail": None},
        "execution_receipt_identity": "5" * 64,
        "assertion": {"assertion_id": expected_authority["assertion_id"]},
        "rubric_sha256": expected_authority["rubric_sha256"],
        "adjudicator_registry_identity": expected_authority["adjudicator_registry_identity"],
    }
    packet = {**packet_core, "packet_identity": module.sha256(module.canonical(packet_core))}
    packet_bytes = module.canonical(packet)
    packet_path = "materialization-A/repetition-1/CANDIDATE-A/case.blind.json"
    def custody_for(selected_packet: bytes, *, inventory_mutation=None, custody_mutation=None):
        inventory = [
            {"path": packet_path, "sha256": module.sha256(selected_packet)},
            *(
                {"path": f"materialization-B/repetition-3/CANDIDATE-B/dummy-{index:04d}.blind.json", "sha256": f"{index:064x}"}
                for index in range(1, 2400)
            ),
        ]
        inventory.sort(key=lambda row: row["path"].encode("ascii"))
        if inventory_mutation is not None:
            inventory_mutation(inventory)
        inventory_bytes = module.canonical(inventory)
        custody_core = {
            "schema": "pastila-production-core-blind-export-custody-manifest",
            "schema_version": 1,
            "adjudicator_role": "ADJUDICATOR_A",
            "qualification_generation_identity": module.FROZEN_GENERATION_IDENTITY,
            "packet_count": 2400,
            "packets_root": module.sha256(inventory_bytes),
            "candidate_mapping_present": False,
            "private_observations_present": False,
        }
        if custody_mutation is not None:
            custody_mutation(custody_core)
        custody_identity = module.sha256(module.canonical(custody_core))
        return {
            "blind_packet_path": packet_path,
            "export_inventory_bytes": inventory_bytes,
            "custody_manifest_bytes": module.canonical({**custody_core, "custody_identity": custody_identity}),
            "authorized_custody_identity": custody_identity,
        }
    custody_args = custody_for(packet_bytes)
    expected_authority["candidate_output_sha256"] = module.sha256(valid_output)
    observed = {}

    def inspect_materialization(
        receipts,
        *,
        public_keys,
        registered_adjudicators,
        expected_authority,
        openssl,
        expected_openssl_runtime_sha256,
    ):
        del receipts, openssl, expected_openssl_runtime_sha256
        observed["keys"] = {role: public_keys[role].read_bytes() for role in ROLE_IDS}
        observed["registrations"] = registered_adjudicators
        observed["authority"] = expected_authority
        return "PASS"

    monkeypatch.setattr(module, "adjudicate_pair", inspect_materialization)
    assert (
        adjudicate_pair_from_registry(
            [],
            registry_bytes=raw,
            blind_packet_bytes=packet_bytes,
            **custody_args,
            openssl=Path("unused"),
            expected_openssl_runtime_sha256={},
        )
        == "PASS"
    )
    loaded = load_adjudicator_registry(raw)
    assert observed == {
        "keys": loaded.public_key_bytes,
        "registrations": loaded.registrations,
        "authority": expected_authority,
    }
    malformed_custodies = (
        custody_for(packet_bytes, inventory_mutation=lambda rows: rows.append("bad-row")),
        custody_for(packet_bytes, inventory_mutation=lambda rows: rows[1].update({"extra": True})),
        custody_for(packet_bytes, inventory_mutation=lambda rows: rows[1].__setitem__("path", rows[0]["path"])),
        custody_for(packet_bytes, inventory_mutation=lambda rows: rows.reverse()),
        custody_for(packet_bytes, inventory_mutation=lambda rows: rows[1].__setitem__("path", "../escape.blind.json")),
        custody_for(packet_bytes, custody_mutation=lambda value: value.__setitem__("adjudicator_role", "OWNER")),
        custody_for(packet_bytes, custody_mutation=lambda value: value.__setitem__("schema_version", True)),
        custody_for(packet_bytes, custody_mutation=lambda value: value.__setitem__("packet_count", True)),
        custody_for(packet_bytes, custody_mutation=lambda value: value.__setitem__("extra", True)),
    )
    for malformed in malformed_custodies:
        with pytest.raises(ValueError, match="custody"):
            adjudicate_pair_from_registry(
                [], registry_bytes=raw, blind_packet_bytes=packet_bytes,
                **malformed, openssl=Path("unused"),
                expected_openssl_runtime_sha256={},
            )
    invalid_core = dict(packet_core)
    invalid_core["candidate_output_validation"] = {
        "status": "FAIL",
        "failure_code": "STRUCTURED_RESPONSE_V1_INVALID",
        "failure_detail": "candidate output is not one UTF-8 JSON object",
    }
    invalid = {**invalid_core, "packet_identity": module.sha256(module.canonical(invalid_core))}
    invalid_bytes = module.canonical(invalid)
    with pytest.raises(ValueError, match="structural FAIL is terminal"):
        adjudicate_pair_from_registry(
            [],
            registry_bytes=raw,
            blind_packet_bytes=invalid_bytes,
            **custody_for(invalid_bytes),
            openssl=Path("unused"),
            expected_openssl_runtime_sha256={},
        )

    for mutate, message in (
        (lambda value: value["candidate_output"].__setitem__("text", "Substituit."), "raw/canonical"),
        (lambda value: value["case"].__setitem__("request_identity", "sha256:" + "7" * 64), "case binding"),
        (lambda value: value.__setitem__("qualification_generation_sha256", "8" * 64), "frozen authority"),
        (lambda value: value.__setitem__("schema_version", True), "frozen authority"),
    ):
        rebound_core = copy.deepcopy(packet_core)
        mutate(rebound_core)
        rebound = {
            **rebound_core,
            "packet_identity": module.sha256(module.canonical(rebound_core)),
        }
        rebound_bytes = module.canonical(rebound)
        with pytest.raises(ValueError, match=message):
            adjudicate_pair_from_registry(
                [], registry_bytes=raw, blind_packet_bytes=rebound_bytes,
                **custody_for(rebound_bytes),
                openssl=Path("unused"), expected_openssl_runtime_sha256={},
            )
